# pylint: disable=wrong-import-order

import requests, json, os
from cryptography.fernet import Fernet
from datetime            import timedelta, date
from dateutil            import parser
from flask               import Flask, current_app

app = Flask(__name__)
LOG = current_app.logger

##################################################################
# Functions related to HEADSCALE and API KEYS
##################################################################

def get_url():  return os.environ['HS_SERVER']

def set_api_key(api_key):
    # User-set encryption key
    encryption_key = os.environ['KEY']                      
    # Key file on the filesystem for persistent storage
    key_file       = open("/data/key.txt", "wb+")           
    # Preparing the Fernet class with the key
    fernet         = Fernet(encryption_key)                 
    # Encrypting the key
    encrypted_key  = fernet.encrypt(api_key.encode())       
    # Return true if the file wrote correctly
    return True if key_file.write(encrypted_key) else False 

def get_api_key():
    if not os.path.exists("/data/key.txt"): return False
    # User-set encryption key
    encryption_key = os.environ['KEY']                      
    # Key file on the filesystem for persistent storage
    key_file       = open("/data/key.txt", "rb+")           
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
    LOG.debug("Sending the payload '"+str(json_payload)+"' to the headscale server")

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
        LOG.warning("Key is about to expire.  Delta is "+str(delta))
        payload = {'expiration':str(new_expiration_date)}
        json_payload=json.dumps(payload)
        LOG.debug("Sending the payload '"+str(json_payload)+"' to the headscale server")

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
        LOG.debug("JSON:  "+json.dumps(new_key))
        LOG.debug("New Key is:  "+new_key["apiKey"])
        api_key_test = test_api_key(url, new_key["apiKey"])
        LOG.debug("Testing the key:  "+str(api_key_test))
        # Test if the new key works:
        if api_key_test == 200:
            LOG.info("The new key is valid and we are writing it to the file")
            if not set_api_key(new_key["apiKey"]):
                LOG.error("We failed writing the new key!")
                return False # Key write failed
            LOG.info("Key validated and written.  Moving to expire the key.")
            expire_key(url, api_key)
            return True     # Key updated and validated
        else: 
            LOG.error("Testing the API key failed.")
            return False  # The API Key test failed
    else: return True       # No work is required

# Gets information about the current API key
def get_api_key_info(url, api_key):
    LOG.info("Getting API key information")
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
    LOG.info("Looking for valid API Key...")
    for key in json_response["apiKeys"]:
        if key_prefix == key["prefix"]:
            LOG.info("Key found.")
            return key
    LOG.error("Could not find a valid key in Headscale.  Need a new API key.")
    return "Key not found"

##################################################################
# Functions related to MACHINES
##################################################################

# register a new machine
def register_machine(url, api_key, machine_key, user):
    LOG.info("Registering machine %s to user %s", str(machine_key), str(user))
    response = requests.post(
        str(url)+"/api/v1/machine/register?user="+str(user)+"&key="+str(machine_key),
        headers={
            'Accept': 'application/json',
            'Authorization': 'Bearer '+str(api_key)
        }
    )
    return response.json()


# Sets the machines tags
def set_machine_tags(url, api_key, machine_id, tags_list):
    LOG.info("Setting machine_id %s tag %s", str(machine_id), str(tags_list))
    response = requests.post(
        str(url)+"/api/v1/machine/"+str(machine_id)+"/tags",
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
    LOG.info("Moving machine_id %s to user %s", str(machine_id), str(new_user))
    response = requests.post(
        str(url)+"/api/v1/machine/"+str(machine_id)+"/user?user="+str(new_user),
        headers={
            'Accept': 'application/json',
            'Authorization': 'Bearer '+str(api_key)
        }
    )
    return response.json()

def update_route(url, api_key, route_id, current_state):
    action = ""
    if current_state == "True":  action = "disable"
    if current_state == "False": action = "enable"
    LOG.info("Updating Route %s:  Action: %s", str(route_id), str(action))

    # Debug
    LOG.debug("URL:  "+str(url))
    LOG.debug("Route ID:  "+str(route_id))
    LOG.debug("Current State:  "+str(current_state))
    LOG.debug("Action to take:  "+str(action))

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
    LOG.info("Getting machine information")
    response = requests.get(
        str(url)+"/api/v1/machine",
        headers={
            'Accept': 'application/json',
            'Authorization': 'Bearer '+str(api_key)
        }
    )
    return response.json()

# Get machine with "machine_id" on the Headscale network
def get_machine_info(url, api_key, machine_id):
    LOG.info("Getting information for machine ID %s", str(machine_id))
    response = requests.get(
        str(url)+"/api/v1/machine/"+str(machine_id),
        headers={
            'Accept': 'application/json',
            'Authorization': 'Bearer '+str(api_key)
        }
    )
    return response.json()

# Delete a machine from Headscale
def delete_machine(url, api_key, machine_id):
    LOG.info("Deleting machine %s", str(machine_id))
    response = requests.delete(
        str(url)+"/api/v1/machine/"+str(machine_id),
        headers={
            'Accept': 'application/json',
            'Authorization': 'Bearer '+str(api_key)
        }
    )
    status = "True" if response.status_code == 200 else "False"
    if response.status_code == 200:
        LOG.info("Machine deleted.")
    else:
        LOG.error("Deleting machine failed!  %s", str(response.json()))
    return {"status": status, "body": response.json()}

# Rename "machine_id" with name "new_name"
def rename_machine(url, api_key, machine_id, new_name):
    LOG.info("Renaming machine %s", str(machine_id))
    response = requests.post(
        str(url)+"/api/v1/machine/"+str(machine_id)+"/rename/"+str(new_name),
        headers={
            'Accept': 'application/json',
            'Authorization': 'Bearer '+str(api_key)
        }
    )
    status = "True" if response.status_code == 200 else "False"
    if response.status_code == 200:
        LOG.info("Machine renamed")
    else:
        LOG.error("Machine rename failed!  %s", str(response.json()))
    return {"status": status, "body": response.json()}

# Gets routes for the passed machine_id
def get_machine_routes(url, api_key, machine_id):
    LOG.info("Renaming machine %s", str(machine_id))
    response = requests.get(
        str(url)+"/api/v1/machine/"+str(machine_id)+"/routes",
        headers={
            'Accept': 'application/json',
            'Authorization': 'Bearer '+str(api_key)
        }
    )
    if response.status_code == 200:
        LOG.info("Routes obtained")
    else:
        LOG.error("Failed to get routes:  %s", str(response.json()))
    return response.json()

# Gets routes for the entire tailnet
def get_routes(url, api_key):
    LOG.info("Getting routes")
    response = requests.get(
        str(url)+"/api/v1/routes",
        headers={
            'Accept': 'application/json',
            'Authorization': 'Bearer '+str(api_key)
        }
    )
    return response.json()

##################################################################
# Functions related to NAMESPACES
##################################################################

# Get all users in use
def get_users(url, api_key):
    LOG.info("Getting Users")
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
    LOG.info("Renaming user %s to %s.", str(old_name), str(new_name))
    response = requests.post(
        str(url)+"/api/v1/user/"+str(old_name)+"/rename/"+str(new_name),
        headers={
            'Accept': 'application/json',
            'Authorization': 'Bearer '+str(api_key)
        }
    )
    status = "True" if response.status_code == 200 else "False"
    if response.status_code == 200:
        LOG.info("User renamed.")
    else:
        LOG.error("Renaming User failed!")
    return {"status": status, "body": response.json()}

# Delete a user from Headscale
def delete_user(url, api_key, user_name):
    LOG.info("Deleting a User:  %s", str(user_name))
    response = requests.delete(
        str(url)+"/api/v1/user/"+str(user_name),
        headers={
            'Accept': 'application/json',
            'Authorization': 'Bearer '+str(api_key)
        }
    )
    status = "True" if response.status_code == 200 else "False"
    if response.status_code == 200:
        LOG.info("User deleted.")
    else:
        LOG.error("Deleting User failed!")
    return {"status": status, "body": response.json()}

# Add a user from Headscale
def add_user(url, api_key, data):
    LOG.info("Adding user:  %s", str(data))
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
        LOG.info("User added.")
    else:
        LOG.error("Adding User failed!")
    return {"status": status, "body": response.json()}

##################################################################
# Functions related to PREAUTH KEYS in NAMESPACES
##################################################################

# Get all PreAuth keys associated with a user "user_name"
def get_preauth_keys(url, api_key, user_name):
    LOG.info("Getting PreAuth Keys in User %s", str(user_name))
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
    LOG.info("Adding PreAuth Key:  %s", str(data))
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
        LOG.info("PreAuth Key added.")
    else:
        LOG.error("Adding PreAuth Key failed!")
    return {"status": status, "body": response.json()}

# Expire a pre-auth key.  data is {"user": "string", "key": "string"}
def expire_preauth_key(url, api_key, data):
    LOG.info("Expiring PreAuth Key...")
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
    LOG.debug("expire_preauth_key - Return:  "+str(response.json()))
    LOG.debug("expire_preauth_key - Status:  "+str(status))
    return {"status": status, "body": response.json()}
