"""Page rendering functions.

TODO: Move some parts to Jinja templates.
"""


import asyncio
import datetime

from flask import current_app, render_template
from flask_oidc import OpenIDConnect  # type: ignore
from headscale_api.schema.headscale import v1 as schema
from markupsafe import Markup

import helper
from config import Config
from headscale import HeadscaleApi


async def render_overview(headscale: HeadscaleApi):
    """Render the overview page."""
    current_app.logger.info("Rendering the Overview page")

    local_time = datetime.datetime.now(headscale.app_config.timezone)

    # Get and display overview of the following information:
    #   server's machines, users, preauth keys, API key expiration, server version

    async with headscale.session:
        machines, routes, users = await asyncio.gather(
            headscale.list_machines(schema.ListMachinesRequest("")),
            headscale.get_routes(schema.GetRoutesRequest()),
            headscale.list_users(schema.ListUsersRequest()),
        )
        user_preauth_keys: list[schema.ListPreAuthKeysResponse] = await asyncio.gather(
            *[
                headscale.list_pre_auth_keys(schema.ListPreAuthKeysRequest(user.name))
                for user in users.users
            ]
        )

    # Need to check if routes are attached to an active machine:
    # ISSUE:  https://github.com/iFargle/headscale-webui/issues/36
    # ISSUE:  https://github.com/juanfont/headscale/issues/1228

    # Get all routes:
    total_routes = sum(route.machine.id != 0 for route in routes.routes)
    enabled_routes = sum(
        route.enabled and route.advertised and route.machine.id != 0
        for route in routes.routes
    )

    # Get a count of all enabled exit routes
    exits_count = 0
    exits_enabled_count = 0
    for route in routes.routes:
        if route.advertised and route.machine.id != 0:
            if route.prefix in ("0.0.0.0/0", "::/0"):
                exits_count += 1
                if route.enabled:
                    exits_enabled_count += 1

    # Get User and PreAuth Key counts
    usable_keys_count = sum(
        sum(
            (key.reusable or (not key.reusable and not key.used))
            and not key.expiration < local_time
            for key in preauth_keys.pre_auth_keys
        )
        for preauth_keys in user_preauth_keys
    )

    # Start putting the content together
    overview_content = f"""
        <div class="row">
            <div class="col s1"></div>
            <div class="col s10">
                <ul class="collection with-header z-depth-1">
                    <li class="collection-header"><h4>Server Statistics</h4></li>
                    <li class="collection-item"><div>Machines Added
                        <div class="secondary-content overview-page">
                            {len(machines.machines)}</div></div></li>
                    <li class="collection-item"><div>Users Added
                        <div class="secondary-content overview-page">
                            {len(users.users)}</div></div></li>
                    <li class="collection-item"><div>Usable Preauth Keys
                        <div class="secondary-content overview-page">
                            {usable_keys_count}</div></div></li>
                    <li class="collection-item"><div>Enabled/Total Routes
                        <div class="secondary-content overview-page">
                            {enabled_routes}/{total_routes}</div></div></li>
                    <li class="collection-item"><div>Enabled/Total Exits
                        <div class="secondary-content overview-page">
                            {exits_enabled_count}/{exits_count}</div></div></li>
                </ul>
            </div>
            <div class="col s1"></div>
        </div>
        """

    # Overview page will just read static information from the config file and display
    # it Open the config.yaml and parse it.
    config_yaml = headscale.hs_config

    if config_yaml is None:
        return Markup(
            f"""<br>{overview_content}
                <div class='row'>
                    <div class="col s1"></div>
                    <div class="col s10">
                        <ul class="collection with-header z-depth-1">
                            <li class="collection-header"><h4>General</h4></li>
                            <li class="collection-item">
                            Headscale configuration is invalid or unavailable.
                            Please check logs.</li>
                        </ul>
                    </div>
                    <div class="col s1"></div>
                </div>
            """
        )

    general_content = f"""
        <div class="row">
            <div class="col s1"></div>
            <div class="col s10">
                <ul class="collection with-header z-depth-1">
                    <li class="collection-header"><h4>General</h4></li>
                    <li class="collection-item"><div>IP Prefixes
                        <div class="secondary-content overview-page">
                            {config_yaml.ip_prefixes or 'N/A'}</div></div></li>
                    <li class="collection-item"><div>Server URL
                        <div class="secondary-content overview-page">
                            {config_yaml.server_url}</div></div></li>
                    <li class="collection-item"><div>Updates Disabled
                        <div class="secondary-content overview-page">
                            {config_yaml.disable_check_updates or 'N/A'}
                        </div></div></li>
                    <li class="collection-item"><div>Ephemeral Node Inactivity Timeout
                        <div class="secondary-content overview-page">
                            {config_yaml.ephemeral_node_inactivity_timeout or 'N/A'}
                        </div></div></li>
                    <li class="collection-item"><div>Node Update Check Interval
                        <div class="secondary-content overview-page">
                            {config_yaml.node_update_check_interval or 'N/A'}
                        </div></div></li>
                </ul>
            </div>
            <div class="col s1"></div>
        </div>
        """

    # OIDC Content:
    oidc = config_yaml.oidc
    oidc_content = (
        (
            f"""
            <div class="row">
                <div class="col s1"></div>
                <div class="col s10">
                    <ul class="collection with-header z-depth-1">
                        <li class="collection-header"><h4>Headscale OIDC</h4></li>
                        <li class="collection-item"><div>Issuer
                            <div class="secondary-content overview-page">
                                {oidc.issuer or 'N/A'}</div></div></li>
                        <li class="collection-item"><div>Client ID
                            <div class="secondary-content overview-page">
                                {oidc.client_id or 'N/A'}</div></div></li>
                        <li class="collection-item"><div>Scope
                            <div class="secondary-content overview-page">
                                {oidc.scope or 'N/A'}</div></div></li>
                        <li class="collection-item"><div>Use OIDC Token Expiry
                            <div class="secondary-content overview-page">
                                {oidc.use_expiry_from_token or 'N/A'}</div></div></li>
                        <li class="collection-item"><div>Expiry
                            <div class="secondary-content overview-page">
                                {oidc.expiry or 'N/A'}</div></div></li>
                    </ul>
                </div>
                <div class="col s1"></div>
            </div>
            """
        )
        if oidc is not None
        else ""
    )

    # Embedded DERP server information.
    derp = config_yaml.derp
    derp_content = (
        (
            f"""
            <div class="row">
                <div class="col s1"></div>
                <div class="col s10">
                    <ul class="collection with-header z-depth-1">
                        <li class="collection-header"><h4>Embedded DERP</h4></li>
                        <li class="collection-item"><div>Enabled
                            <div class="secondary-content overview-page">
                            {derp.server.enabled}</div></div></li>
                        <li class="collection-item"><div>Region ID
                            <div class="secondary-content overview-page">
                            {derp.server.region_id or 'N/A'}</div></div></li>
                        <li class="collection-item"><div>Region Code
                            <div class="secondary-content overview-page">
                            {derp.server.region_code or 'N/A'}</div></div></li>
                        <li class="collection-item"><div>Region Name
                            <div class="secondary-content overview-page">
                            {derp.server.region_name or 'N/A'}</div></div></li>
                        <li class="collection-item"><div>STUN Address
                            <div class="secondary-content overview-page">
                            {derp.server.stun_listen_addr or 'N/A'}</div></div></li>
                    </ul>
                </div>
                <div class="col s1"></div>
            </div>
            """
        )
        if derp is not None and derp.server is not None and derp.server.enabled
        else ""
    )

    dns_config = config_yaml.dns_config
    dns_content = (
        (
            f"""
            <div class="row">
                <div class="col s1"></div>
                <div class="col s10">
                    <ul class="collection with-header z-depth-1">
                        <li class="collection-header"><h4>DNS</h4></li>
                        <li class="collection-item"><div>DNS Nameservers
                            <div class="secondary-content overview-page">
                            {dns_config.nameservers or 'N/A'}</div></div></li>
                        <li class="collection-item"><div>MagicDNS
                            <div class="secondary-content overview-page">
                            {dns_config.magic_dns or 'N/A'}</div></div></li>
                        <li class="collection-item"><div>Search Domains
                            <div class="secondary-content overview-page">
                            {dns_config.domains or 'N/A'}</div></div></li>
                        <li class="collection-item"><div>Base Domain
                            <div class="secondary-content overview-page">
                            {dns_config.base_domain or 'N/A'}</div></div></li>
                    </ul>
                </div>
                <div class="col s1"></div>
            </div>
            """
        )
        if dns_config is not None
        else ""
    )

    # TODO:
    #     Whether there are custom DERP servers
    #         If there are custom DERP servers, get the file location from the config
    #         file.  Assume mapping is the same.
    #     Whether the built-in DERP server is enabled
    #     The IP prefixes
    #     The DNS config

    # if derp is not None and derp.paths is not None:
    #     pass
    #   # open the path:
    #   derp_file =
    #   config_file = open("/etc/headscale/config.yaml", "r")
    #   config_yaml = yaml.safe_load(config_file)
    #     The ACME config, if not empty
    #     Whether updates are running
    #     Whether metrics are enabled (and their listen addr)
    #     The log level
    #     What kind of Database is being used to drive headscale

    return Markup(
        "<br>"
        + overview_content
        + general_content
        + derp_content
        + oidc_content
        + dns_content
    )


async def thread_machine_content(
    headscale: HeadscaleApi,
    machine: schema.Machine,
    idx: int,
    all_routes: schema.GetRoutesResponse,
) -> str:
    """Render a single machine."""
    # machine      = passed in machine information
    # content      = place to write the content

    failover_pair_prefixes: list[str] = []
    current_app.logger.debug("Machine Information =================")
    current_app.logger.debug(
        "Name: %s, ID: %i, User: %s, givenName: %s",
        machine.name,
        machine.id,
        machine.user.name,
        machine.given_name,
    )

    # Set the current timezone and local time
    timezone = headscale.app_config.timezone
    local_time = datetime.datetime.now(timezone)

    # Get the machines routes
    pulled_routes = await headscale.get_machine_routes(
        schema.GetMachineRoutesRequest(machine.id)
    )
    routes = ""

    # Test if the machine is an exit node:
    exit_route_found = False
    exit_route_enabled = False
    # If the device has enabled Failover routes (High Availability routes)
    ha_enabled = False

    # If the length of "routes" is NULL/0, there are no routes, enabled or disabled:
    if len(pulled_routes.routes) > 0:
        # First, check if there are any routes that are both enabled and advertised If
        # that is true, we will output the collection-item for routes.  Otherwise, it
        # will not be displayed.
        advertised_routes = any(route.advertised for route in pulled_routes.routes)

        if advertised_routes:
            routes = """
                <li class="collection-item avatar">
                    <i class="material-icons circle">directions</i>
                    <span class="title">Routes</span>
                    <p>
                """
            # current_app.logger.debug("Pulled Routes Dump:  "+str(pulled_routes))
            # current_app.logger.debug("All    Routes Dump:  "+str(all_routes))

            # Find all exits and put their ID's into the exit_routes array
            exit_routes: list[int] = []
            exit_enabled_color = "red"
            exit_tooltip = "enable"
            exit_route_enabled = False

            for route in pulled_routes.routes:
                if route.prefix in ("0.0.0.0/0", "::/0"):
                    exit_routes.append(route.id)
                    exit_route_found = True
                    # Test if it is enabled:
                    if route.enabled:
                        exit_enabled_color = "green"
                        exit_tooltip = "disable"
                        exit_route_enabled = True
                    current_app.logger.debug("Found exit route ID's: %s", exit_routes)
                    current_app.logger.debug(
                        "Exit Route Information: ID: %i | Enabled: %r | "
                        "exit_route_enabled: %r / Found: %r",
                        route.id,
                        route.enabled,
                        exit_route_enabled,
                        exit_route_found,
                    )

            # Print the button for the Exit routes:
            if exit_route_found:
                routes += (
                    f"<p class='waves-effect waves-light btn-small "
                    f"{exit_enabled_color} lighten-2 tooltipped' data-position='top' "
                    f"data-tooltip='Click to {exit_tooltip}' id='{machine.id}-exit' "
                    f'onclick="toggle_exit({exit_routes[0]}, {exit_routes[1]}, '
                    f"{machine.id}-exit', '{exit_route_enabled}', 'machines')\">"
                    "Exit Route</p>"
                )

            # Check if the route has another enabled identical route.
            # Check all routes from the current machine...
            for route in pulled_routes.routes:
                # ... against all routes from all machines ....
                for route_info in all_routes.routes:
                    current_app.logger.debug(
                        "Comparing routes %s and %s", route.prefix, route_info.prefix
                    )
                    # ... If the route prefixes match and are not exit nodes ...
                    if route_info.prefix == route.prefix and (
                        route.prefix not in ("0.0.0.0/0", "::/0")
                    ):
                        # Check if the route ID's match.  If they don't ...
                        current_app.logger.debug(
                            "Found a match: %s and %s", route.prefix, route_info.prefix
                        )
                        if route_info.id != route.id:
                            current_app.logger.debug(
                                "Route ID's don't match. They're on different nodes."
                            )
                            # ... Check if the routes prefix is already in the array...
                            if route.prefix not in failover_pair_prefixes:
                                #  IF it isn't, add it.
                                current_app.logger.info(
                                    "New HA pair found: %s", route.prefix
                                )
                                failover_pair_prefixes.append(route.prefix)
                            if route.enabled and route_info.enabled:
                                # If it is already in the array. . .
                                # Show as HA only if both routes are enabled:
                                current_app.logger.debug(
                                    "Both routes are enabled. Setting as HA [%s] (%s) ",
                                    machine.name,
                                    route.prefix,
                                )
                                ha_enabled = True
                # If the route is an exit node and already counted as a failover route,
                # it IS a failover route, so display it.
                if (
                    route.prefix not in ("0.0.0.0/0", "::/0")
                    and route.prefix in failover_pair_prefixes
                ):
                    route_enabled = "red"
                    route_tooltip = "enable"
                    color_index = failover_pair_prefixes.index(route.prefix)
                    route_enabled_color = helper.get_color(color_index, "failover")
                    if route.enabled:
                        color_index = failover_pair_prefixes.index(route.prefix)
                        route_enabled = helper.get_color(color_index, "failover")
                        route_tooltip = "disable"
                    routes += (
                        f"<p class='waves-effect waves-light btn-small {route_enabled} "
                        "lighten-2  tooltipped' data-position='top' "
                        f"data-tooltip='Click to {route_tooltip} (Failover Pair)' "
                        f"id='{route.id}' onclick=\"toggle_failover_route({route.id}, "
                        f"'{route.enabled}', '{route_enabled_color}')\">"
                        f"{route.prefix}</p>"
                    )

            # Get the remaining routes:
            for route in pulled_routes.routes:
                # Get the remaining routes - No exits or failover pairs
                if (
                    route.prefix not in ("0.0.0.0/0", "::/0")
                    and route.prefix not in failover_pair_prefixes
                ):
                    current_app.logger.debug(
                        "Route:  [%s] id: %i / prefix: %s enabled?:  %r",
                        route.machine.name,
                        route.id,
                        route.prefix,
                        route.enabled,
                    )
                    route_enabled = "red"
                    route_tooltip = "enable"
                    if route.enabled:
                        route_enabled = "green"
                        route_tooltip = "disable"
                    routes += (
                        f"<p class='waves-effect waves-light btn-small {route_enabled} "
                        "lighten-2 tooltipped' data-position='top' data-tooltip='Click "
                        f"to {route_tooltip}' id='{route.id}' "
                        f"onclick=\"toggle_route({route.id}, '{route.enabled}', "
                        f"'machines')\">{route.prefix}</p>"
                    )
            routes += "</p></li>"

    # Get machine tags
    tag_array = ", ".join(f"{{tag: '{tag[4:]}'}}" for tag in machine.forced_tags)
    tags = f"""
        <li class="collection-item avatar">
            <i class="material-icons circle tooltipped" data-position="right"
                data-tooltip="Spaces will be replaced with a dash (-)
                upon page refresh">label</i>
            <span class="title">Tags</span>
            <p><div style='margin: 0px' class='chips' id='{machine.id}-tags'></div></p>
        </li>
        <script>
            window.addEventListener('load', function() {{
                var instances = M.Chips.init (
                    document.getElementById('{machine.id}-tags'),  ({{
                        data:[{tag_array}],
                        onChipDelete() {{ delete_chip({machine.id}, this.chipsData) }},
                        onChipAdd()    {{ add_chip({machine.id},    this.chipsData) }}
                    }})
                );
            }}, false
            )
        </script>
        """

    # Get the machine IP's
    machine_ips = (
        "<ul>"
        + "".join(f"<li>{ip_address}</li>" for ip_address in machine.ip_addresses)
        + "</ul>"
    )

    # Format the dates for easy readability
    last_seen_local = machine.last_seen.astimezone(timezone)
    last_seen_delta = local_time - last_seen_local
    last_seen_print = helper.pretty_print_duration(last_seen_delta)
    last_seen_time = (
        str(last_seen_local.strftime("%A %m/%d/%Y, %H:%M:%S"))
        + f" {timezone} ({last_seen_print})"
    )

    if machine.last_successful_update is not None:
        last_update_local = machine.last_successful_update.astimezone(timezone)
        last_update_delta = local_time - last_update_local
        last_update_print = helper.pretty_print_duration(last_update_delta)
        last_update_time = (
            str(last_update_local.strftime("%A %m/%d/%Y, %H:%M:%S"))
            + f" {timezone} ({last_update_print})"
        )
    else:
        last_update_print = None
        last_update_time = None

    created_local = machine.created_at.astimezone(timezone)
    created_delta = local_time - created_local
    created_print = helper.pretty_print_duration(created_delta)
    created_time = (
        str(created_local.strftime("%A %m/%d/%Y, %H:%M:%S"))
        + f" {timezone} ({created_print})"
    )

    # If there is no expiration date, we don't need to do any calculations:
    if machine.expiry != datetime.datetime(1, 1, 1, 0, 0, tzinfo=datetime.timezone.utc):
        expiry_local = machine.expiry.astimezone(timezone)
        expiry_delta = expiry_local - local_time
        expiry_print = helper.pretty_print_duration(expiry_delta, "expiry")
        if str(expiry_local.strftime("%Y")) in ("0001", "9999", "0000"):
            expiry_time = "No expiration date."
        elif int(expiry_local.strftime("%Y")) > int(expiry_local.strftime("%Y")) + 2:
            expiry_time = (
                str(expiry_local.strftime("%m/%Y")) + f" {timezone} ({expiry_print})"
            )
        else:
            expiry_time = (
                str(expiry_local.strftime("%A %m/%d/%Y, %H:%M:%S"))
                + f" {timezone} ({expiry_print})"
            )

        expiring_soon = int(expiry_delta.days) < 14 and int(expiry_delta.days) > 0
        current_app.logger.debug(
            "Machine: %s expires: %s / %i",
            machine.name,
            expiry_local.strftime("%Y"),
            expiry_delta.days,
        )
    else:
        expiry_time = "No expiration date."
        expiring_soon = False
        current_app.logger.debug("Machine: %s has no expiration date", machine.name)

    # Get the first 10 characters of the PreAuth Key:
    if machine.pre_auth_key is not None:
        preauth_key = machine.pre_auth_key.key[0:10]
    else:
        preauth_key = "None"

    # Set the status and user badge color:
    text_color = helper.text_color_duration(last_seen_delta)
    user_color = helper.get_color(int(machine.user.id))

    # Generate the various badges:
    status_badge = (
        f"<i class='material-icons left tooltipped {text_color}' data-position='top' "
        f"data-tooltip='Last Seen: {last_seen_print}' id='{machine.id}-status'>"
        "fiber_manual_record</i>"
    )
    user_badge = (
        f"<span class='badge ipinfo {user_color} white-text hide-on-small-only' "
        f"id='{machine.id}-ns-badge'>{machine.user.name}</span>"
    )
    exit_node_badge = (
        ""
        if not exit_route_enabled
        else (
            "<span class='badge grey white-text text-lighten-4 tooltipped' "
            "data-position='left' data-tooltip='This machine has an enabled exit "
            "route.'>Exit</span>"
        )
    )
    ha_route_badge = (
        ""
        if not ha_enabled
        else (
            "<span class='badge blue-grey white-text text-lighten-4 tooltipped' "
            "data-position='left' data-tooltip='This machine has an enabled High "
            "Availability (Failover) route.'>HA</span>"
        )
    )
    expiration_badge = (
        ""
        if not expiring_soon
        else (
            "<span class='badge red white-text text-lighten-4 tooltipped' "
            "data-position='left' data-tooltip='This machine expires soon.'>"
            "Expiring!</span>"
        )
    )

    current_app.logger.info(
        "Finished thread for machine %s index %i", machine.given_name, idx
    )
    return render_template(
        "machines_card.html",
        given_name=machine.given_name,
        machine_id=machine.id,
        hostname=machine.name,
        ns_name=machine.user.name,
        ns_id=machine.user.id,
        ns_created=machine.user.created_at,
        last_seen=str(last_seen_print),
        last_update=str(last_update_print),
        machine_ips=Markup(machine_ips),
        advertised_routes=Markup(routes),
        exit_node_badge=Markup(exit_node_badge),
        ha_route_badge=Markup(ha_route_badge),
        status_badge=Markup(status_badge),
        user_badge=Markup(user_badge),
        last_update_time=str(last_update_time),
        last_seen_time=str(last_seen_time),
        created_time=str(created_time),
        expiry_time=str(expiry_time),
        preauth_key=str(preauth_key),
        expiration_badge=Markup(expiration_badge),
        machine_tags=Markup(tags),
        taglist=machine.forced_tags,
    )


async def render_machines_cards(headscale: HeadscaleApi):
    """Render machine cards."""
    current_app.logger.info("Rendering machine cards")

    async with headscale.session:
        # Execute concurrent machine info requests and sort them by machine_id.
        routes = await headscale.get_routes(schema.GetRoutesRequest())
        content = await asyncio.gather(
            *[
                thread_machine_content(headscale, machine, idx, routes)
                for idx, machine in enumerate(
                    (
                        await headscale.list_machines(schema.ListMachinesRequest(""))
                    ).machines
                )
            ]
        )
    return Markup("<ul class='collapsible expandable'>" + "".join(content) + "</ul>")


async def render_users_cards(headscale: HeadscaleApi):
    """Render users cards."""
    current_app.logger.info("Rendering Users cards")

    async with headscale.session:
        content = await asyncio.gather(
            *[
                build_user_card(headscale, user)
                for user in (
                    await headscale.list_users(schema.ListUsersRequest())
                ).users
            ]
        )

    return Markup("<ul class='collapsible expandable'>" + "".join(content) + "</ul>")


async def build_user_card(headscale: HeadscaleApi, user: schema.User):
    """Build a user card."""
    # Get all preAuth Keys in the user, only display if one exists:
    preauth_keys_collection = await build_preauth_key_table(
        headscale, schema.ListPreAuthKeysRequest(user.name)
    )

    # Set the user badge color:
    user_color = helper.get_color(int(user.id), "text")

    # Generate the various badges:
    status_badge = (
        f"<i class='material-icons left {user_color}' id='{user.id}-status'>"
        "fiber_manual_record</i>"
    )

    return render_template(
        "users_card.html",
        status_badge=Markup(status_badge),
        user_name=user.name,
        user_id=user.id,
        preauth_keys_collection=Markup(preauth_keys_collection),
    )


async def build_preauth_key_table(
    headscale: HeadscaleApi, request: schema.ListPreAuthKeysRequest
):
    """Build PreAuth key table for a user."""
    current_app.logger.info(
        "Building the PreAuth key table for User:  %s", request.user
    )

    preauth_keys = await headscale.list_pre_auth_keys(request)
    preauth_keys_collection = f"""
        <li class="collection-item avatar">
            <span
                class='badge grey lighten-2 btn-small'
                onclick='toggle_expired()'
            >Toggle Expired</span>
            <span
                href="#card_modal"
                class='badge grey lighten-2 btn-small modal-trigger'
                onclick="load_modal_add_preauth_key('{request.user}')"
            >Add PreAuth Key</span>
            <i class="material-icons circle">vpn_key</i>
            <span class="title">PreAuth Keys</span>
        """
    if len(preauth_keys.pre_auth_keys) == 0:
        preauth_keys_collection += "<p>No keys defined for this user</p>"
    else:
        preauth_keys_collection += f"""
            <table class="responsive-table striped"
            id='{request.user}-preauthkey-table'>
                <thead><tr>
                    <td>ID</td>
                    <td class='tooltipped' data-tooltip='Click an Auth Key Prefix to
                        copy it to the clipboard'>Key Prefix</td>
                    <td><center>Reusable</center></td>
                    <td><center>Used</center></td>
                    <td><center>Ephemeral</center></td>
                    <td><center>Usable</center></td>
                    <td><center>Actions</center></td>
                </tr></thead>
            """
    for key in preauth_keys.pre_auth_keys:
        # Get the key expiration date and compare it to now to check if it's expired:
        # Set the current timezone and local time
        timezone = headscale.app_config.timezone
        local_time = datetime.datetime.now(timezone)
        key_expired = key.expiration < local_time
        expiration_time = (
            key.expiration.strftime("%A %m/%d/%Y, %H:%M:%S") + f" {timezone}"
        )

        key_usable = (key.reusable and not key_expired) or (
            not key.reusable and not key.used and not key_expired
        )

        # Class for the javascript function to look for to toggle the hide function
        hide_expired = "expired-row" if not key_usable else ""

        btn_reusable = (
            "<i class='pulse material-icons tiny blue-text text-darken-1'>"
            "::"
            "fiber_manual_record</i>"
            if key.reusable
            else ""
        )
        btn_ephemeral = (
            "<i class='pulse material-icons tiny red-text text-darken-1'>"
            "fiber_manual_record</i>"
            if key.ephemeral
            else ""
        )
        btn_used = (
            "<i class='pulse material-icons tiny yellow-text text-darken-1'>"
            "fiber_manual_record</i>"
            if key.used
            else ""
        )
        btn_usable = (
            "<i class='pulse material-icons tiny green-text text-darken-1'>"
            "fiber_manual_record</i>"
            if key_usable
            else ""
        )

        # Other buttons:
        btn_delete = (
            "<span href='#card_modal' data-tooltip='Expire this PreAuth Key' "
            "class='btn-small modal-trigger badge tooltipped white-text red' onclick='"
            f'load_modal_expire_preauth_key("{request.user}", "{key.key}")\'>'
            "Expire</span>"
            if key_usable
            else ""
        )
        tooltip_data = f"Expiration: {expiration_time}"

        # TR ID will look like "1-albert-tr"
        preauth_keys_collection += f"""
            <tr id='{key.id}-{request.user}-tr' class='{hide_expired}'>
                <td>{key.id}</td>
                <td onclick=copy_preauth_key('{key.key}') class='tooltipped'
                    data-tooltip='{tooltip_data}'>{key.key[0:10]}</td>
                <td><center>{btn_reusable}</center></td>
                <td><center>{btn_used}</center></td>
                <td><center>{btn_ephemeral}</center></td>
                <td><center>{btn_usable}</center></td>
                <td><center>{btn_delete}</center></td>
            </tr>
            """

    return preauth_keys_collection + "</table></li>"


def oidc_nav_dropdown(user_name: str, email_address: str, name: str) -> Markup:
    """Render desktop navigation for OIDC."""
    current_app.logger.debug("OIDC is enabled. Building the OIDC nav dropdown")
    html_payload = f"""
        <!-- OIDC Dropdown Structure -->
        <ul id="dropdown1" class="dropdown-content dropdown-oidc">
            <ul class="collection dropdown-oidc-collection">
                <li class="collection-item dropdown-oidc-avatar avatar">
                    <i class="material-icons circle">email</i>
                    <span class="dropdown-oidc-title title">Email</span>
                    <p>{email_address}</p>
                </li>
                <li class="collection-item dropdown-oidc-avatar avatar">
                    <i class="material-icons circle">person_outline</i>
                    <span class="dropdown-oidc-title title">Username</span>
                    <p>{user_name}</p>
                </li>
            </ul>
        <li class="divider"></li>
            <li><a href="logout">
                <i class="material-icons left">exit_to_app</i> Logout</a></li>
        </ul>
        <li>
            <a class="dropdown-trigger" href="#!" data-target="dropdown1">
                {name} <i class="material-icons right">account_circle</i>
            </a>
        </li>
        """
    return Markup(html_payload)


def oidc_nav_mobile():
    """Render mobile navigation for OIDC."""
    return Markup(
        '<li><hr><a href="logout"><i class="material-icons left">'
        "exit_to_app</i>Logout</a></li>"
    )


def render_defaults(
    config: Config, oidc_handler: OpenIDConnect | None
) -> dict[str, Markup | str]:
    """Render the default elements.

    TODO: Think about caching the results.
    """
    colors = {
        "color_nav": config.color_nav,
        "color_btn": config.color_btn,
    }

    if oidc_handler is None:
        return colors

    # If OIDC is enabled, display the buttons:
    email_address: str = oidc_handler.user_getfield("email")  # type: ignore
    assert isinstance(email_address, str)
    user_name: str = oidc_handler.user_getfield("preferred_username")  # type: ignore
    assert isinstance(user_name, str)
    name: str = oidc_handler.user_getfield("name")  # type: ignore
    assert isinstance(name, str)

    return {
        "oidc_nav_dropdown": oidc_nav_dropdown(user_name, email_address, name),
        "oidc_nav_mobile": oidc_nav_mobile(),
        **colors,
    }


def render_search():
    """Render search bar."""
    return Markup(
        """
        <li role="menu-item" class="tooltipped" data-position="bottom"
            data-tooltip="Search" onclick="show_search()">
                <a href="#"><i class="material-icons">search</i></a>
        </li>
        """
    )


async def render_routes(headscale: HeadscaleApi):
    """Render routes page."""
    current_app.logger.info("Rendering Routes page")
    all_routes = await headscale.get_routes(schema.GetRoutesRequest())

    # If there are no routes, just exit:
    if len(all_routes.routes) == 0:
        return Markup("<br><br><br><center>There are no routes to display!</center>")
    # Get a list of all Route ID's to iterate through:
    all_routes_id_list: list[int] = []
    for route in all_routes.routes:
        all_routes_id_list.append(route.id)
        if route.machine.name:
            current_app.logger.info(
                "Found route %i / machine: %s", route.id, route.machine.name
            )
        else:
            current_app.logger.info("Route id %i has no machine associated.", route.id)

    route_content = ""
    failover_content = ""
    exit_content = ""

    route_title = '<span class="card-title">Routes</span>'
    failover_title = '<span class="card-title">Failover Routes</span>'
    exit_title = '<span class="card-title">Exit Routes</span>'

    markup_pre = """
    <div class="row">
        <div class="col m1"></div>
        <div class="col s12 m10">
            <div class="card">
                <div class="card-content">
    """
    markup_post = """
                </div>
            </div>
        </div>
        <div class="col m1"></div>
    </div>
    """

    ##############################################################################################
    # Step 1:  Get all non-exit and non-failover routes:
    route_content = (
        markup_pre
        + route_title
        + """
            <p><table>
            <thead>
                <tr>
                    <th>ID       </th>
                    <th>Machine  </th>
                    <th>Route    </th>
                    <th width="60px">Enabled</th>
                </tr>
            </thead>
            <tbody>
        """
    )
    for route in all_routes.routes:
        # Get relevant info:
        machine = route.machine.given_name
        prefix = route.prefix
        is_enabled = route.enabled
        is_primary = route.is_primary
        is_failover = False
        is_exit = False

        enabled = (
            f"<i id='{route.id}' onclick='toggle_route({route.id}, \"True\", "
            "\"routes\")' class='material-icons green-text text-lighten-2 tooltipped' "
            "data-tooltip='Click to disable'>fiber_manual_record</i>"
        )
        disabled = (
            f"<i id='{route.id}' onclick='toggle_route({route.id}, \"False\", "
            "\"routes\")' class='material-icons red-text text-lighten-2 tooltipped' "
            "data-tooltip='Click to enable' >fiber_manual_record</i>"
        )

        # Set the displays:
        enabled_display = disabled

        if is_enabled:
            enabled_display = enabled
        # Check if a prefix is an Exit route:
        if prefix in ("0.0.0.0/0", "::/0"):
            is_exit = True
        # Check if a prefix is part of a failover pair:
        for route_check in all_routes.routes:
            if (
                not is_exit
                and route.prefix == route_check.prefix
                and route.id != route_check.id
            ):
                is_failover = True

        if not is_exit and not is_failover and machine != "":
            # Build a simple table for all non-exit routes:
            route_content += f"""<tr>
                <td>{route.id}</td>
                <td>{machine}</td>
                <td>{prefix}</td>
                <td><center>{enabled_display}</center></td>
            </tr>"""
    route_content += "</tbody></table></p>" + markup_post

    ##############################################################################################
    # Step 2:  Get all failover routes only.  Add a separate table per failover prefix

    # Get a set of all prefixes for all routes:
    # - that  aren't exit routes
    # - the current route matches any prefix of any other route
    # - the route ID's are different
    failover_route_prefix = set(
        route.prefix
        for route_check in all_routes.routes
        for route in all_routes.routes
        if (
            route.prefix not in ("0.0.0.0/0", "::/0")
            and route.prefix == route.prefix
            and route.id != route_check.id
        )
    )

    if len(failover_route_prefix) > 0:
        # Set up the display code:
        enabled = (
            "<i class='material-icons green-text text-lighten-2'>"
            "fiber_manual_record</i>"
        )
        disabled = (
            "<i class='material-icons red-text text-lighten-2'>fiber_manual_record</i>"
        )

        failover_content = markup_pre + failover_title
        # Build the display for failover routes:
        for route_prefix in failover_route_prefix:
            # Get all route ID's associated with the route_prefix:
            route_id_list = [
                route.id for route in all_routes.routes if route.prefix == route_prefix
            ]

            # Set up the display code:
            failover_enabled = (
                f"<i id='{route_prefix}' class='material-icons small left green-text "
                "text-lighten-2'>fiber_manual_record</i>"
            )
            failover_disabled = (
                f"<i id='{route_prefix}' class='material-icons small left red-text "
                "text-lighten-2'>fiber_manual_record</i>"
            )

            failover_display = failover_disabled
            for route_id in route_id_list:
                # Get the routes index:
                current_route_index = all_routes_id_list.index(route_id)
                if all_routes.routes[current_route_index].enabled:
                    failover_display = failover_enabled

            # Get all route_id's associated with the route prefix:
            failover_content += f"""<p>
                <h5>{failover_display}</h5><h5>{route_prefix}</h5>
                <table>
                    <thead>
                        <tr>
                            <th>Machine</th>
                            <th width="60px">Enabled</th>
                            <th width="60px">Primary</th>
                        </tr>
                    </thead>
                    <tbody>
                """

            # Build the display:
            for route_id in route_id_list:
                idx = all_routes_id_list.index(route_id)

                machine = all_routes.routes[idx].machine.given_name
                machine_id = all_routes.routes[idx].machine.id
                is_primary = all_routes.routes[idx].is_primary
                is_enabled = all_routes.routes[idx].enabled

                payload = route_id_list.copy()

                current_app.logger.debug(
                    "[%i] Machine:  [%i]  %s : %r / %r",
                    route_id,
                    machine_id,
                    machine,
                    is_enabled,
                    is_primary,
                )
                current_app.logger.debug(str(all_routes.routes[idx]))

                # Set up the display code:
                enabled_display_enabled = (
                    f"<i id='{route_id}' onclick='toggle_failover_route_routespage("
                    f'{route_id}, "True", "{route_prefix}", {payload})\'  '
                    "class='material-icons green-text text-lighten-2 tooltipped' "
                    "data-tooltip='Click to disable'>fiber_manual_record</i>"
                )
                enabled_display_disabled = (
                    f"<i id='{route_id}' onclick='toggle_failover_route_routespage("
                    f'{route_id}, "False", "{route_prefix}", {payload})\' '
                    "class='material-icons red-text text-lighten-2 tooltipped' "
                    "data-tooltip='Click to enable'>fiber_manual_record</i>"
                )
                primary_display_enabled = (
                    f"<i id='{route_id}-primary' class='material-icons "
                    "green-text text-lighten-2'>fiber_manual_record</i>"
                )
                primary_display_disabled = (
                    f"<i id='{route_id}-primary' class='material-icons "
                    "red-text text-lighten-2'>fiber_manual_record</i>"
                )

                # Set displays:
                enabled_display = (
                    enabled_display_enabled if is_enabled else enabled_display_disabled
                )
                primary_display = (
                    primary_display_enabled if is_primary else primary_display_disabled
                )

                # Build a simple table for all non-exit routes:
                failover_content += f"""
                    <tr>
                        <td>{machine}</td>
                        <td><center>{enabled_display}</center></td>
                        <td><center>{primary_display}</center></td>
                    </tr>
                    """
            failover_content += "</tbody></table></p>"
        failover_content += markup_post

    ##############################################################################################
    # Step 3:  Get exit nodes only:
    # Get a set of nodes with exit routes:
    exit_node_list = set(
        route.machine.given_name
        for route in all_routes.routes
        if route.prefix in ("0.0.0.0/0", "::/0")
    )

    # Exit node display building:
    # Display by machine, not by route
    exit_content = (
        markup_pre
        + exit_title
        + """
        <p><table>
            <thead>
                <tr>
                    <th>Machine</th>
                    <th>Enabled</th>
                </tr>
            </thead>
        <tbody>
        """
    )
    # Get exit route ID's for each node in the list:
    for node in exit_node_list:
        node_exit_route_ids: list[int] = []
        exit_enabled = False
        exit_available = False
        machine_id = 0
        for route in all_routes.routes:
            if (
                route.prefix in ("0.0.0.0/0", "::/0")
                and route.machine.given_name == node
            ):
                node_exit_route_ids.append(route.id)
                machine_id = route.machine.id
                exit_available = True
                if route.enabled:
                    exit_enabled = True

        if exit_available:
            # Set up the display code:
            enabled = (
                f"<i id='{machine_id}-exit' onclick='toggle_exit("
                f"{node_exit_route_ids[0]}, {node_exit_route_ids[1]}, "
                '"{machine_id}-exit", "True",  "routes")\' '
                "class='material-icons green-text text-lighten-2 tooltipped' "
                "data-tooltip='Click to disable'>fiber_manual_record</i>"
            )
            disabled = (
                f"<i id='{machine_id}-exit' onclick='toggle_exit("
                f"{node_exit_route_ids[0]}, {node_exit_route_ids[1]}, "
                '"{machine_id}-exit", "False", "routes")\' '
                "class='material-icons red-text text-lighten-2 tooltipped' "
                "data-tooltip='Click to enable' >fiber_manual_record</i>"
            )
            # Set the displays:
            enabled_display = enabled if exit_enabled else disabled

            exit_content += f"""
                <tr>
                    <td>{node}</td>
                    <td width="60px"><center>{enabled_display}</center></td>
                </tr>
                """
    exit_content += "</tbody></table></p>" + markup_post

    content = route_content + failover_content + exit_content
    return Markup(content)
