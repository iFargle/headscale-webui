# pylint: disable=wrong-import-order

import requests, json, os, logging, yaml
from cryptography.fernet import Fernet
from datetime            import timedelta, date
from dateutil            import parser
from flask               import Flask
from dotenv              import load_dotenv

load_dotenv()
LOG_LEVEL = os.environ["LOG_LEVEL"].replace('"', '').upper()
DATA_DIRECTORY = os.environ["DATA_DIRECTORY"].replace('"', '') if os.environ["DATA_DIRECTORY"] else "/data"
# Initiate the Flask application and logging:
app = Flask(__name__, static_url_path="/static")
match LOG_LEVEL:
    case "DEBUG"   : app.logger.setLevel(logging.DEBUG)
    case "INFO"    : app.logger.setLevel(logging.INFO)
    case "WARNING" : app.logger.setLevel(logging.WARNING)
    case "ERROR"   : app.logger.setLevel(logging.ERROR)
    case "CRITICAL": app.logger.setLevel(logging.CRITICAL)

##################################################################
# Functions related to HEADSCALE and API KEYS
##################################################################
def get_url(inpage=False):
    if not inpage: 
        return os.environ['HS_SERVER']
    config_file = ""
    try:
        config_file = open("/etc/headscale/config.yml",  "r")
        app.logger.info("Opening /etc/headscale/config.yml")
    except: 
        config_file = open("/etc/headscale/config.yaml", "r")
        app.logger.info("Opening /etc/headscale/config.yaml")
    config_yaml = yaml.safe_load(config_file)
    if "server_url" in config_yaml: 
        return str(config_yaml["server_url"])
    app.logger.warning("Failed to find server_url in the config. Falling back to ENV variable")
    return os.environ['HS_SERVER']

def set_api_key(api_key):
    # User-set encryption key
    encryption_key = os.environ['KEY']                      
    # Key file on the filesystem for persistent storage
    key_file       = open(os.path.join(DATA_DIRECTORY, "key.txt"), "wb+")
    # Preparing the Fernet class with the key
    fernet         = Fernet(encryption_key)                 
    # Encrypting the key
    encrypted_key  = fernet.encrypt(api_key.encode())       
    # Return true if the file wrote correctly
    return True if key_file.write(encrypted_key) else False 

def get_api_key():
    if not os.path.exists(os.path.join(DATA_DIRECTORY, "key.txt")): return False
    # User-set encryption key
    encryption_key = os.environ['KEY']                      
    # Key file on the filesystem for persistent storage
    key_file       = open(os.path.join(DATA_DIRECTORY, "key.txt"), "rb+")           
    # The encrypted key read from the file
    enc_api_key    = key_file.read()                        
    if enc_api_key == b'': return "NULL"

    # Preparing the Fernet class with the key
    fernet         = Fernet(encryption_key)                 
    # Decrypting the key
    decrypted_key  = fernet.decrypt(enc_api_key).decode()   

    return decrypted_key

def test_api_key(url, api_key):
    response = requests.get(
        str(url)+"/api/v1/apikey",
        headers={
            'Accept': 'application/json',
            'Authorization': 'Bearer '+str(api_key)
        }
    )
    return response.status_code

# Expires an API key
def expire_key(url, api_key):
    payload = {'prefix':str(api_key[0:10])}
    json_payload=json.dumps(payload)
    app.logger.debug("Sending the payload '"+str(json_payload)+"' to the headscale server")

    response = requests.post(
        str(url)+"/api/v1/apikey/expire",
        data=json_payload,
        headers={
            'Accept': 'application/json',
            'Content-Type': 'application/json',
            'Authorization': 'Bearer '+str(api_key)
            }
    )
    return response.status_code

# Checks if the key needs to be renewed
# If it does, renews the key, then expires the old key
def renew_api_key(url, api_key):
    # 0 = Key has been updated or key is not in need of an update
    # 1 = Key has failed validity check or has failed to write the API key 
    # Check when the key expires and compare it to todays date:
    key_info            = get_api_key_info(url, api_key)
    expiration_time     = key_info["expiration"]
    today_date          = date.today()
    expire              = parser.parse(expiration_time)
    expire_fmt          = str(expire.year) + "-" + str(expire.month).zfill(2) + "-" + str(expire.day).zfill(2)
    expire_date         = date.fromisoformat(expire_fmt)
    delta               = expire_date - today_date
    tmp                 = today_date + timedelta(days=90) 
    new_expiration_date = str(tmp)+"T00:00:00.000000Z"

    # If the delta is less than 5 days, renew the key:
    if delta < timedelta(days=5):
        app.logger.warning("Key is about to expire.  Delta is "+str(delta))
        payload = {'expiration':str(new_expiration_date)}
        json_payload=json.dumps(payload)
        app.logger.debug("Sending the payload '"+str(json_payload)+"' to the headscale server")

        response = requests.post(
            str(url)+"/api/v1/apikey",
            data=json_payload,
            headers={
                'Accept': 'application/json',
                'Content-Type': 'application/json',
                'Authorization': 'Bearer '+str(api_key)
                }
        )
        new_key = response.json()
        app.logger.debug("JSON:  "+json.dumps(new_key))
        app.logger.debug("New Key is:  "+new_key["apiKey"])
        api_key_test = test_api_key(url, new_key["apiKey"])
        app.logger.debug("Testing the key:  "+str(api_key_test))
        # Test if the new key works:
        if api_key_test == 200:
            app.logger.info("The new key is valid and we are writing it to the file")
            if not set_api_key(new_key["apiKey"]):
                app.logger.error("We failed writing the new key!")
                return False # Key write failed
            app.logger.info("Key validated and written.  Moving to expire the key.")
            expire_key(url, api_key)
            return True     # Key updated and validated
        else: 
            app.logger.error("Testing the API key failed.")
            return False  # The API Key test failed
    else: return True       # No work is required

# Gets information about the current API key
def get_api_key_info(url, api_key):
    app.logger.info("Getting API key information")
    response = requests.get(
        str(url)+"/api/v1/apikey",
        headers={
            'Accept': 'application/json',
            'Authorization': 'Bearer '+str(api_key)
        }
    )
    json_response = response.json()
    # Find the current key in the array:  
    key_prefix = str(api_key[0:10])
    app.logger.info("Looking for valid API Key...")
    for key in json_response["apiKeys"]:
        if key_prefix == key["prefix"]:
            app.logger.info("Key found.")
            return key
    app.logger.error("Could not find a valid key in Headscale.  Need a new API key.")
    return "Key not found"

##################################################################
# Functions related to MACHINES
##################################################################

# register a new machine
def register_machine(url, api_key, machine_key, user):
    app.logger.info("Registering machine %s to user %s", str(machine_key), str(user))
    response = requests.post(
        str(url)+"/api/v1/node/register?user="+str(user)+"&key="+str(machine_key),
        headers={
            'Accept': 'application/json',
            'Authorization': 'Bearer '+str(api_key)
        }
    )
    return response.json()


# Sets the machines tags
def set_machine_tags(url, api_key, machine_id, tags_list):
    app.logger.info("Setting machine_id %s tag %s", str(machine_id), str(tags_list))
    response = requests.post(
        str(url)+"/api/v1/node/"+str(machine_id)+"/tags",
        data=tags_list,
        headers={
            'Accept': 'application/json',
            'Content-Type': 'application/json',
            'Authorization': 'Bearer '+str(api_key)
            }
    )
    return response.json()

# Moves machine_id to user "new_user"
def move_user(url, api_key, machine_id, new_user):
    app.logger.info("Moving machine_id %s to user %s", str(machine_id), str(new_user))
    response = requests.post(
        str(url)+"/api/v1/node/"+str(machine_id)+"/user?user="+str(new_user),
        headers={
            'Accept': 'application/json',
            'Authorization': 'Bearer '+str(api_key)
        }
    )
    return response.json()

def update_route(url, api_key, route_id, current_state):
    action = "disable" if current_state == "True" else "enable"

    app.logger.info("Updating Route %s:  Action: %s", str(route_id), str(action))

    # Debug
    app.logger.debug("URL:  "+str(url))
    app.logger.debug("Route ID:  "+str(route_id))
    app.logger.debug("Current State:  "+str(current_state))
    app.logger.debug("Action to take:  "+str(action))

    response = requests.post(
        str(url)+"/api/v1/routes/"+str(route_id)+"/"+str(action),
        headers={
            'Accept': 'application/json',
            'Authorization': 'Bearer '+str(api_key)
        }
    )
    return response.json()

# Get all machines on the Headscale network
def get_machines(url, api_key):
    app.logger.info("Getting machine information")
    response = requests.get(
        str(url)+"/api/v1/node",
        headers={
            'Accept': 'application/json',
            'Authorization': 'Bearer '+str(api_key)
        }
    )
    return response.json()

# Get machine with "machine_id" on the Headscale network
def get_machine_info(url, api_key, machine_id):
    app.logger.info("Getting information for machine ID %s", str(machine_id))
    response = requests.get(
        str(url)+"/api/v1/node/"+str(machine_id),
        headers={
            'Accept': 'application/json',
            'Authorization': 'Bearer '+str(api_key)
        }
    )
    return response.json()

# Delete a machine from Headscale
def delete_machine(url, api_key, machine_id):
    app.logger.info("Deleting machine %s", str(machine_id))
    response = requests.delete(
        str(url)+"/api/v1/node/"+str(machine_id),
        headers={
            'Accept': 'application/json',
            'Authorization': 'Bearer '+str(api_key)
        }
    )
    status = "True" if response.status_code == 200 else "False"
    if response.status_code == 200:
        app.logger.info("Machine deleted.")
    else:
        app.logger.error("Deleting machine failed!  %s", str(response.json()))
    return {"status": status, "body": response.json()}

# Rename "machine_id" with name "new_name"
def rename_machine(url, api_key, machine_id, new_name):
    app.logger.info("Renaming machine %s", str(machine_id))
    response = requests.post(
        str(url)+"/api/v1/node/"+str(machine_id)+"/rename/"+str(new_name),
        headers={
            'Accept': 'application/json',
            'Authorization': 'Bearer '+str(api_key)
        }
    )
    status = "True" if response.status_code == 200 else "False"
    if response.status_code == 200:
        app.logger.info("Machine renamed")
    else:
        app.logger.error("Machine rename failed!  %s", str(response.json()))
    return {"status": status, "body": response.json()}

# Gets routes for the passed machine_id
def get_machine_routes(url, api_key, machine_id):
    app.logger.info("Getting routes for machine %s", str(machine_id))
    response = requests.get(
        str(url)+"/api/v1/node/"+str(machine_id)+"/routes",
        headers={
            'Accept': 'application/json',
            'Authorization': 'Bearer '+str(api_key)
        }
    )
    if response.status_code == 200:
        app.logger.info("Routes obtained")
    else:
        app.logger.error("Failed to get routes:  %s", str(response.json()))
    return response.json()

# Gets routes for the entire tailnet
def get_routes(url, api_key):
    app.logger.info("Getting routes")
    response = requests.get(
        str(url)+"/api/v1/routes",
        headers={
            'Accept': 'application/json',
            'Authorization': 'Bearer '+str(api_key)
        }
    )
    return response.json()
##################################################################
# Functions related to USERS
##################################################################

# Get all users in use
def get_users(url, api_key):
    app.logger.info("Getting Users")
    response = requests.get(
        str(url)+"/api/v1/user",
        headers={
            'Accept': 'application/json',
            'Authorization': 'Bearer '+str(api_key)
        }
    )
    return response.json()

# Rename "old_name" with name "new_name"
def rename_user(url, api_key, old_name, new_name):
    app.logger.info("Renaming user %s to %s.", str(old_name), str(new_name))
    response = requests.post(
        str(url)+"/api/v1/user/"+str(old_name)+"/rename/"+str(new_name),
        headers={
            'Accept': 'application/json',
            'Authorization': 'Bearer '+str(api_key)
        }
    )
    status = "True" if response.status_code == 200 else "False"
    if response.status_code == 200:
        app.logger.info("User renamed.")
    else:
        app.logger.error("Renaming User failed!")
    return {"status": status, "body": response.json()}

# Delete a user from Headscale
def delete_user(url, api_key, user_name):
    app.logger.info("Deleting a User:  %s", str(user_name))
    response = requests.delete(
        str(url)+"/api/v1/user/"+str(user_name),
        headers={
            'Accept': 'application/json',
            'Authorization': 'Bearer '+str(api_key)
        }
    )
    status = "True" if response.status_code == 200 else "False"
    if response.status_code == 200:
        app.logger.info("User deleted.")
    else:
        app.logger.error("Deleting User failed!")
    return {"status": status, "body": response.json()}

# Add a user from Headscale
def add_user(url, api_key, data):
    app.logger.info("Adding user:  %s", str(data))
    response = requests.post(
        str(url)+"/api/v1/user",
        data=data,
        headers={
            'Accept': 'application/json',
            'Content-Type': 'application/json',
            'Authorization': 'Bearer '+str(api_key)
        }
    )
    status = "True" if response.status_code == 200 else "False"
    if response.status_code == 200:
        app.logger.info("User added.")
    else:
        app.logger.error("Adding User failed!")
    return {"status": status, "body": response.json()}

##################################################################
# Functions related to PREAUTH KEYS in USERS
##################################################################

# Get all PreAuth keys associated with a user "user_name"
def get_preauth_keys(url, api_key, user_name):
    app.logger.info("Getting PreAuth Keys in User %s", str(user_name))
    response = requests.get(
        str(url)+"/api/v1/preauthkey?user="+str(user_name),
        headers={
            'Accept': 'application/json',
            'Authorization': 'Bearer '+str(api_key)
        }
    )
    return response.json()

# Add a preauth key to the user "user_name" given the booleans "ephemeral" 
# and "reusable" with the expiration date "date" contained in the JSON payload "data"
def add_preauth_key(url, api_key, data):
    app.logger.info("Adding PreAuth Key:  %s", str(data))
    response = requests.post(
        str(url)+"/api/v1/preauthkey",
        data=data,
        headers={
            'Accept': 'application/json',
            'Content-Type': 'application/json',
            'Authorization': 'Bearer '+str(api_key)
        }
    )
    status = "True" if response.status_code == 200 else "False"
    if response.status_code == 200:
        app.logger.info("PreAuth Key added.")
    else:
        app.logger.error("Adding PreAuth Key failed!")
    return {"status": status, "body": response.json()}

# Expire a pre-auth key.  data is {"user": "string", "key": "string"}
def expire_preauth_key(url, api_key, data):
    app.logger.info("Expiring PreAuth Key...")
    response = requests.post(
        str(url)+"/api/v1/preauthkey/expire",
        data=data,
        headers={
            'Accept': 'application/json',
            'Content-Type': 'application/json',
            'Authorization': 'Bearer '+str(api_key)
        }
    )
    status = "True" if response.status_code == 200 else "False"
    app.logger.debug("expire_preauth_key - Return:  "+str(response.json()))
    app.logger.debug("expire_preauth_key - Status:  "+str(status))
    return {"status": status, "body": response.json()}
