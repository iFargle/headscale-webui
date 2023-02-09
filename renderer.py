import headscale, helper, json, logging, sys, pytz, os, time, yaml
from flask    import Markup, render_template, Flask
from datetime import datetime, timedelta, date
from dateutil import parser

# Threading to speed things up
from concurrent.futures import wait, ALL_COMPLETED
from flask_executor import Executor

app = Flask(__name__)
executor = Executor(app)

log = logging.getLogger('server.renderer')

def render_overview():
    url           = headscale.get_url()
    api_key       = headscale.get_api_key()

    timezone         = pytz.timezone(os.environ["TZ"] if os.environ["TZ"] else "UTC")
    local_time       = timezone.localize(datetime.now())
    
    # Overview page will just read static information from the config file and display it
    # Open the config.yaml and parse it.
    config_file = open("/etc/headscale/config.yaml", "r")
    config_yaml = yaml.safe_load(config_file)

    # Get and display the following information:
    # Overview of the server's machines, users, preauth keys, API key expiration, server version
    
    # Get all machines:
    machines_count = 0
    machines = headscale.get_machines(url, api_key)
    for machine in machines["machines"]:
        machines_count += 1

    # Get all routes:
    routes = headscale.get_routes(url,api_key)
    total_routes = len(routes["routes"])
    enabled_routes = 0
    for route in routes["routes"]:
        if route["enabled"] and route['advertised']: 
            enabled_routes += 1

    # Get a count of all enabled exit routes
    exits_count = 0
    exits_enabled_count = 0
    for route in routes["routes"]:
        if route['advertised']:
            if route["prefix"] == "0.0.0.0/0" or route["prefix"] == "::/0":
                exits_count +=1
                if route["enabled"]:
                    exits_enabled_count += 1

    # Get User and PreAuth Key counts
    user_count   = 0
    usable_keys_count = 0
    users = headscale.get_users(url, api_key)
    for user in users["users"]:
        user_count +=1
        preauth_keys = headscale.get_preauth_keys(url, api_key, user["name"])
        for key in preauth_keys["preAuthKeys"]:
            expiration_parse = parser.parse(key["expiration"])
            key_expired = True if expiration_parse < local_time else False
            if key["reusable"] and not key_expired: usable_keys_count += 1
            if not key["reusable"] and not key["used"] and not key_expired: usable_keys_count += 1

    overview_content  = """
        <div class="col s12 m6">
            <div class="card hoverable">
                <div class="card-content">
                    <span class="card-title">Stats</span>
                    <p>
                        <table>
                            <tr><td> Machines Added      </td><td> """+ str(machines_count)    +""" </td></tr>
                            <tr><td> Users          </td><td> """+ str(user_count)   +""" </td></tr>
                            <tr><td> Usable PreAuth Keys </td><td> """+ str(usable_keys_count) +""" </td></tr>
                            <tr><td> Enabled/Total Routes</td><td> """+ str(enabled_routes) +"""/"""+str(total_routes)+""" </td></tr>
                            <tr><td> Enabled/Total Exits</td><td> """+ str(exits_enabled_count) +"""/"""+str(exits_count)+""" </td></tr>
                        </table>
                    </p>
                </div>
            </div>
        </div>
    """
    # Overview of general configs from the YAML
    general_content  = """
        <div class="col s12 m6">
            <div class="card hoverable">
                <div class="card-content">
                    <span class="card-title">General</span>
                    <p>
                        <table>
                            <tr><td> IP Prefixes                </td><td> """+str(config_yaml["ip_prefixes"])                       +""" </td></tr>
                            <tr><td> Server URL                 </td><td> """+str(config_yaml["server_url"])                        +""" </td></tr>
                            <tr><td> Updates Disabled?          </td><td> """+str(config_yaml["disable_check_updates"])             +""" </td></tr>
                            <tr><td> Ephemeral Node Timeout     </td><td> """+str(config_yaml["ephemeral_node_inactivity_timeout"]) +""" </td></tr>
                            <tr><td> Node Update Check Interval </td><td> """+str(config_yaml["node_update_check_interval"])        +""" </td></tr>
                        </table>
                    </p>
                </div>
            </div>
        </div>
    """

    #     Whether OIDC is configured
    if config_yaml["oidc"]:
        oidc_content  = """
            <div class="col s12 m6">
                <div class="card hoverable">
                    <div class="card-content">
                        <span class="card-title">OIDC</span>
                        <p>
                            <table>   
                                <tr><td> Issuer             </td><td> """+str(config_yaml["oidc"]["issuer"])            +""" </td></tr>
                                <tr><td> Client ID          </td><td> """+str(config_yaml["oidc"]["client_id"])         +""" </td></tr>
                                <tr><td> Scope              </td><td> """+str(config_yaml["oidc"]["scope"])             +""" </td></tr>
                                <tr><td> Allowed Domains    </td><td> """+str(config_yaml["oidc"]["allowed_domains"])   +""" </td></tr>
                                <tr><td> Strip Email Domain </td><td> """+str(config_yaml["oidc"]["strip_email_domain"])+""" </td></tr>
                            </table>
                        </p>
                    </div>
                </div>
            </div>
        """

    if config_yaml["derp"]["server"]:
        derp_content  = """
            <div class="col s12 m6">
                <div class="card hoverable">
                    <div class="card-content">
                        <span class="card-title">Built-in DERP</span>
                        <p>
                            <table>
                                <tr><td> Enabled      </td><td> """+str(config_yaml["derp"]["server"]["enabled"])          +""" </td></tr>
                                <tr><td> Region ID    </td><td> """+str(config_yaml["derp"]["server"]["region_id"])        +""" </td></tr>
                                <tr><td> Region Code  </td><td> """+str(config_yaml["derp"]["server"]["region_code"])      +""" </td></tr>
                                <tr><td> Region Name  </td><td> """+str(config_yaml["derp"]["server"]["region_name"])      +""" </td></tr>
                                <tr><td> STUN Address </td><td> """+str(config_yaml["derp"]["server"]["stun_listen_addr"]) +""" </td></tr>
                            </table>
                        </p>
                    </div>
                </div>
            </div>
        """

    #     Whether there are custom DERP servers
    #         If there are custom DERP servers, get the file location from the config file.  Assume mapping is the same.
    #     Whether the built-in DERP server is enabled 
    #     The IP prefixes
    #     The DNS config
    if config_yaml["dns_config"]:
        dns_content  = """
            <div class="col s12 m6">
                <div class="card hoverable">
                    <div class="card-content">
                        <span class="card-title">DNS</span>
                        <p>
                            <table>
                                <tr><td> Nameservers </td><td> """+str(config_yaml["dns_config"]["nameservers"])+""" </td></tr>
                                <tr><td> MagicDNS    </td><td> """+str(config_yaml["dns_config"]["magic_dns"])  +""" </td></tr>
                                <tr><td> Domains     </td><td> """+str(config_yaml["dns_config"]["domains"])    +""" </td></tr>
                                <tr><td> Base Domain </td><td> """+str(config_yaml["dns_config"]["base_domain"])+""" </td></tr>
                                <tr><td> </td><td><br></td></tr>
                            </table>
                        </p>
                    </div>
                </div>
            </div>
        """
    if config_yaml["derp"]["paths"]: pass
    #   # open the path:
    #   derp_file = 
    #   config_file = open("/etc/headscale/config.yaml", "r")
    #   config_yaml = yaml.safe_load(config_file)
    #     The ACME config, if not empty
    #     Whether updates are running
    #     Whether metrics are enabled (and their listen addr)
    #     The log level
    #     What kind of Database is being used to drive headscale

    content = "<br><div class='row'>" + overview_content + general_content + derp_content + oidc_content + dns_content + "</div>"
    return Markup(content)

def thread_machine_content(machine, machine_content, idx):
    # machine      = passed in machine information
    # content      = place to write the content

    url           = headscale.get_url()
    api_key       = headscale.get_api_key()

    # Set the current timezone and local time
    timezone = pytz.timezone(os.environ["TZ"] if os.environ["TZ"] else "UTC")
    local_time      = timezone.localize(datetime.now())

    # Get the machines routes
    pulled_routes = headscale.get_machine_routes(url, api_key, machine["id"])
    routes = ""

# New format to parse:
# New JSON endpoint requires a machine_id and a route_id to toggle.
# Pass the following info:
#  1.  Machine ID
#  2.  Route ID (NEW REQ)
#  3.  Route State (NEW REQ) - This would be the JSON key of pulled_routes["routes"][index][enabled]
# {
#   "routes": [
#     { <INDEX>
#       "id": "1",
#       "prefix": "0.0.0.0/0",
#       "advertised": true,
#       "enabled": true,
#     },

    # Test if the machine is an exit node:
    exit_node = False
    # If the LENGTH of "routes" is NULL/0, there are no routes, enabled or disabled:
    if len(pulled_routes["routes"]) > 0:
        advertised_and_enabled = False
        advertised_route = False
        # First, check if there are any routes that are both enabled and advertised
        for route in pulled_routes["routes"]:
            if route ["advertised"] and route["enabled"]: 
                advertised_and_enabled = True
            if route["advertised"]:
                advertised_route = True
        if advertised_and_enabled or advertised_route:
            routes = """
                <li class="collection-item avatar">
                    <i class="material-icons circle">directions</i>
                    <span class="title">Routes</span>
                    <p><div>
            """
            for route in pulled_routes["routes"]:
                # log.info("Route:  ["+str(route['machine']['name'])+"] id: "+str(route['id'])+" / prefix: "+str(route['prefix'])+" enabled?:  "+str(route['enabled']))
                # Check if the route is enabled:
                route_enabled = "red"
                route_tooltip = 'enable'
                if route["enabled"]:
                    route_enabled = "green"
                    route_tooltip = 'disable'
                    if route["prefix"] == "0.0.0.0/0" or route["prefix"] == "::/0" and str(route["enabled"]) == "True":
                        exit_node = True
                routes = routes+"""
                <p 
                    class='waves-effect waves-light btn-small """+route_enabled+""" lighten-2 tooltipped'
                    data-position='top' data-tooltip='Click to """+route_tooltip+"""'
                    id='"""+route['id']+"""'
                    onclick="toggle_route("""+route['id']+""", '"""+str(route['enabled'])+"""')">
                    """+route['prefix']+"""
                </p>
                """
            routes = routes+"</div></p></li>"
# This entire thing will probably need to change after the new API endpoint change.
# Old code for v1.17.0
#    # Test if the machine is an exit node:
#    exit_node = False
#    # If there are ANY advertised routes, print them:
#    if len(pulled_routes["routes"]["advertisedRoutes"]) > 0:
#        routes = """
#            <li class="collection-item avatar">
#                <i class="material-icons circle">directions</i>
#                <span class="title">Routes</span>
#                <p><div>
#        """
#        for advertised_route in pulled_routes["routes"]["advertisedRoutes"]:
#            # Check if the route has been enabled.  Red for False, Green for True 
#            route_enabled = "red"
#            route_tooltip = 'enable'
#            for enabled_route in pulled_routes["routes"]["enabledRoutes"]:
#                if advertised_route == enabled_route: 
#                    route_enabled = "green"
#                    route_tooltip = 'disable'
#            if (advertised_route == "0.0.0.0/0" or advertised_route == "::/0") and route_enabled == "green": 
#                exit_node = True
#            routes = routes+"""
#            <p 
#                class='waves-effect waves-light btn-small """+route_enabled+""" lighten-2 tooltipped'
#                data-position='top' data-tooltip='Click to """+route_tooltip+"""'
#                id='"""+machine['id']+"""-"""+advertised_route+"""'
#                onclick="toggle_route("""+machine['id']+""", '"""+advertised_route+"""')">
#                """+advertised_route+"""
#            </p>
#            """
#        routes = routes+"</div></p></li>"

    # Get machine tags
    tag_array = ""
    for tag in machine["forcedTags"]: tag_array = tag_array+"{tag: '"+tag[4:]+"'}, "
    tags = """
        <li class="collection-item avatar">
            <i class="material-icons circle tooltipped" data-position="right" data-tooltip="Spaces will be replaced with a dash (-) upon page refresh">label</i>
            <span class="title">Tags</span>
            <p><div style='margin: 0px' class='chips' id='"""+machine["id"]+"""-tags'></div></p>
        </li>
        <script>
            window.addEventListener('load', 
                function() { 
                    var instances = M.Chips.init ( 
                        document.getElementById('"""+machine['id']+"""-tags'),  ({
                            data:["""+tag_array+"""], 
                            onChipDelete() { delete_chip("""+machine["id"]+""", this.chipsData) }, 
                            onChipAdd()    { add_chip("""+machine["id"]+""",    this.chipsData) }
                        }) 
                    );
                }, false
            ); 
        </script>
        """

    # Get the machine IP's
    machine_ips = "<ul>"
    for ip in machine["ipAddresses"]:
        machine_ips = machine_ips+"<li>"+ip+"</li>"
    machine_ips = machine_ips+"</ul>"

    # Format the dates for easy readability
    last_seen_parse   = parser.parse(machine["lastSeen"])
    last_seen_local   = last_seen_parse.astimezone(timezone)
    last_seen_delta   = local_time - last_seen_local
    last_seen_print   = helper.pretty_print_duration(last_seen_delta)
    last_seen_time    = str(last_seen_local.strftime('%A %m/%d/%Y, %H:%M:%S'))+" "+str(timezone)+" ("+str(last_seen_print)+")"
    
    last_update_parse = local_time if machine["lastSuccessfulUpdate"] is None else parser.parse(machine["lastSuccessfulUpdate"])
    last_update_local = last_update_parse.astimezone(timezone)
    last_update_delta = local_time - last_update_local
    last_update_print = helper.pretty_print_duration(last_update_delta)
    last_update_time  = str(last_update_local.strftime('%A %m/%d/%Y, %H:%M:%S'))+" "+str(timezone)+" ("+str(last_update_print)+")"

    created_parse     = parser.parse(machine["createdAt"])
    created_local     = created_parse.astimezone(timezone)
    created_delta     = local_time - created_local
    created_print     = helper.pretty_print_duration(created_delta)
    created_time      = str(created_local.strftime('%A %m/%d/%Y, %H:%M:%S'))+" "+str(timezone)+" ("+str(created_print)+")"

    # Get the first 10 characters of the PreAuth Key:
    if machine["preAuthKey"]:
        preauth_key = str(machine["preAuthKey"]["key"])[0:10]
    else: preauth_key = "None"

    # Set the status badge color:
    text_color = helper.text_color_duration(last_seen_delta)
    # Set the user badge color:
    user_color = helper.get_color(int(machine["user"]["id"]))

    # Generate the various badges:
    status_badge      = "<i class='material-icons left tooltipped "+text_color+"' data-position='top' data-tooltip='Last Seen:  "+last_seen_print+"' id='"+machine["id"]+"-status'>fiber_manual_record</i>"
    user_badge   = "<span class='badge ipinfo " + user_color + " white-text hide-on-small-only' id='"+machine["id"]+"-ns-badge'>"+machine["user"]["name"]+"</span>"
    exit_node_badge   = "" if not exit_node else "<span class='badge grey white-text text-lighten-4 tooltipped' data-position='left' data-tooltip='This machine has an enabled exit route.'>Exit Node</span>"


    machine_content[idx] = (str(render_template(
        'machines_card.html', 
        given_name        = machine["givenName"],
        machine_id        = machine["id"],
        hostname          = machine["name"],
        ns_name           = machine["user"]["name"],
        ns_id             = machine["user"]["id"],
        ns_created        = machine["user"]["createdAt"],
        last_seen         = str(last_seen_print),
        last_update       = str(last_update_print),
        machine_ips       = Markup(machine_ips),
        advertised_routes = Markup(routes),
        exit_node_badge   = Markup(exit_node_badge),
        status_badge      = Markup(status_badge),
        user_badge   = Markup(user_badge),
        last_update_time  = str(last_update_time),
        last_seen_time    = str(last_seen_time),
        created_time      = str(created_time),
        preauth_key       = str(preauth_key),
        machine_tags      = Markup(tags),
    )))
    log.info("Finished thread for machine "+machine["givenName"]+" index "+str(idx))

# Render the cards for the machines page:
def render_machines_cards():
    url           = headscale.get_url()
    api_key       = headscale.get_api_key()
    machines_list = headscale.get_machines(url, api_key)

    #########################################
    # Thread this entire thing.  
    numThreads = len(machines_list["machines"])
    iterable = []
    machine_content = {}
    for i in range (0, numThreads):
        log.info("Appending iterable:  "+str(i))
        iterable.append(i)
    # Flask-Executor Method:
    log.info("Starting futures")
    futures = [executor.submit(thread_machine_content, machines_list["machines"][idx], machine_content, idx) for idx in iterable]
    # Wait for the executor to finish all jobs:
    wait(futures, return_when=ALL_COMPLETED)
    log.info("Finished futures")

    # DEBUG:  Do in a forloop:
    # for idx in iterable: thread_machine_content(machines_list["machines"][idx], machine_content, idx)

    # Sort the content by machine_id:
    sorted_machines = {key: val for key, val in sorted(machine_content.items(), key = lambda ele: ele[0])}

    content = "<div class='u-flex u-justify-space-evenly u-flex-wrap u-gap-1'>"
    # Print the content

    for index in range(0, numThreads):
        content = content+str(sorted_machines[index])
        # content = content+str(sorted_machines[index])

    content = content+"</div>"

    return Markup(content)

# Render the cards for the Users page:
def render_users_cards():
    url            = headscale.get_url()
    api_key        = headscale.get_api_key()
    user_list = headscale.get_users(url, api_key)

    # Set the current timezone and local time
    timezone   = pytz.timezone(os.environ["TZ"] if os.environ["TZ"] else "UTC")
    local_time = timezone.localize(datetime.now())

    content = "<div class='u-flex u-justify-space-evenly u-flex-wrap u-gap-1'>"
    for user in user_list["users"]:
        # Get all preAuth Keys in the user, only display if one exists:
        preauth_keys_collection = build_preauth_key_table(user["name"])

        # Set the user badge color:
        user_color = helper.get_color(int(user["id"]), "text")

        # Generate the various badges:
        status_badge      = "<i class='material-icons left "+user_color+"' id='"+user["id"]+"-status'>fiber_manual_record</i>"

        content = content + render_template(
            'users_card.html', 
            status_badge            = Markup(status_badge),
            user_name          = user["name"],
            user_id            = user["id"],
            preauth_keys_collection = Markup(preauth_keys_collection)
        ) 
    content = content+"</div>"
    return Markup(content)

# Builds the preauth key table for the User page
def build_preauth_key_table(user_name):
    url            = headscale.get_url()
    api_key        = headscale.get_api_key()

    preauth_keys = headscale.get_preauth_keys(url, api_key, user_name)
    preauth_keys_collection = """<li class="collection-item avatar">
            <span
                class='badge grey lighten-2 btn-small' 
                onclick='toggle_expired()'
            >Toggle Expired</span>
            <span 
                href="#card_modal" 
                class='badge grey lighten-2 btn-small modal-trigger' 
                onclick="load_modal_add_preauth_key('"""+user_name+"""')"
            >Add PreAuth Key</span>
            <i class="material-icons circle">vpn_key</i>
            <span class="title">PreAuth Keys</span>
            """
    if len(preauth_keys["preAuthKeys"]) == 0: preauth_keys_collection += "<p>No keys defined for this user</p>"
    if len(preauth_keys["preAuthKeys"]) > 0:
        preauth_keys_collection += """
                <table class="responsive-table striped" id='"""+user_name+"""-preauthkey-table'>
                    <thead>
                        <tr>
                            <td>ID</td>
                            <td>Key</td>
                            <td><center>Reusable</center></td>
                            <td><center>Used</center></td>
                            <td><center>Ephemeral</center></td>
                            <td><center>Usable</center></td>
                            <td><center>Actions</center></td>
                        </tr>
                    </thead>
                """
    for key in preauth_keys["preAuthKeys"]:
        # Get the key expiration date and compare it to now to check if it's expired:
        # Set the current timezone and local time
        timezone         = pytz.timezone(os.environ["TZ"] if os.environ["TZ"] else "UTC")
        local_time       = timezone.localize(datetime.now())
        expiration_parse = parser.parse(key["expiration"])
        key_expired = True if expiration_parse < local_time else False
        expiration_time  = str(expiration_parse.strftime('%A %m/%d/%Y, %H:%M:%S'))+" "+str(timezone)

        # Class for the javascript function to look for to toggle the hide function
        hide_expired = "expired-row" if key_expired else ""

        key_usable = False
        if key["reusable"] and not key_expired: key_usable = True
        if not key["reusable"] and not key["used"] and not key_expired: key_usable = True

        tooltip_expired   = "Expiration:  "+expiration_time

        btn_reusable      = "<i class='pulse material-icons tiny blue-text text-darken-1'>fiber_manual_record</i>"   if key["reusable"]  else ""
        btn_ephemeral     = "<i class='pulse material-icons tiny red-text text-darken-1'>fiber_manual_record</i>"    if key["ephemeral"] else ""
        btn_used          = "<i class='pulse material-icons tiny yellow-text text-darken-1'>fiber_manual_record</i>" if key["used"]      else ""
        btn_usable        = "<i class='pulse material-icons tiny green-text text-darken-1'>fiber_manual_record</i>"  if key_usable       else ""

        # Other buttons:
        btn_delete        = "<span href='#card_modal' data-tooltip='Expire this PreAuth Key' class='btn-small modal-trigger badge tooltipped white-text red' onclick='load_modal_expire_preauth_key(\""+user_name+"\", \""+str(key["key"])+"\")'>Expire</span>" if key_usable else ""
        tooltip_data      = "Expiration:  "+expiration_time

        # TR ID will look like "1-albert-tr"
        preauth_keys_collection = preauth_keys_collection+"""
            <tr id='"""+key["id"]+"""-"""+user_name+"""-tr' class='"""+hide_expired+"""'>
                <td>"""+str(key["id"])+"""</td>
                <td class='tooltipped' data-tooltip='"""+tooltip_data+"""'>"""+str(key["key"])+"""</td>
                <td><center>"""+btn_reusable+"""</center></td>
                <td><center>"""+btn_used+"""</center></td>
                <td><center>"""+btn_ephemeral+"""</center></td>
                <td><center>"""+btn_usable+"""</center></td>
                <td><center>"""+btn_delete+"""</center></td>
            </tr>
        """

    preauth_keys_collection = preauth_keys_collection+"""</table>
        </li>
        """
    return preauth_keys_collection