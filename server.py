# pylint: disable=wrong-import-order

import headscale, helper, json, os, pytz, renderer, secrets, requests, logging
from functools                     import wraps
from datetime                      import datetime
from flask                         import Flask, escape, Markup, redirect, render_template, request, url_for
from dateutil                      import parser
from flask_executor                import Executor
from werkzeug.middleware.proxy_fix import ProxyFix

# Global vars
# Colors:  https://materializecss.com/color.html
COLOR       = os.environ["COLOR"].replace('"', '').lower()
COLOR_NAV   = COLOR+" darken-1"
COLOR_BTN   = COLOR+" darken-3"
AUTH_TYPE   = os.environ["AUTH_TYPE"].replace('"', '').lower()
LOG_LEVEL   = os.environ["LOG_LEVEL"].replace('"', '').upper()
# If LOG_LEVEL is DEBUG, enable Flask debugging:
DEBUG_STATE = True if LOG_LEVEL == "DEBUG" else False

# Initiate the Flask application and logging:
app = Flask(__name__, static_url_path="/static")
match LOG_LEVEL:
    case "DEBUG"   : app.logger.setLevel(logging.DEBUG)
    case "INFO"    : app.logger.setLevel(logging.INFO)
    case "WARNING" : app.logger.setLevel(logging.WARNING)
    case "ERROR"   : app.logger.setLevel(logging.ERROR)
    case "CRITICAL": app.logger.setLevel(logging.CRITICAL)

executor = Executor(app)
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_prefix=1)
app.logger.info("Headscale-WebUI Version:  "+os.environ["APP_VERSION"]+" / "+os.environ["GIT_BRANCH"])
app.logger.info("LOG LEVEL SET TO %s", str(LOG_LEVEL))
app.logger.info("DEBUG STATE:  %s", str(DEBUG_STATE))

########################################################################################
# Set Authentication type.  Currently "OIDC" and "BASIC"
########################################################################################
if AUTH_TYPE == "oidc":
    # Currently using: flask-providers-oidc - https://pypi.org/project/flask-providers-oidc/ 
    #
    # https://gist.github.com/thomasdarimont/145dc9aa857b831ff2eff221b79d179a/ 
    # https://www.authelia.com/integration/openid-connect/introduction/ 
    # https://github.com/steinarvk/flask_oidc_demo 
    app.logger.info("Loading OIDC libraries and configuring app...")

    DOMAIN_NAME    = os.environ["DOMAIN_NAME"]
    BASE_PATH      = os.environ["SCRIPT_NAME"] if os.environ["SCRIPT_NAME"] != "/" else ""
    OIDC_SECRET    = os.environ["OIDC_CLIENT_SECRET"]
    OIDC_CLIENT_ID = os.environ["OIDC_CLIENT_ID"]
    OIDC_AUTH_URL  = os.environ["OIDC_AUTH_URL"]

    # Construct client_secrets.json:
    response = requests.get(str(OIDC_AUTH_URL))
    oidc_info = response.json()
    app.logger.debug("JSON Dumps for OIDC_INFO:  "+json.dumps(oidc_info))

    client_secrets = json.dumps(
        {
            "web": {
                "issuer": oidc_info["issuer"],
                "auth_uri": oidc_info["authorization_endpoint"],
                "client_id": OIDC_CLIENT_ID,
                "client_secret": OIDC_SECRET,
                "redirect_uris": [DOMAIN_NAME + BASE_PATH + "/oidc_callback"],
                "userinfo_uri": oidc_info["userinfo_endpoint"],
                "token_uri": oidc_info["token_endpoint"],
            }
        }
    )

    with open("/app/instance/secrets.json", "w+") as secrets_json:
        secrets_json.write(client_secrets)
    app.logger.debug("Client Secrets:  ")
    with open("/app/instance/secrets.json", "r+") as secrets_json:
        app.logger.debug("/app/instances/secrets.json:")
        app.logger.debug(secrets_json.read())
    
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
    app.logger.info("Loading basic auth libraries and configuring app...")
    from flask_basicauth import BasicAuth

    app.config['BASIC_AUTH_USERNAME'] = os.environ["BASIC_AUTH_USER"].replace('"', '')
    app.config['BASIC_AUTH_PASSWORD'] = os.environ["BASIC_AUTH_PASS"]
    app.config['BASIC_AUTH_FORCE']    = True

    basic_auth = BasicAuth(app)
    ########################################################################################
    # Set Authentication type - Dynamically load function decorators
    # https://stackoverflow.com/questions/17256602/assertionerror-view-function-mapping-is-overwriting-an-existing-endpoint-functi 
    ########################################################################################
    # Make a fake decorator for oidc.require_login
    # If anyone knows a better way of doing this, please let me know.
    class OpenIDConnect():
        def require_login(self, view_func):
            @wraps(view_func)
            def decorated(*args, **kwargs):
                return view_func(*args, **kwargs)
            return decorated
    oidc = OpenIDConnect()

else:
    ########################################################################################
    # Set Authentication type - Dynamically load function decorators
    # https://stackoverflow.com/questions/17256602/assertionerror-view-function-mapping-is-overwriting-an-existing-endpoint-functi 
    ########################################################################################
    # Make a fake decorator for oidc.require_login
    # If anyone knows a better way of doing this, please let me know.
    class OpenIDConnect():
        def require_login(self, view_func):
            @wraps(view_func)
            def decorated(*args, **kwargs):
                return view_func(*args, **kwargs)
            return decorated
    oidc = OpenIDConnect()

########################################################################################
# / pages - User-facing pages
########################################################################################
@app.route('/')
@app.route('/overview')
@oidc.require_login
def overview_page():
    # Some basic sanity checks:
    pass_checks = str(helper.load_checks())
    if pass_checks != "Pass": return redirect(url_for(pass_checks))

    # Check if OIDC is enabled.  If it is, display the buttons:
    OIDC_NAV_DROPDOWN = Markup("")
    OIDC_NAV_MOBILE = Markup("")
    if AUTH_TYPE == "oidc":
        email_address = oidc.user_getfield("email")
        user_name     = oidc.user_getfield("preferred_username")
        name          = oidc.user_getfield("name")
        OIDC_NAV_DROPDOWN = renderer.oidc_nav_dropdown(user_name, email_address, name)
        OIDC_NAV_MOBILE   = renderer.oidc_nav_mobile(user_name, email_address, name)

    return render_template('overview.html',
        render_page       = renderer.render_overview(),
        COLOR_NAV         = COLOR_NAV,
        COLOR_BTN         = COLOR_BTN,
        OIDC_NAV_DROPDOWN = OIDC_NAV_DROPDOWN,
        OIDC_NAV_MOBILE   = OIDC_NAV_MOBILE
    )

@app.route('/routes', methods=('GET', 'POST'))
@oidc.require_login
def routes_page():
    # Some basic sanity checks:
    pass_checks = str(helper.load_checks())
    if pass_checks != "Pass": return redirect(url_for(pass_checks))

    # Check if OIDC is enabled.  If it is, display the buttons:
    OIDC_NAV_DROPDOWN = Markup("")
    OIDC_NAV_MOBILE = Markup("")
    INPAGE_SEARCH = Markup(renderer.render_search())
    if AUTH_TYPE == "oidc":
        email_address = oidc.user_getfield("email")
        user_name     = oidc.user_getfield("preferred_username")
        name          = oidc.user_getfield("name")
        OIDC_NAV_DROPDOWN = renderer.oidc_nav_dropdown(user_name, email_address, name)
        OIDC_NAV_MOBILE   = renderer.oidc_nav_mobile(user_name, email_address, name)
    
    return render_template('routes.html',
        render_page       = renderer.render_routes(),
        COLOR_NAV         = COLOR_NAV,
        COLOR_BTN         = COLOR_BTN,
        OIDC_NAV_DROPDOWN = OIDC_NAV_DROPDOWN,
        OIDC_NAV_MOBILE   = OIDC_NAV_MOBILE
    )


@app.route('/machines', methods=('GET', 'POST'))
@oidc.require_login
def machines_page():
    # Some basic sanity checks:
    pass_checks = str(helper.load_checks())
    if pass_checks != "Pass": return redirect(url_for(pass_checks))

    # Check if OIDC is enabled.  If it is, display the buttons:
    OIDC_NAV_DROPDOWN = Markup("")
    OIDC_NAV_MOBILE = Markup("")
    INPAGE_SEARCH = Markup(renderer.render_search())
    if AUTH_TYPE == "oidc":
        email_address = oidc.user_getfield("email")
        user_name     = oidc.user_getfield("preferred_username")
        name          = oidc.user_getfield("name")
        OIDC_NAV_DROPDOWN = renderer.oidc_nav_dropdown(user_name, email_address, name)
        OIDC_NAV_MOBILE   = renderer.oidc_nav_mobile(user_name, email_address, name)
    
    cards = renderer.render_machines_cards()
    return render_template('machines.html',
        cards             = cards,
        headscale_server  = headscale.get_url(True),
        COLOR_NAV         = COLOR_NAV,
        COLOR_BTN         = COLOR_BTN,
        OIDC_NAV_DROPDOWN = OIDC_NAV_DROPDOWN,
        OIDC_NAV_MOBILE   = OIDC_NAV_MOBILE,
        INPAGE_SEARCH     = INPAGE_SEARCH
    )

@app.route('/users', methods=('GET', 'POST'))
@oidc.require_login
def users_page():
    # Some basic sanity checks:
    pass_checks = str(helper.load_checks())
    if pass_checks != "Pass": return redirect(url_for(pass_checks))

    # Check if OIDC is enabled.  If it is, display the buttons:
    OIDC_NAV_DROPDOWN = Markup("")
    OIDC_NAV_MOBILE = Markup("")
    INPAGE_SEARCH = Markup(renderer.render_search())
    if AUTH_TYPE == "oidc":
        email_address = oidc.user_getfield("email")
        user_name     = oidc.user_getfield("preferred_username")
        name          = oidc.user_getfield("name")
        OIDC_NAV_DROPDOWN = renderer.oidc_nav_dropdown(user_name, email_address, name)
        OIDC_NAV_MOBILE   = renderer.oidc_nav_mobile(user_name, email_address, name)

    cards = renderer.render_users_cards()
    return render_template('users.html',
        cards             = cards,
        COLOR_NAV         = COLOR_NAV,
        COLOR_BTN         = COLOR_BTN,
        OIDC_NAV_DROPDOWN = OIDC_NAV_DROPDOWN,
        OIDC_NAV_MOBILE   = OIDC_NAV_MOBILE,
        INPAGE_SEARCH     = INPAGE_SEARCH
    )

@app.route('/settings', methods=('GET', 'POST'))
@oidc.require_login
def settings_page():
    # Some basic sanity checks:
    pass_checks = str(helper.load_checks())
    if pass_checks != "Pass" and pass_checks != "settings_page": 
        return redirect(url_for(pass_checks))

    # Check if OIDC is enabled.  If it is, display the buttons:
    OIDC_NAV_DROPDOWN = Markup("")
    OIDC_NAV_MOBILE = Markup("")
    if AUTH_TYPE == "oidc":
        email_address = oidc.user_getfield("email")
        user_name     = oidc.user_getfield("preferred_username")
        name          = oidc.user_getfield("name")
        OIDC_NAV_DROPDOWN = renderer.oidc_nav_dropdown(user_name, email_address, name)
        OIDC_NAV_MOBILE   = renderer.oidc_nav_mobile(user_name, email_address, name)

    GIT_COMMIT_LINK = Markup("<a href='https://github.com/iFargle/headscale-webui/commit/"+os.environ["GIT_COMMIT"]+"'>"+str(os.environ["GIT_COMMIT"])[0:7]+"</a>")

    return render_template('settings.html', 
        url          = headscale.get_url(),
        COLOR_NAV    = COLOR_NAV,
        COLOR_BTN    = COLOR_BTN,
        OIDC_NAV_DROPDOWN = OIDC_NAV_DROPDOWN,
        OIDC_NAV_MOBILE = OIDC_NAV_MOBILE,
        BUILD_DATE   = os.environ["BUILD_DATE"],
        APP_VERSION  = os.environ["APP_VERSION"],
        GIT_COMMIT   = GIT_COMMIT_LINK,
        GIT_BRANCH   = os.environ["GIT_BRANCH"],
        HS_VERSION   = os.environ["HS_VERSION"]
    )

@app.route('/error')
@oidc.require_login
def error_page():
    if helper.access_checks() == "Pass": 
        return redirect(url_for('overview_page'))

    return render_template('error.html', 
        ERROR_MESSAGE = Markup(helper.access_checks())
    )

@app.route('/logout')
def logout_page():
    if AUTH_TYPE == "oidc":
        oidc.logout()
    return redirect(url_for('overview_page'))
########################################################################################
# /api pages
########################################################################################

########################################################################################
# Headscale API Key Endpoints
########################################################################################

@app.route('/api/test_key', methods=('GET', 'POST'))
@oidc.require_login
def test_key_page():
    api_key    = headscale.get_api_key()
    url        = headscale.get_url()

    # Test the API key.  If the test fails, return a failure.  
    status = headscale.test_api_key(url, api_key)
    if status != 200: return "Unauthenticated"

    renewed = headscale.renew_api_key(url, api_key)
    app.logger.warning("The below statement will be TRUE if the key has been renewed, ")
    app.logger.warning("or DOES NOT need renewal.  False in all other cases")
    app.logger.warning("Renewed:  "+str(renewed))
    # The key works, let's renew it if it needs it.  If it does, re-read the api_key from the file:
    if renewed: api_key = headscale.get_api_key()

    key_info   = headscale.get_api_key_info(url, api_key)

    # Set the current timezone and local time
    timezone   = pytz.timezone(os.environ["TZ"] if os.environ["TZ"] else "UTC")
    local_time = timezone.localize(datetime.now())

    # Format the dates for easy readability
    creation_parse   = parser.parse(key_info['createdAt'])
    creation_local   = creation_parse.astimezone(timezone)
    creation_delta   = local_time - creation_local
    creation_print   = helper.pretty_print_duration(creation_delta)
    creation_time    = str(creation_local.strftime('%A %m/%d/%Y, %H:%M:%S'))+" "+str(timezone)+" ("+str(creation_print)+")"

    expiration_parse = parser.parse(key_info['expiration'])
    expiration_local = expiration_parse.astimezone(timezone)
    expiration_delta = expiration_local - local_time
    expiration_print = helper.pretty_print_duration(expiration_delta, "expiry")
    expiration_time  = str(expiration_local.strftime('%A %m/%d/%Y, %H:%M:%S'))+" "+str(timezone)+" ("+str(expiration_print)+")"

    key_info['expiration'] = expiration_time
    key_info['createdAt']  = creation_time

    message = json.dumps(key_info)
    return message

@app.route('/api/save_key', methods=['POST'])
@oidc.require_login
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
@oidc.require_login
def update_route_page():
    json_response = request.get_json()
    route_id      = escape(json_response['route_id'])
    url           = headscale.get_url()
    api_key       = headscale.get_api_key()
    current_state = json_response['current_state']

    return headscale.update_route(url, api_key, route_id, current_state)

@app.route('/api/machine_information', methods=['POST'])
@oidc.require_login
def machine_information_page():
    json_response = request.get_json()
    machine_id    = escape(json_response['id'])
    url           = headscale.get_url()
    api_key       = headscale.get_api_key()

    return headscale.get_machine_info(url, api_key, machine_id)

@app.route('/api/delete_machine', methods=['POST'])
@oidc.require_login
def delete_machine_page():
    json_response = request.get_json()
    machine_id    = escape(json_response['id'])
    url           = headscale.get_url()
    api_key       = headscale.get_api_key()

    return headscale.delete_machine(url, api_key, machine_id)

@app.route('/api/rename_machine', methods=['POST'])
@oidc.require_login
def rename_machine_page():
    json_response = request.get_json()
    machine_id    = escape(json_response['id'])
    new_name      = escape(json_response['new_name'])
    url           = headscale.get_url()
    api_key       = headscale.get_api_key()

    return headscale.rename_machine(url, api_key, machine_id, new_name)

@app.route('/api/move_user', methods=['POST'])
@oidc.require_login
def move_user_page():
    json_response = request.get_json()
    machine_id    = escape(json_response['id'])
    new_user      = escape(json_response['new_user'])
    url           = headscale.get_url()
    api_key       = headscale.get_api_key()

    return headscale.move_user(url, api_key, machine_id, new_user)

@app.route('/api/set_machine_tags', methods=['POST'])
@oidc.require_login
def set_machine_tags():
    json_response = request.get_json()
    machine_id    = escape(json_response['id'])
    machine_tags  = json_response['tags_list']
    url           = headscale.get_url()
    api_key       = headscale.get_api_key()

    return headscale.set_machine_tags(url, api_key, machine_id, machine_tags)

@app.route('/api/register_machine', methods=['POST'])
@oidc.require_login
def register_machine():
    json_response = request.get_json()
    machine_key   = escape(json_response['key'])
    user          = escape(json_response['user'])
    url           = headscale.get_url()
    api_key       = headscale.get_api_key()

    return headscale.register_machine(url, api_key, machine_key, user)

########################################################################################
# User API Endpoints
########################################################################################
@app.route('/api/rename_user', methods=['POST'])
@oidc.require_login
def rename_user_page():
    json_response = request.get_json()
    old_name      = escape(json_response['old_name'])
    new_name      = escape(json_response['new_name'])
    url           = headscale.get_url()
    api_key       = headscale.get_api_key()

    return headscale.rename_user(url, api_key, old_name, new_name)

@app.route('/api/add_user', methods=['POST'])
@oidc.require_login
def add_user():
    json_response  = request.get_json()
    user_name      = str(escape(json_response['name']))
    url            = headscale.get_url()
    api_key        = headscale.get_api_key()
    json_string    = '{"name": "'+user_name+'"}'

    return headscale.add_user(url, api_key, json_string)

@app.route('/api/delete_user', methods=['POST'])
@oidc.require_login
def delete_user():
    json_response  = request.get_json()
    user_name      = str(escape(json_response['name']))
    url            = headscale.get_url()
    api_key        = headscale.get_api_key()

    return headscale.delete_user(url, api_key, user_name)

@app.route('/api/get_users', methods=['POST'])
@oidc.require_login
def get_users_page():
    url           = headscale.get_url()
    api_key       = headscale.get_api_key()
    
    return headscale.get_users(url, api_key)

########################################################################################
# Pre-Auth Key API Endpoints
########################################################################################
@app.route('/api/add_preauth_key', methods=['POST'])
@oidc.require_login
def add_preauth_key():
    json_response  = json.dumps(request.get_json())
    url            = headscale.get_url()
    api_key        = headscale.get_api_key()

    return headscale.add_preauth_key(url, api_key, json_response)

@app.route('/api/expire_preauth_key', methods=['POST'])
@oidc.require_login
def expire_preauth_key():
    json_response  = json.dumps(request.get_json())
    url            = headscale.get_url()
    api_key        = headscale.get_api_key()

    return headscale.expire_preauth_key(url, api_key, json_response)

@app.route('/api/build_preauthkey_table', methods=['POST'])
@oidc.require_login
def build_preauth_key_table():
    json_response  = request.get_json()
    user_name      = str(escape(json_response['name']))

    return renderer.build_preauth_key_table(user_name)

########################################################################################
# Route API Endpoints
########################################################################################
@app.route('/api/get_routes', methods=['POST'])
@oidc.require_login
def get_route_info():
    url     = headscale.get_url()
    api_key = headscale.get_api_key()

    return headscale.get_routes(url, api_key)


########################################################################################
# Main thread
########################################################################################
if __name__ == '__main__':
    app.run(host="0.0.0.0", debug=DEBUG_STATE)
