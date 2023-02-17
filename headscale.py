import requests, json, os
from cryptography.fernet import Fernet
from datetime            import timedelta, date
from dateutil            import parser
from flask               import Flask
from flask.logging       import create_logger


app = Flask(__name__)
LOG = create_logger(app)

##################################################################
# Functions related to HEADSCALE and API KEYS
##################################################################

def get_url():  return os.environ['HS_SERVER']

def set_api_key(api_key):
    encryption_key = os.environ['KEY']                      # User-set encryption key
    key_file       = open("/data/key.txt", "wb+")           # Key file on the filesystem for persistent storage
    fernet         = Fernet(encryption_key)                 # Preparing the Fernet class with the key
    encrypted_key  = fernet.encrypt(api_key.encode())       # Encrypting the key
    return True if key_file.write(encrypted_key) else False # Return true if the file wrote correctly

def get_api_key():
    if not os.path.exists("/data/key.txt"): return False
    encryption_key = os.environ['KEY']                      # User-set encryption key
    key_file       = open("/data/key.txt", "rb+")           # Key file on the filesystem for persistent storage
    enc_api_key    = key_file.read()                        # The encrypted key read from the file
    if enc_api_key == b'': return "NULL"

    fernet         = Fernet(encryption_key)                 # Preparing the Fernet class with the key
    decrypted_key  = fernet.decrypt(enc_api_key).decode()   # Decrypting the key

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
#       app.logge.warning("Sending the payload '"+str(json_payload)+"' to the headscale server")

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
    key_info                = get_api_key_info(url, api_key)

    expiration_time     = key_info["expiration"]
    today_date          = date.today()
    expire              = parser.parse(expiration_time)
    expire_fmt          = str(expire.year) + "-" + str(expire.month).zfill(2) + "-" + str(expire.day).zfill(2) # 2023-01-04
    expire_date         = date.fromisoformat(expire_fmt)
    delta               = expire_date - today_date
    tmp                 = today_date + timedelta(days=90) 
    new_expiration_date = str(tmp)+"T00:00:00.000000Z"

    # If the delta is less than 5 days, renew the key:
    if delta < timedelta(days=5):
#       app.logge.warning("Key is about to expire.  Delta is "+str(delta))
        payload = {'expiration':str(new_expiration_date)}
        json_payload=json.dumps(payload)
#       app.logge.warning("Sending the payload '"+str(json_payload)+"' to the headscale server")

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
#       app.logge.warning("JSON:  "+json.dumps(new_key))
#       app.logge.warning("New Key is:  "+new_key["apiKey"])
        api_key_test = test_api_key(url, new_key["apiKey"])
#       app.logge.warning("Testing the key:  "+str(api_key_test))
        # Test if the new key works:
        if api_key_test == 200:
#           app.logge.warning("The new key is valid and we are writing it to the file")
            if not set_api_key(new_key["apiKey"]):
#               app.logge.warning("We failed writing the new key!")
                return False # Key write failed
#           app.logge.warning("Key validated and written.  Moving to expire the key.")
            expire_key(url, api_key)
            return True     # Key updated and validated
        else: return False  # The API Key test failed
    else: return True       #No work is required

# Gets information about the current API key
def get_api_key_info(url, api_key):
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
    for key in json_response["apiKeys"]:
        if key_prefix == key["prefix"]:
            return key
    return "Key not found"

##################################################################
# Functions related to MACHINES
##################################################################

# register a new machine
def register_machine(url, api_key, machine_key, user):
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
    response = requests.post(
        str(url)+"/api/v1/machine/"+str(machine_id)+"/user?user="+str(new_user),
        headers={
            'Accept': 'application/json',
            'Authorization': 'Bearer '+str(api_key)
        }
    )
    return response.json()

# updates routes for the given machine_id. enable / disable
# The Headscale API expects a list of routes to enable.  if we want to toggle 1 out of 3 routes
# we need to pass all currently enabled routes and mask it
# For example, if we have routes:
#  0.0.0.0/0
#  ::/0
#  192.168.1.0/24
# available, but only routes 
#  0.0.0.0/24
#  192.168.1.0/24 
# ENABLED, and we want to disable route 192.168.1.0/24, we need to pass ONLY the routes to KEEP enabled.
# In this case, 0.0.0/24
def update_route(url, api_key, route_id, current_state):
    action = ""
    if current_state == "True":  action = "disable"
    if current_state == "False": action = "enable"

    # Debug
    # LOG.info("URL:  "+str(url))
    # LOG.info("Route ID:  "+str(route_id))
    # LOG.info("Current State:  "+str(current_state))
    # LOG.info("Action to take:  "+str(action))

    response = requests.post(
        str(url)+"/api/v1/routes/"+str(route_id)+"/"+str(action),
        headers={
            'Accept': 'application/json',
            'Authorization': 'Bearer '+str(api_key)
        }
    )
    return response.json()
    # First, get all route info:
#    routes = get_machine_routes(url, api_key, machine_id)
#    to_enable = []
#    is_enabled = False
    # "route" is what we are toggling.  On or off. 
    # Get a list of all currently enabled routes.
    # If route IS currently in enabled routes, remove it
#    # TODO: REDO THIS FOR THE NEW API
#    for enabled_route in routes["routes"]["enabledRoutes"]:
#        if enabled_route == route: is_enabled=True
#        else: to_enable.append(enabled_route)
#    if not is_enabled: to_enable.append(route)
#
#    query = ""
#    count = 0
#    for route in to_enable:
#        count = count+1
#        if count == 1:  query = query+"routes="+route
#        else: query = query+"&routes="+route
#
#    response = requests.post(
#        str(url)+"/api/v1/machine/"+str(machine_id)+"/routes?"+query,
#        headers={
#            'Accept': 'application/json',
#            'Authorization': 'Bearer '+str(api_key)
#        }
#    )
#    return response.json()

# Get all machines on the Headscale network
def get_machines(url, api_key):
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
    response = requests.delete(
        str(url)+"/api/v1/machine/"+str(machine_id),
        headers={
            'Accept': 'application/json',
            'Authorization': 'Bearer '+str(api_key)
        }
    )
    status = "True" if response.status_code == 200 else "False"
    return {"status": status, "body": response.json()}

# Rename "machine_id" with name "new_name"
def rename_machine(url, api_key, machine_id, new_name):
    response = requests.post(
        str(url)+"/api/v1/machine/"+str(machine_id)+"/rename/"+str(new_name),
        headers={
            'Accept': 'application/json',
            'Authorization': 'Bearer '+str(api_key)
        }
    )
    status = "True" if response.status_code == 200 else "False"
    return {"status": status, "body": response.json()}

# Gets routes for the passed machine_id
def get_machine_routes(url, api_key, machine_id):
    response = requests.get(
        str(url)+"/api/v1/machine/"+str(machine_id)+"/routes",
        headers={
            'Accept': 'application/json',
            'Authorization': 'Bearer '+str(api_key)
        }
    )
    return response.json()
# Gets routes for the entire tailnet
def get_routes(url, api_key):
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
    response = requests.post(
        str(url)+"/api/v1/user/"+str(old_name)+"/rename/"+str(new_name),
        headers={
            'Accept': 'application/json',
            'Authorization': 'Bearer '+str(api_key)
        }
    )
    status = "True" if response.status_code == 200 else "False"
    return {"status": status, "body": response.json()}

# Delete a user from Headscale
def delete_user(url, api_key, user_name):
    response = requests.delete(
        str(url)+"/api/v1/user/"+str(user_name),
        headers={
            'Accept': 'application/json',
            'Authorization': 'Bearer '+str(api_key)
        }
    )
    status = "True" if response.status_code == 200 else "False"
    return {"status": status, "body": response.json()}

# Add a user from Headscale
def add_user(url, api_key, data):
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
    return {"status": status, "body": response.json()}

##################################################################
# Functions related to PREAUTH KEYS in NAMESPACES
##################################################################

# Get all PreAuth keys associated with a user "user_name"
def get_preauth_keys(url, api_key, user_name):
    response = requests.get(
        str(url)+"/api/v1/preauthkey?user="+str(user_name),
        headers={
            'Accept': 'application/json',
            'Authorization': 'Bearer '+str(api_key)
        }
    )
    return response.json()

# Add a preauth key to the user "user_name" given the booleans "ephemeral" and "reusable" with the expiration date "date" contained in the JSON payload "data"
def add_preauth_key(url, api_key, data):
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
    return {"status": status, "body": response.json()}

# Expire a pre-auth key.  data is {"user": "string", "key": "string"}
def expire_preauth_key(url, api_key, data):
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
    ## LOG.info("expire_preauth_key - Return:  "+str(response.json()))
    ## LOG.info("expire_preauth_key - Status:  "+str(status))
    return {"status": status, "body": response.json()}
