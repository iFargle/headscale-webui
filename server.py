# pylint: disable=wrong-import-order

import headscale, helper, json, os, pytz, renderer, secrets, urllib
from functools      import wraps
from flask          import Flask, Markup, redirect, render_template, request, url_for, logging
from dateutil       import parser
from flask_executor import Executor

# Global vars
# Colors:  https://materializecss.com/color.html
COLOR           = os.environ["COLOR"].replace('"', '')
COLOR_NAV       = COLOR+" darken-1"
COLOR_BTN       = COLOR+" darken-3"
DEBUG_STATE     = True
AUTH_TYPE       = os.environ["AUTH_TYPE"].replace('"', '').lower()
STATIC_URL_PATH = "/static"

# Initiate the Flask application:
app = Flask(__name__, static_url_path=STATIC_URL_PATH)
LOG = logging.create_logger(app)
executor = Executor(app)

########################################################################################
# Set Authentication type.  Currently "OIDC" and "BASIC"
########################################################################################
if AUTH_TYPE == "oidc":
    # Currently using: flask-providers-oidc - https://pypi.org/project/flask-providers-oidc/ 
    #
    # https://gist.github.com/thomasdarimont/145dc9aa857b831ff2eff221b79d179a/ 
    # https://www.authelia.com/integration/openid-connect/introduction/ 
    # https://github.com/steinarvk/flask_oidc_demo 
    LOG.error("Loading OIDC libraries and configuring app...")

    DOMAIN_NAME       = os.environ["DOMAIN_NAME"]
    BASE_PATH         = os.environ["SCRIPT_NAME"] if os.environ["SCRIPT_NAME"] != "/" else ""
    OIDC_ISSUER       = os.environ["OIDC_ISSUER"].replace('"','')
    OIDC_SECRET       = os.environ["OIDC_CLIENT_SECRET"]
    OIDC_CLIENT_ID    = os.environ["OIDC_CLIENT_ID"]
    # Construct client_secrets.json:
    client_secrets = """{
        "web": {
            "issuer": \""""+OIDC_ISSUER+"""",
            "auth_uri": \""""+OIDC_ISSUER+"""/api/oidc/authorization",
            "client_id": \""""+OIDC_CLIENT_ID+"""",
            "client_secret": \""""+OIDC_SECRET+"""",
            "redirect_uris": [
                \""""+DOMAIN_NAME+BASE_PATH+"""/oidc_callback"
            ],
            "userinfo_uri": \""""+OIDC_ISSUER+"""/api/oidc/userinfo", 
            "token_uri": \""""+OIDC_ISSUER+"""/api/oidc/token",
            "token_introspection_uri": \""""+OIDC_ISSUER+"""/api/oidc/introspection"
        }
    }
    """

    with open("/app/instance/secrets.json", "w+") as secrets_json:
        secrets_json.write(client_secrets)
    
    app.config.update({
        'SECRET_KEY': secrets.token_urlsafe(32),
        'TESTING': DEBUG_STATE,
        'DEBUG': DEBUG_STATE,
        'OIDC_CLIENT_SECRETS': '/app/instance/secrets.json',
        'OIDC_ID_TOKEN_COOKIE_SECURE': True,
        'OIDC_REQUIRE_VERIFIED_EMAIL': False,
        'OIDC_USER_INFO_ENABLED': True,
        'OIDC_OPENID_REALM': 'Headscale-WebUI',
        'OIDC_SCOPES': ['openid', 'profile', 'email'],
        'OIDC_INTROSPECTION_AUTH_METHOD': 'client_secret_post'
    })
    from flask_oidc import OpenIDConnect
    oidc = OpenIDConnect(app)

elif AUTH_TYPE == "basic":
    # https://flask-basicauth.readthedocs.io/en/latest/
    LOG.error("Loading basic auth libraries and configuring app...")
    from flask_basicauth import BasicAuth

    app.config['BASIC_AUTH_USERNAME'] = os.environ["BASIC_AUTH_USER"].replace('"', '')
    app.config['BASIC_AUTH_PASSWORD'] = os.environ["BASIC_AUTH_PASS"]
    app.config['BASIC_AUTH_FORCE']    = True

    basic_auth = BasicAuth(app)

########################################################################################
# Set Authentication type - Dynamically load function decorators
# https://wiki.python.org/moin/PythonDecoratorLibrary#Enable.2FDisable_Decorators 
########################################################################################
def enable_oidc(func):
    def decorator_enable_oidc(func):
        def wrapper_decorator_enable_oidc():
            if AUTH_TYPE != "oidc":
                func()
                return
            oidc.require_login(func)
            func()
        return wrapper_decorator_enable_oidc
    return decorator_enable_oidc
########################################################################################
# / pages - User-facing pages
########################################################################################
@app.route('/')
@app.route('/overview')
@enable_oidc
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
@enable_oidc
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
@enable_oidc
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
@enable_oidc
def settings_page():
    # Some basic sanity checks:
    pass_checks = str(helper.load_checks())
    if pass_checks != "Pass": return redirect(url_for(pass_checks))

    return render_template('settings.html', 
        url          = headscale.get_url(),
        COLOR_NAV    = COLOR_NAV,
        COLOR_BTN    = COLOR_BTN,
        BUILD_DATE   = os.environ["BUILD_DATE"],
        APP_VERSION  = os.environ["APP_VERSION"],
        GIT_COMMIT   = os.environ["GIT_COMMIT"],
        GIT_BRANCH   = os.environ["GIT_BRANCH"],
        HS_VERSION   = os.environ["HS_VERSION"]
    )

@app.route('/error')
@enable_oidc
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
@enable_oidc
def test_key_page():
    api_key    = headscale.get_api_key()
    url        = headscale.get_url()

    # Test the API key.  If the test fails, return a failure.  
    status = headscale.test_api_key(url, api_key)
    if status != 200: return "Unauthenticated"

    renewed = headscale.renew_api_key(url, api_key)
    LOG.warning("The below statement will be TRUE if the key has been renewed, ")
    LOG.warning("or DOES NOT need renewal.  False in all other cases")
    LOG.warning("Renewed:  "+str(renewed))
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
@enable_oidc
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
@enable_oidc
def update_route_page():
    json_response = request.get_json()
    route_id      = json_response['route_id']
    url           = headscale.get_url()
    api_key       = headscale.get_api_key()
    current_state = json_response['current_state']

    return headscale.update_route(url, api_key, route_id, current_state)

@app.route('/api/machine_information', methods=['POST'])
@enable_oidc
def machine_information_page():
    json_response = request.get_json()
    machine_id    = json_response['id']
    url           = headscale.get_url()
    api_key       = headscale.get_api_key()

    return headscale.get_machine_info(url, api_key, machine_id)

@app.route('/api/delete_machine', methods=['POST'])
@enable_oidc
def delete_machine_page():
    json_response = request.get_json()
    machine_id    = json_response['id']
    url           = headscale.get_url()
    api_key       = headscale.get_api_key()

    return headscale.delete_machine(url, api_key, machine_id)

@app.route('/api/rename_machine', methods=['POST'])
@enable_oidc
def rename_machine_page():
    json_response = request.get_json()
    machine_id    = json_response['id']
    new_name      = json_response['new_name']
    url           = headscale.get_url()
    api_key       = headscale.get_api_key()

    return headscale.rename_machine(url, api_key, machine_id, new_name)

@app.route('/api/move_user', methods=['POST'])
@enable_oidc
def move_user_page():
    json_response = request.get_json()
    machine_id    = json_response['id']
    new_user = json_response['new_user']
    url           = headscale.get_url()
    api_key       = headscale.get_api_key()

    return headscale.move_user(url, api_key, machine_id, new_user)

@app.route('/api/set_machine_tags', methods=['POST'])
@enable_oidc
def set_machine_tags():
    json_response = request.get_json()
    machine_id    = json_response['id']
    machine_tags  = json_response['tags_list']
    url           = headscale.get_url()
    api_key       = headscale.get_api_key()

    return headscale.set_machine_tags(url, api_key, machine_id, machine_tags)

@app.route('/api/register_machine', methods=['POST'])
@enable_oidc
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
@enable_oidc
def rename_user_page():
    json_response = request.get_json()
    old_name      = json_response['old_name']
    new_name      = json_response['new_name']
    url           = headscale.get_url()
    api_key       = headscale.get_api_key()

    return headscale.rename_user(url, api_key, old_name, new_name)

@app.route('/api/add_user', methods=['POST'])
@enable_oidc
def add_user():
    json_response  = json.dumps(request.get_json())
    url            = headscale.get_url()
    api_key        = headscale.get_api_key()

    return headscale.add_user(url, api_key, json_response)

@app.route('/api/delete_user', methods=['POST'])
@enable_oidc
def delete_user():
    json_response  = request.get_json()
    user_name = json_response['name']
    url            = headscale.get_url()
    api_key        = headscale.get_api_key()

    return headscale.delete_user(url, api_key, user_name)

@app.route('/api/get_users', methods=['POST'])
@enable_oidc
def get_users_page():
    url           = headscale.get_url()
    api_key       = headscale.get_api_key()
    
    return headscale.get_users(url, api_key)

########################################################################################
# Pre-Auth Key API Endpoints
########################################################################################
@app.route('/api/add_preauth_key', methods=['POST'])
@enable_oidc
def add_preauth_key():
    json_response  = json.dumps(request.get_json())
    url            = headscale.get_url()
    api_key        = headscale.get_api_key()

    return headscale.add_preauth_key(url, api_key, json_response)

@app.route('/api/expire_preauth_key', methods=['POST'])
@enable_oidc
def expire_preauth_key():
    json_response  = json.dumps(request.get_json())
    url            = headscale.get_url()
    api_key        = headscale.get_api_key()

    return headscale.expire_preauth_key(url, api_key, json_response)

@app.route('/api/build_preauthkey_table', methods=['POST'])
@enable_oidc
def build_preauth_key_table():
    json_response  = request.get_json()
    user_name = json_response['name']

    return renderer.build_preauth_key_table(user_name)

########################################################################################
# Main thread
########################################################################################
if __name__ == '__main__':
    app.run(host="0.0.0.0", debug=DEBUG_STATE)
