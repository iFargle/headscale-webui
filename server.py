import json, renderer, headscale, helper, pytz, os
from flask          import Flask, render_template, request, url_for, redirect, Markup
from dateutil       import parser
# from flask_executor import Executor

# Global vars
# Colors:  https://materializecss.com/color.html
COLOR_NAV   = "blue-grey darken-1"
COLOR_BTN   = "blue-grey darken-3"
BASE_PATH   = os.environ["BASE_PATH"].replace('"', '')
BUILD_DATE  = os.environ["BUILD_DATE"]
APP_VERSION = os.environ["APP_VERSION"]
GIT_COMMIT  = os.environ["GIT_COMMIT"]
GIT_BRANCH  = os.environ["GIT_BRANCH"]
HS_VERSION  = "v0.20.0"
DEBUG_STATE = False
AUTH_TYPE   = os.environ["AUTH_TYPE"].replace('"', '')

# Set Authentication type:
if AUTH_TYPE.lower() == "oidc":
    # Load OIDC libraries
    from flaskoidc import FlaskOIDC

    app = FlaskOIDC(__name__)
    app.logger.debug("Loading OIDC libraries and configuring app...")
    # TODO:
    # If OIDC is enabled, add user info and a logout button to the top bar.

elif AUTH_TYPE.lower() == "basic":
    app = Flask(__name__)
    # Load basic auth libraries:
    app.logger.debug("Loading basic auth libraries and configuring app...")
    # https://flask-basicauth.readthedocs.io/en/latest/

    from flask_basicauth import BasicAuth
    app.config['BASIC_AUTH_USERNAME'] = os.environ["BASIC_AUTH_USER"].replace('"', '')
    app.config['BASIC_AUTH_PASSWORD'] = os.environ["BASIC_AUTH_PASS"]
    app.config['BASIC_AUTH_FORCE']    = True

    basic_auth = BasicAuth(app)

else:
    app = Flask(__name__)

app.logger.debug("===================================== Environment:  ")
app.logger.debug("FLASK_OIDC_PROVIDER_NAME:           "+os.environ["FLASK_OIDC_PROVIDER_NAME"])
app.logger.debug("FLASK_OIDC_CLIENT_ID:               "+os.environ["FLASK_OIDC_CLIENT_ID"])
app.logger.debug("FLASK_OIDC_CLIENT_SECRET:           "+os.environ["FLASK_OIDC_CLIENT_SECRET"])
app.logger.debug("FLASK_OIDC_CONFIG_URL:              "+os.environ["FLASK_OIDC_CONFIG_URL"])
app.logger.debug("BASE_PATH:                          "+os.environ["BASE_PATH"])
app.logger.debug("AUTH_TYPE:                          "+os.environ["AUTH_TYPE"])
app.config["APPLICATION_ROOT"] = os.environ["BASE_PATH"].replace('"', '')
app.logger.debug("Authentication Method:  "+AUTH_TYPE.lower())

########################################################################################
# / pages - User-facing pages
########################################################################################
@app.route('/')
@app.route('/overview')
def overview_page():
    # Some basic sanity checks:
    pass_checks = str(helper.load_checks())
    if pass_checks != "Pass": return redirect(url_for(pass_checks))

    return render_template('overview.html',
        render_page = renderer.render_overview(),
        COLOR_NAV   = COLOR_NAV,
        COLOR_BTN   = COLOR_BTN
    )

@app.route('/machines', methods=('GET', 'POST'))
def machines_page():
    # Some basic sanity checks:
    pass_checks = str(helper.load_checks())
    if pass_checks != "Pass": return redirect(url_for(pass_checks))
    
    cards = renderer.render_machines_cards()
    return render_template('machines.html',
        cards            = cards,
        headscale_server = headscale.get_url(),
        COLOR_NAV   = COLOR_NAV,
        COLOR_BTN   = COLOR_BTN
    )

@app.route('/users', methods=('GET', 'POST'))
def users_page():
    # Some basic sanity checks:
    pass_checks = str(helper.load_checks())
    if pass_checks != "Pass": return redirect(url_for(pass_checks))

    cards = renderer.render_users_cards()
    return render_template('users.html',
        cards = cards,
        headscale_server = headscale.get_url(),
        COLOR_NAV   = COLOR_NAV,
        COLOR_BTN   = COLOR_BTN
    )

@app.route('/settings', methods=('GET', 'POST'))
def settings_page():
    # Some basic sanity checks:
    pass_checks = str(helper.load_checks())
    if pass_checks != "Pass": return redirect(url_for(pass_checks))

    return render_template('settings.html', 
        url          = headscale.get_url(),
        COLOR_NAV    = COLOR_NAV,
        COLOR_BTN    = COLOR_BTN,
        HS_VERSION   = HS_VERSION,
        APP_VERSION  = APP_VERSION,
        GIT_COMMIT   = GIT_COMMIT,
        GIT_BRANCH   = GIT_BRANCH,
        BUILD_DATE   = BUILD_DATE
    )

@app.route('/error')
def error_page():
    if helper.access_checks() == "Pass": 
        return redirect(url_for('overview_page'))

    return render_template('error.html', 
        ERROR_MESSAGE = Markup(helper.access_checks())
    )

########################################################################################
# /api pages
########################################################################################

########################################################################################
# Headscale API Key Endpoints
########################################################################################

@app.route('/api/test_key', methods=('GET', 'POST'))
def test_key_page():
    api_key    = headscale.get_api_key()
    url        = headscale.get_url()

    # Test the API key.  If the test fails, return a failure.  
    status = headscale.test_api_key(url, api_key)
    if status != 200: return "Unauthenticated"

    renewed = headscale.renew_api_key(url, api_key)
    app.logger.warning("The below statement will be TRUE if the key has been renewed or DOES NOT need renewal.  False in all other cases")
    app.logger.warning("Renewed:  "+str(renewed))
    # The key works, let's renew it if it needs it.  If it does, re-read the api_key from the file:
    if renewed: api_key = headscale.get_api_key()

    key_info   = headscale.get_api_key_info(url, api_key)

    # Set the current timezone and local time
    timezone   = pytz.timezone(os.environ["TZ"] if os.environ["TZ"] else "UTC")

    # Format the dates for easy readability
    expiration_parse   = parser.parse(key_info['expiration'])
    expiration_local   = expiration_parse.astimezone(timezone)
    expiration_time    = str(expiration_local.strftime('%A %m/%d/%Y, %H:%M:%S'))+" "+str(timezone)

    creation_parse     = parser.parse(key_info['createdAt'])
    creation_local     = creation_parse.astimezone(timezone)
    creation_time      = str(creation_local.strftime('%A %m/%d/%Y, %H:%M:%S'))+" "+str(timezone)
    
    key_info['expiration'] = expiration_time
    key_info['createdAt']  = creation_time

    message = json.dumps(key_info)
    return message

@app.route('/api/save_key', methods=['POST'])
def save_key_page():
    json_response = request.get_json()
    api_key       = json_response['api_key']
    url           = headscale.get_url()
    file_written  = headscale.set_api_key(api_key)
    message       = ''

    if file_written:
        # Re-read the file and get the new API key and test it
        api_key = headscale.get_api_key()
        test_status = headscale.test_api_key(url, api_key)
        if test_status == 200:
            key_info   = headscale.get_api_key_info(url, api_key)
            expiration = key_info['expiration']
            message = "Key:  '"+api_key+"', Expiration:  "+expiration
            # If the key was saved successfully, test it:
            return "Key saved and tested:  "+message
        else: return "Key failed testing.  Check your key"
    else: return "Key did not save properly.  Check logs"

########################################################################################
# Machine API Endpoints
########################################################################################
@app.route('/api/update_route', methods=['POST'])
def update_route_page():
    json_response = request.get_json()
    route_id      = json_response['route_id']
    url           = headscale.get_url()
    api_key       = headscale.get_api_key()
    current_state = json_response['current_state']

    return headscale.update_route(url, api_key, route_id, current_state)

@app.route('/api/machine_information', methods=['POST'])
def machine_information_page():
    json_response = request.get_json()
    machine_id    = json_response['id']
    url           = headscale.get_url()
    api_key       = headscale.get_api_key()

    return headscale.get_machine_info(url, api_key, machine_id)

@app.route('/api/delete_machine', methods=['POST'])
def delete_machine_page():
    json_response = request.get_json()
    machine_id    = json_response['id']
    url           = headscale.get_url()
    api_key       = headscale.get_api_key()

    return headscale.delete_machine(url, api_key, machine_id)

@app.route('/api/rename_machine', methods=['POST'])
def rename_machine_page():
    json_response = request.get_json()
    machine_id    = json_response['id']
    new_name      = json_response['new_name']
    url           = headscale.get_url()
    api_key       = headscale.get_api_key()

    return headscale.rename_machine(url, api_key, machine_id, new_name)

@app.route('/api/move_user', methods=['POST'])
def move_user_page():
    json_response = request.get_json()
    machine_id    = json_response['id']
    new_user = json_response['new_user']
    url           = headscale.get_url()
    api_key       = headscale.get_api_key()

    return headscale.move_user(url, api_key, machine_id, new_user)

@app.route('/api/set_machine_tags', methods=['POST'])
def set_machine_tags():
    json_response = request.get_json()
    machine_id    = json_response['id']
    machine_tags  = json_response['tags_list']
    url           = headscale.get_url()
    api_key       = headscale.get_api_key()

    return headscale.set_machine_tags(url, api_key, machine_id, machine_tags)

@app.route('/api/register_machine', methods=['POST'])
def register_machine():
    json_response = request.get_json()
    machine_key   = json_response['key']
    user     = json_response['user']
    url           = headscale.get_url()
    api_key       = headscale.get_api_key()

    return str(headscale.register_machine(url, api_key, machine_key, user))

########################################################################################
# User API Endpoints
########################################################################################
@app.route('/api/rename_user', methods=['POST'])
def rename_user_page():
    json_response = request.get_json()
    old_name      = json_response['old_name']
    new_name      = json_response['new_name']
    url           = headscale.get_url()
    api_key       = headscale.get_api_key()

    return headscale.rename_user(url, api_key, old_name, new_name)

@app.route('/api/add_user', methods=['POST'])
def add_user():
    json_response  = json.dumps(request.get_json())
    url            = headscale.get_url()
    api_key        = headscale.get_api_key()

    return headscale.add_user(url, api_key, json_response)

@app.route('/api/delete_user', methods=['POST'])
def delete_user():
    json_response  = request.get_json()
    user_name = json_response['name']
    url            = headscale.get_url()
    api_key        = headscale.get_api_key()

    return headscale.delete_user(url, api_key, user_name)

@app.route('/api/get_users', methods=['POST'])
def get_users_page():
    url           = headscale.get_url()
    api_key       = headscale.get_api_key()
    
    return headscale.get_users(url, api_key)

########################################################################################
# Pre-Auth Key API Endpoints
########################################################################################
@app.route('/api/add_preauth_key', methods=['POST'])
def add_preauth_key():
    json_response  = json.dumps(request.get_json())
    url            = headscale.get_url()
    api_key        = headscale.get_api_key()

    return headscale.add_preauth_key(url, api_key, json_response)

@app.route('/api/expire_preauth_key', methods=['POST'])
def expire_preauth_key():
    json_response  = json.dumps(request.get_json())
    url            = headscale.get_url()
    api_key        = headscale.get_api_key()

    return headscale.expire_preauth_key(url, api_key, json_response)

@app.route('/api/build_preauthkey_table', methods=['POST'])
def build_preauth_key_table():
    json_response  = request.get_json()
    user_name = json_response['name']

    return renderer.build_preauth_key_table(user_name)

########################################################################################
# Main thread
########################################################################################
if __name__ == '__main__':
    app.run(host="0.0.0.0", debug=DEBUG_STATE)
