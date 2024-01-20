//-----------------------------------------------------------
// Search on Users and Machines pages
//-----------------------------------------------------------
function show_search() {
    $('#nav-search').removeClass('hidden');
    $('#nav-search').addClass('show');
    $('#nav-content').removeClass('show');
    $('#nav-content').addClass('hidden');
}

function hide_search() {
    $('#nav-content').removeClass('hidden');
    $('#nav-content').addClass('show');
    $('#nav-search').removeClass('show');
    $('#nav-search').addClass('hidden');

    // Also remove the contents of the searchbox:
    document.getElementById("search").value = ""
    let cards = document.querySelectorAll('.searchable');
    for (var i = 0; i < cards.length; i++) {
        cards[i].classList.remove("hide");
    }
}

function liveSearch() {
    let cards = document.querySelectorAll('.searchable');
    let search_query = document.getElementById("search").value;

    for (var i = 0; i < cards.length; i++) {
        if (cards[i].textContent.toLowerCase().includes(search_query.toLowerCase())) {
            cards[i].classList.remove("hide");
        } else {
            cards[i].classList.add("hide");
        }
    }
}
//-----------------------------------------------------------
// General Helpers
//-----------------------------------------------------------
function loading() {
    return `<center>
                <div class="preloader-wrapper big active">
                    <div class="spinner-layer spinner-blue-only">
                        <div class="circle-clipper left">
                            <div class="circle">
                            </div>
                        </div>
                        <div class="gap-patch">
                            <div class="circle">
                            </div>
                        </div>
                        <div class="circle-clipper right">
                            <div class="circle"></div>
                        </div>
                    </div>
                </div>
            </center> `
}

function get_color(id) {
    // Define the colors... Seems like a good number to start with
    var colors = [
        "red         lighten-1",
        "teal        lighten-1",
        "blue        lighten-1",
        "blue-grey   lighten-1",
        "indigo      lighten-2",
        "green       lighten-1",
        "deep-orange lighten-1",
        "yellow      lighten-2",
        "purple      lighten-2",
        "indigo      lighten-2",
        "brown       lighten-1",
        "grey        lighten-1"
    ];
    index = id % colors.length
    return colors[index]
}

// Generic modal used for alerts / problems
function load_modal_generic(type, title, message) {
    console.log("Loading the generic modal")
    element = document.getElementById('generic_modal')
    content_element = document.getElementById('generic_modal_content')
    title_element = document.getElementById('generic_modal_title')

    content_element.innerHTML = loading()
    title_element.innerHTML = "Loading..."
    html = ""

    switch (type) {
        case "warning" || "Warning":
            title_html = "Warning"
            content_html = `
            <ul class="collection">
                <li class="collection-item avatar">
                    <i class="material-icons circle yellow">priority_high</i>
                    <span class="title">${title}</span>
                    <p>${message}</p>
                </li>
            </ul>`
            break;
        case "success" || "Success":
            title_html = "Success"
            content_html = `
            <ul class="collection">
                <li class="collection-item avatar">
                    <i class="material-icons circle green">check</i>
                    <span class="title">${title}</span>
                    <p>${message}</p>
                </li>
            </ul>`
            break;
        case "error" || "Error":
            title_html = "Error"
            content_html = `
            <ul class="collection">
                <li class="collection-item avatar">
                    <i class="material-icons circle red">warning</i>
                    <span class="title">${title}</span>
                    <p>${message}</p>
                </li>
            </ul>`
            break;
        case "information" || "Information":
            title_html = "Information"
            content_html = `
            <ul class="collection">
                <li class="collection-item avatar">
                    <i class="material-icons circle grey">help</i>
                    <span class="title">${title}</span>
                    <p>${message}</p>
                </li>
            </ul>`
            break;
    }
    title_element.innerHTML = title_html
    content_element.innerHTML = content_html

    var instance = M.Modal.getInstance(element);
    instance.open()
}

// https://stackoverflow.com/questions/3043775/how-to-escape-html#22706073
function escapeHTML(str) {
    var p = document.createElement("p");
    p.appendChild(document.createTextNode(str));
    return p.innerHTML;
}

// Enables the Floating Action Button (FAB) for the Machines and Users page
document.addEventListener('DOMContentLoaded', function () {
    var elems = document.querySelectorAll('.fixed-action-btn');
    var instances = M.FloatingActionButton.init(elems, { hoverEnabled: false });
});

// Init the date picker when adding PreAuth keys
document.addEventListener('DOMContentLoaded', function () {
    var elems = document.querySelectorAll('.datepicker');
    var instances = M.Datepicker.init(elems);
});

//-----------------------------------------------------------
// Settings Page Actions
//-----------------------------------------------------------
function test_key() {
    document.getElementById('test_modal_results').innerHTML = loading()
    var data = $.ajax({
        type: "GET",
        url: "api/test_key",
        success: function (response) {
            if (response == "Unauthenticated") {
                html = `
                <ul class="collection">
                    <li class="collection-item avatar">
                        <i class="material-icons circle red">warning</i>
                        <span class="title">Error</span>
                        <p>Key authentication failed.  Check your key.</p>
                    </li>
                </ul>
                `
                document.getElementById('test_modal_results').innerHTML = html
            } else {
                json = JSON.parse(response)
                var html = `
                    <ul class="collection">
                        <li class="collection-item avatar">
                            <i class="material-icons circle green">check</i>
                            <span class="title">Success</span>
                            <p>Key authenticated with the Headscale server.</p>
                        </li>
                    </ul>
                    <h6>Key Information</h6>
                    <table class="highlight">
                        <tbody>
                            <tr>
                                <td><b>Key ID</b></td>
                                <td>${json['id']}</td>
                            </tr>
                            <tr>
                                <td><b>Prefix</b></td>
                                <td>${json['prefix']}</td>
                            </tr>
                            <tr>
                                <td><b>Expiration Date</b></td>
                                <td>${json['expiration']}</td>
                            </tr>
                            <tr>
                                <td><b>Creation Date</b></td>
                                <td>${json['createdAt']}</td>
                            </tr>
                        </tbody>
                    </table>
                    `
                document.getElementById('test_modal_results').innerHTML = html
            }
        }
    })

}

function save_key() {
    var api_key = document.getElementById('api_key').value;
    if (!api_key) {
        html = `
        <ul class="collection">
            <li class="collection-item avatar">
                <i class="material-icons circle red">warning</i>
                <span class="title">Error</span>
                <p>You must enter an API key before saving.</p>
            </li>
        </ul>
        `
        document.getElementById('test_modal_results').innerHTML = html
        return
    };
    var data = { "api_key": api_key };
    $.ajax({
        type: "POST",
        url: "api/save_key",
        data: JSON.stringify(data),
        contentType: "application/json",
        success: function (response) {
            M.toast({ html: 'Key saved.  Testing...' });
            test_key();
        }
    })
}

//-----------------------------------------------------------
// Modal Loaders
//-----------------------------------------------------------
function load_modal_rename_user(user_id, old_name) {
    document.getElementById('modal_content').innerHTML = loading()
    document.getElementById('modal_title').innerHTML = "Loading..."
    document.getElementById('modal_confirm').className = "green btn-flat white-text"
    document.getElementById('modal_confirm').innerText = "Rename"

    modal = document.getElementById('card_modal');
    modal_title = document.getElementById('modal_title');
    modal_body = document.getElementById('modal_content');
    modal_confirm = document.getElementById('modal_confirm');

    modal_title.innerHTML = "Rename user '" + old_name + "'?"
    body_html = `
    <ul class="collection">
        <li class="collection-item avatar">
            <i class="material-icons circle">language</i>
            <span class="title">Information</span>
            <p>You are about to rename the user '${old_name}'</p>
        </li>
    </ul>
    <h6>New Name</h6>
    <div class="input-field">
        <i class="material-icons prefix">language</i>
        <input value='${old_name}' id="new_user_name_form" type="text" data-length="32">
    </div>
    `

    modal_body.innerHTML = body_html
    $(document).ready(function () { $('input#new_user_name_form').characterCounter(); });

    modal_confirm.setAttribute('onclick', 'rename_user(' + user_id + ', "' + old_name + '")')
}

function load_modal_delete_user(user_id, user_name) {
    document.getElementById('modal_content').innerHTML = loading()
    document.getElementById('modal_title').innerHTML = "Loading..."
    document.getElementById('modal_confirm').className = "red btn-flat white-text"
    document.getElementById('modal_confirm').innerText = "Delete"

    modal = document.getElementById('card_modal');
    modal_title = document.getElementById('modal_title');
    modal_body = document.getElementById('modal_content');
    modal_confirm = document.getElementById('modal_confirm');

    modal_title.innerHTML = "Delete user '" + user_name + "'?"
    body_html = `
    <ul class="collection">
        <li class="collection-item avatar">
            <i class="material-icons circle red">warning</i>
            <span class="title">Warning</span>
            <p>Are you sure you want to delete the user '${user_name}'?</p>
        </li>
    </ul>
    `
    modal_body.innerHTML = body_html
    modal_confirm.setAttribute('onclick', 'delete_user("' + user_id + '", "' + user_name + '")')
}

function load_modal_add_preauth_key(user_name) {
    document.getElementById('modal_content').innerHTML = loading()
    document.getElementById('modal_title').innerHTML = "Loading..."
    document.getElementById('modal_confirm').className = "green btn-flat white-text"
    document.getElementById('modal_confirm').innerText = "Add"

    modal = document.getElementById('card_modal');
    modal_title = document.getElementById('modal_title');
    modal_body = document.getElementById('modal_content');
    modal_confirm = document.getElementById('modal_confirm');

    modal_title.innerHTML = "Adding a PreAuth key to '" + user_name + "'"
    body_html = `
        <ul class="collection">
            <li class="collection-item avatar">
                <i class="material-icons circle">help</i>
                <span class="title">Information</span>
                <p>
                    <ul>
                        <li>Pre-Auth keys can be used to authenticate to Headscale without manually registering a machine.  Use the flag <code>--auth-key</code> to do so.</li>
                        <li>"Ephemeral" keys can be used to register devices that frequently come on and drop off the newtork (for example, docker containers)</li>
                        <li>Keys that are "Reusable" can be used multiple times.  Keys that are "One Time Use" will expire after their first use.</li> 
                    </ul>
                </p>
            </li>
        </ul>
        <h4>PreAuth Key Information</h4>
        <br>
        <input type="text" class="datepicker" id="preauth_key_expiration_date">
        <p>
            <label>
                <input type="checkbox" class="filled-in" id="checkbox-reusable"/>
                <span>Reusable</span>
            </label>
        </p>
        <p>
            <label>
                <input type="checkbox" class="filled-in" id="checkbox-ephemeral" />
                <span>Ephemeral</span>
            </label>
        </p>
    `

    modal_body.innerHTML = body_html

    // Init the date picker
    M.Datepicker.init(document.querySelector('.datepicker'), { format: 'yyyy-mm-dd' });

    modal_confirm.setAttribute('onclick', 'add_preauth_key("' + user_name + '")')
}

function load_modal_expire_preauth_key(user_name, key) {
    document.getElementById('modal_content').innerHTML = loading()
    document.getElementById('modal_title').innerHTML = "Loading..."
    document.getElementById('modal_confirm').className = "red lighten-2 btn-flat white-text"
    document.getElementById('modal_confirm').innerText = "Expire"

    modal = document.getElementById('card_modal');
    modal_title = document.getElementById('modal_title');
    modal_body = document.getElementById('modal_content');
    modal_confirm = document.getElementById('modal_confirm');

    modal_title.innerHTML = "Expire PreAuth Key?"
    body_html = `
    <ul class="collection">
        <li class="collection-item avatar">
            <i class="material-icons circle red">warning</i>
            <span class="title">Warning</span>
            <p>Are you sure you want to expire this key?  It will become unusable afterwards, and any machine currently using it will disconnect.</p>
        </li>
    </ul>
    `
    modal_body.innerHTML = body_html
    modal_confirm.setAttribute('onclick', 'expire_preauth_key("' + user_name + '", "' + key + '")')
}

function load_modal_move_machine(machine_id) {
    document.getElementById('modal_content').innerHTML = loading()
    document.getElementById('modal_title').innerHTML = "Loading..."
    document.getElementById('modal_confirm').className = "green btn-flat white-text"
    document.getElementById('modal_confirm').innerText = "Move"

    var data = { "id": machine_id }
    $.ajax({
        type: "POST",
        url: "api/machine_information",
        data: JSON.stringify(data),
        contentType: "application/json",
        success: function (headscale) {
            $.ajax({
                type: "POST",
                url: "api/get_users",
                success: function (response) {
                    modal = document.getElementById('card_modal');
                    modal_title = document.getElementById('modal_title');
                    modal_body = document.getElementById('modal_content');
                    modal_confirm = document.getElementById('modal_confirm');

                    modal_title.innerHTML = "Move machine '" + headscale.node.givenName + "'?"

                    select_html = `<h6>Select a User</h6><select id='move-select'>`
                    for (let i = 0; i < response.users.length; i++) {
                        var name = response["users"][i]["name"]
                        select_html = select_html + `<option value="${name}">${name}</option>`
                    }
                    select_html = select_html + `</select>`

                    body_html = `
                    <ul class="collection">
                        <li class="collection-item avatar">
                            <i class="material-icons circle">language</i>
                            <span class="title">Information</span>
                            <p>You are about to move ${headscale.node.givenName} to a new user.</p>
                        </li>
                    </ul>`
                    body_html = body_html + select_html
                    body_html = body_html + `<h6>Machine Information</h6>
                    <table class="highlight">
                        <tbody>
                            <tr>
                                <td><b>Machine ID</b></td>
                                <td>${headscale.node.id}</td>
                            </tr>
                            <tr>
                                <td><b>Hostname</b></td>
                                <td>${headscale.node.name}</td>
                            </tr>
                            <tr>
                                <td><b>User</b></td>
                                <td>${headscale.node.user.name}</td>
                            </tr>
                        </tbody>
                    </table>
                    `

                    modal_body.innerHTML = body_html
                    M.FormSelect.init(document.querySelectorAll('select'))
                }
            })
            modal_confirm.setAttribute('onclick', 'move_machine(' + machine_id + ')')
        }
    })
}

function load_modal_delete_machine(machine_id) {
    document.getElementById('modal_content').innerHTML = loading()
    document.getElementById('modal_title').innerHTML = "Loading..."
    document.getElementById('modal_confirm').className = "red btn-flat white-text"
    document.getElementById('modal_confirm').innerText = "Delete"

    var data = { "id": machine_id }
    $.ajax({
        type: "POST",
        url: "api/machine_information",
        data: JSON.stringify(data),
        contentType: "application/json",
        success: function (response) {
            modal = document.getElementById('card_modal');
            modal_title = document.getElementById('modal_title');
            modal_body = document.getElementById('modal_content');
            modal_confirm = document.getElementById('modal_confirm');

            modal_title.innerHTML = "Delete machine '" + response.node.givenName + "'?"
            body_html = `
            <ul class="collection">
                <li class="collection-item avatar">
                    <i class="material-icons circle red">warning</i>
                    <span class="title">Warning</span>
                    <p>Are you sure you want to delete ${response.node.givenName}?</p>
                </li>
            </ul>
            <h6>Machine Information</h6>
            <table class="highlight">
                <tbody>
                    <tr>
                        <td><b>Machine ID</b></td>
                        <td>${response.node.id}</td>
                    </tr>
                    <tr>
                        <td><b>Hostname</b></td>
                        <td>${response.node.name}</td>
                    </tr>
                    <tr>
                        <td><b>User</b></td>
                        <td>${response.node.user.name}</td>
                    </tr>
                </tbody>
            </table>
            `
            modal_body.innerHTML = body_html
            modal_confirm.setAttribute('onclick', 'delete_machine(' + machine_id + ')')
        }
    })
}

function load_modal_rename_machine(machine_id) {
    document.getElementById('modal_content').innerHTML = loading()
    document.getElementById('modal_title').innerHTML = "Loading..."
    document.getElementById('modal_confirm').className = "green btn-flat white-text"
    document.getElementById('modal_confirm').innerText = "Rename"
    var data = { "id": machine_id }
    $.ajax({
        type: "POST",
        url: "api/machine_information",
        data: JSON.stringify(data),
        contentType: "application/json",
        success: function (response) {
            modal = document.getElementById('card_modal');
            modal_title = document.getElementById('modal_title');
            modal_body = document.getElementById('modal_content');
            modal_confirm = document.getElementById('modal_confirm');

            modal_title.innerHTML = "Rename machine '" + response.node.givenName + "'?"
            body_html = `
            <ul class="collection">
                <li class="collection-item avatar">
                    <i class="material-icons circle">devices</i>
                    <span class="title">Information</span>
                    <p>You are about to rename ${response.node.givenName}</p>
                </li>
            </ul>
            <h6>New Name</h6>
            <div class="input-field">
                <input value='${response.node.givenName}' id="new_name_form" type="text">
                <label for="new_name_form" class="active">New Machine Name</label>
            </div>
            <h6>Machine Information</h6>
            <table class="highlight">
                <tbody>
                    <tr>
                        <td><b>Machine ID</b></td>
                        <td>${response.node.id}</td>
                    </tr>
                    <tr>
                        <td><b>Hostname</b></td>
                        <td>${response.node.name}</td>
                    </tr>
                    <tr>
                        <td><b>User</b></td>
                        <td>${response.node.user.name}</td>
                    </tr>
                </tbody>
            </table>
            `
            modal_body.innerHTML = body_html
            modal_confirm.setAttribute('onclick', 'rename_machine(' + machine_id + ')')
        }
    })
}

function load_modal_add_machine() {
    $.ajax({
        type: "POST",
        url: "api/get_users",
        success: function (response) {
            modal_body = document.getElementById('default_add_new_machine_modal');
            modal_confirm = document.getElementById('new_machine_modal_confirm');

            select_html = `
            <div class="col s12 m6">
                <div class="input-field">
                    <i class="material-icons prefix">language</i>
                    <select id='add_machine_user_select'>
                        <option value="" disabled selected>Select a User</option>`
            for (let i = 0; i < response.users.length; i++) {
                var name = response["users"][i]["name"]
                select_html = select_html + `<option value="${name}">${name}</option>`
            }
            select_html = select_html + `
                        <label>Select a User</label>
                    </select>
                </div>
            </div>`
            select_html = select_html + `
            <div class="col s12 m6">
                <div class="input-field">
                    <i class="material-icons prefix">vpn_key</i>
                    <input id="add_machine_key_field" type="password">
                    <label for="add_machine_key_field">Machine Registration Key</label>
                </div>
            </div>`
            for (let i = 0; i < response.users.length; i++) {
                var name = response["users"][i]["name"]
            }

            modal_body.innerHTML = select_html
            // Initialize the form and the machine tabs
            M.FormSelect.init(document.querySelectorAll('select'), { classes: 'add_machine_selector_class' })
            M.Tabs.init(document.getElementById('new_machine_tabs'));
        }
    })
}

//-----------------------------------------------------------
// Machine Page Actions
//-----------------------------------------------------------
function delete_chip(machine_id, chipsData) {
    // We need to get ALL the current tags -- We don't care about what's deleted, just what's remaining
    // chipsData is an array generated from from the creation of the array.
    chips = JSON.stringify(chipsData)

    var formattedData = [];
    for (let tag in chipsData) {
        formattedData[tag] = '"tag:' + chipsData[tag].tag + '"'
    }
    var tags_list = '{"tags": [' + formattedData + ']}'
    var data = { "id": machine_id, "tags_list": tags_list }

    $.ajax({
        type: "POST",
        url: "api/set_machine_tags",
        data: JSON.stringify(data),
        contentType: "application/json",
        success: function (response) {
            M.toast({ html: 'Tag removed.' });
        }
    })
}

function add_chip(machine_id, chipsData) {
    chips = JSON.stringify(chipsData).toLowerCase()
    chipsData[chipsData.length - 1].tag = chipsData[chipsData.length - 1].tag.trim().replace(/\s+/g, '-')
    last_chip_fixed = chipsData[chipsData.length - 1].tag

    var formattedData = [];
    for (let tag in chipsData) {
        formattedData[tag] = '"tag:' + chipsData[tag].tag + '"'
    }
    var tags_list = '{"tags": [' + formattedData + ']}'
    var data = { "id": machine_id, "tags_list": tags_list }

    $.ajax({
        type: "POST",
        url: "api/set_machine_tags",
        data: JSON.stringify(data),
        contentType: "application/json",
        success: function (response) {
            M.toast({ html: 'Tag "' + last_chip_fixed + '" added.' });
        }
    })
}

function add_machine() {
    var key = document.getElementById('add_machine_key_field').value
    var user = document.getElementById('add_machine_user_select').value
    var data = { "key": key, "user": user }

    if (user == "") {
        load_modal_generic("error", "User is empty", "Select a user before submitting")
        return
    }
    if (key == "") {
        load_modal_generic("error", "Key is empty", "Input the key generated by your <code>tailscale login</code> command")
        return
    }

    $.ajax({
        type: "POST",
        url: "api/register_machine",
        data: JSON.stringify(data),
        contentType: "application/json",
        success: function (response) {
            if (response.node) {
                window.location.reload()
                return
            }
            load_modal_generic("error", "Error adding machine", response.message)
            return
        }
    })
}

function rename_machine(machine_id) {
    var new_name = document.getElementById('new_name_form').value;
    var data = { "id": machine_id, "new_name": new_name };

    // String to test against
    var regexIT = /[`!@#$%^&*()_+\=\[\]{};':"\\|,.<>\/?~]/;
    if (regexIT.test(new_name)) { load_modal_generic("error", "Invalid Name", "Name cannot contain special characters ('" + regexIT + "')"); return }
    // If there are characters other than - and alphanumeric, throw an error
    if (new_name.includes(' ')) { load_modal_generic("error", "Name cannot have spaces", "Allowed characters are dashes (-) and alphanumeric characters"); return }
    // If it is longer than 32 characters, throw an error
    if (new_name.length > 32) { load_modal_generic("error", "Name is too long", "The name name is too long.  Maximum length is 32 characters"); return }
    // If the new_name is empty, throw an error
    if (!new_name) { load_modal_generic("error", "Name can't be empty", "Please enter a machine name before submitting."); return }

    $.ajax({
        type: "POST",
        url: "api/rename_machine",
        data: JSON.stringify(data),
        contentType: "application/json",
        success: function (response) {

            if (response.status == "True") {
                // Get the modal element and close it
                modal_element = document.getElementById('card_modal')
                M.Modal.getInstance(modal_element).close()

                document.getElementById(machine_id + '-name-container').innerHTML = machine_id + ". " + escapeHTML(new_name)
                M.toast({ html: 'Machine ' + machine_id + ' renamed to ' + escapeHTML(new_name) });
            } else {
                load_modal_generic("error", "Error setting the machine name", "Headscale response:  " + JSON.stringify(response.body.message))
            }
        }
    })
}

function move_machine(machine_id) {
    new_user = document.getElementById('move-select').value
    var data = { "id": machine_id, "new_user": new_user };

    $.ajax({
        type: "POST",
        url: "api/move_user",
        data: JSON.stringify(data),
        contentType: "application/json",
        success: function (response) {
            // Get the modal element and close it
            modal_element = document.getElementById('card_modal')
            M.Modal.getInstance(modal_element).close()

            document.getElementById(machine_id + '-user-container').innerHTML = response.node.user.name
            document.getElementById(machine_id + '-ns-badge').innerHTML = response.node.user.name

            // Get the color and set it
            var user_color = get_color(response.node.user.id)
            document.getElementById(machine_id + '-ns-badge').className = "badge ipinfo " + user_color + " white-text hide-on-small-only"

            M.toast({ html: "'" + response.node.givenName + "' moved to user " + response.node.user.name });
        }
    })
}

function delete_machine(machine_id) {
    var data = { "id": machine_id };
    $.ajax({
        type: "POST",
        url: "api/delete_machine",
        data: JSON.stringify(data),
        contentType: "application/json",
        success: function (response) {
            // Get the modal element and close it
            modal_element = document.getElementById('card_modal')
            M.Modal.getInstance(modal_element).close()

            // When the machine is deleted, hide its collapsible:
            document.getElementById(machine_id + '-main-collapsible').className = "collapsible popout hide";

            M.toast({ html: 'Machine deleted.' });
        }
    })
}

function toggle_exit(route1, route2, exit_id, current_state, page) {
    var data1 = { "route_id": route1, "current_state": current_state }
    var data2 = { "route_id": route2, "current_state": current_state }
    var element = document.getElementById(exit_id);

    var disabledClass = ""
    var enabledClass = ""

    if (page == "machines") {
        disabledClass = "waves-effect waves-light btn-small red lighten-2 tooltipped";
        enabledClass = "waves-effect waves-light btn-small green lighten-2 tooltipped";
    }
    if (page == "routes") {
        disabledClass = "material-icons red-text text-lighten-2 tooltipped";
        enabledClass = "material-icons green-text text-lighten-2 tooltipped";
    }

    var disabledTooltip = "Click to enable"
    var enabledTooltip = "Click to disable"
    var disableState = "False"
    var enableState = "True"
    var action_taken = "unchanged.";

    $.ajax({
        type: "POST",
        url: "api/update_route",
        data: JSON.stringify(data1),
        contentType: "application/json",
        success: function (response) {
            $.ajax({
                type: "POST",
                url: "api/update_route",
                data: JSON.stringify(data2),
                contentType: "application/json",
                success: function (response) {
                    // Response is a JSON object containing the Headscale API response of /v1/api/machines/<id>/route
                    if (element.className == disabledClass) {
                        element.className = enabledClass
                        action_taken = "enabled."
                        element.setAttribute('data-tooltip', enabledTooltip)
                        element.setAttribute('onclick', 'toggle_exit(' + route1 + ', ' + route2 + ', "' + exit_id + '", "' + enableState + '", "' + page + '")')
                    } else if (element.className == enabledClass) {
                        element.className = disabledClass
                        action_taken = "disabled."
                        element.setAttribute('data-tooltip', disabledTooltip)
                        element.setAttribute('onclick', 'toggle_exit(' + route1 + ', ' + route2 + ', "' + exit_id + '", "' + disableState + '", "' + page + '")')
                    }
                    M.toast({ html: 'Exit Route ' + action_taken });
                }
            })
        }
    })
}

function toggle_route(route_id, current_state, page) {
    var data = { "route_id": route_id, "current_state": current_state }
    var element = document.getElementById(route_id);

    var disabledClass = ""
    var enabledClass = ""

    if (page == "machines") {
        disabledClass = "waves-effect waves-light btn-small red lighten-2 tooltipped";
        enabledClass = "waves-effect waves-light btn-small green lighten-2 tooltipped";
    }
    if (page == "routes") {
        disabledClass = "material-icons red-text text-lighten-2 tooltipped";
        enabledClass = "material-icons green-text text-lighten-2 tooltipped";
    }

    var disabledTooltip = "Click to enable"
    var enabledTooltip = "Click to disable"
    var disableState = "False"
    var enableState = "True"
    var action_taken = "unchanged.";
    $.ajax({
        type: "POST",
        url: "api/update_route",
        data: JSON.stringify(data),
        contentType: "application/json",
        success: function (response) {
            if (element.className == disabledClass) {
                element.className = enabledClass
                action_taken = "enabled."
                element.setAttribute('data-tooltip', enabledTooltip)
                element.setAttribute('onclick', 'toggle_route(' + route_id + ', "' + enableState + '", "' + page + '")')
            } else if (element.className == enabledClass) {
                element.className = disabledClass
                action_taken = "disabled."
                element.setAttribute('data-tooltip', disabledTooltip)
                element.setAttribute('onclick', 'toggle_route(' + route_id + ', "' + disableState + '", "' + page + '")')
            }
            M.toast({ html: 'Route ' + action_taken });
        }
    })
}

function get_routes() {
    console.log("Getting info for all routes")
    var data
    $.ajax({
        async: false,
        type: "POST",
        url: "api/get_routes",
        contentType: "application/json",
        success: function (response) {
            console.log("Got all routes.")
            data = response
        }
    })
    return data
}

function toggle_failover_route_routespage(routeid, current_state, prefix, route_id_list) {
    // First, toggle the route:
    // toggle_route(route_id, current_state, page)
    var data = { "route_id": routeid, "current_state": current_state }
    console.log("Data:  " + JSON.stringify(data))
    console.log("Passed in:  " + routeid + ", " + current_state + ", " + prefix + ", " + route_id_list)
    var element = document.getElementById(routeid);

    var disabledClass = "material-icons red-text text-lighten-2 tooltipped";
    var enabledClass = "material-icons green-text text-lighten-2 tooltipped";
    var failover_disabledClass = "material-icons small left red-text text-lighten-2"
    var failover_enabledClass = "material-icons small left green-text text-lighten-2"

    var disabledTooltip = "Click to enable"
    var enabledTooltip = "Click to disable"
    var disableState = "False"
    var enableState = "True"
    var action_taken = "unchanged."

    $.ajax({
        type: "POST",
        url: "api/update_route",
        data: JSON.stringify(data),
        contentType: "application/json",
        success: function (response) {
            console.log("Success:  Route ID:  " + routeid)
            console.log("Success: route_id_list:  " + route_id_list)
            if (element.className == disabledClass) {
                element.className = enabledClass
                action_taken = "enabled."
                element.setAttribute('data-tooltip', enabledTooltip)
                element.setAttribute('onclick', 'toggle_failover_route_routespage(' + routeid + ', "' + enableState + '", "' + prefix + '", [' + route_id_list + '])')
            } else if (element.className == enabledClass) {
                element.className = disabledClass
                action_taken = "disabled."
                element.setAttribute('data-tooltip', disabledTooltip)
                element.setAttribute('onclick', 'toggle_failover_route_routespage(' + routeid + ', "' + disableState + '", "' + prefix + '", [' + route_id_list + '])')
            }
            M.toast({ html: 'Route ' + action_taken });

            // Get all route info:
            console.log("Getting info for prefix " + prefix)
            var routes = get_routes()
            var failover_enabled = false

            // Get the primary and enabled displays for the prefix:
            for (let i = 0; i < route_id_list.length; i++) {
                console.log("route_id_list[" + i + "]: " + route_id_list[i])
                var route_id = route_id_list[i]
                var route_index = route_id - 1
                console.log("Looking for route " + route_id + " at index " + route_index)
                console.log("isPrimary:  " + routes["routes"][route_index]["isPrimary"])

                // Set the Primary class:
                var primary_element = document.getElementById(route_id + "-primary")
                var primary_status = routes["routes"][route_index]["isPrimary"]
                var enabled_status = routes["routes"][route_index]["enabled"]

                console.log("enabled_status:  " + enabled_status)

                if (enabled_status == true) {
                    failover_enabled = true
                }

                console.log("Setting primary class '" + route_id + "-primary':  " + primary_status)
                if (primary_status == true) {
                    console.log("Detected this route is primary.  Setting the class")
                    primary_element.className = enabledClass
                } else if (primary_status == false) {
                    console.log("Detected this route is NOT primary.  Setting the class")
                    primary_element.className = disabledClass
                }
            }

            // if any route is enabled, set the prefix enable icon to enabled:
            var failover_element = document.getElementById(prefix)
            console.log("Failover enabled:  " + failover_enabled)
            if (failover_enabled == true) {
                failover_element.className = failover_enabledClass
            }
            else if (failover_enabled == false) {
                failover_element.className = failover_disabledClass
            }
        }
    })
}

function toggle_failover_route(route_id, current_state, color) {
    var data = { "route_id": route_id, "current_state": current_state }
    $.ajax({
        type: "POST",
        url: "api/update_route",
        data: JSON.stringify(data),
        contentType: "application/json",
        success: function (response) {
            // Response is a JSON object containing the Headscale API response of /v1/api/machines/<id>/route
            var element = document.getElementById(route_id);
            var disabledClass = "waves-effect waves-light btn-small red lighten-2 tooltipped";
            var enabledClass = "waves-effect waves-light btn-small " + color + " lighten-2 tooltipped";
            var disabledTooltip = "Click to enable (Failover Pair)"
            var enabledTooltip = "Click to disable (Failover Pair)"
            var disableState = "False"
            var enableState = "True"
            var action_taken = "unchanged.";

            if (element.className == disabledClass) {
                // 1.  Change the class to change the color of the icon
                // 2.  Change the "action taken" for the M.toast popup
                // 3.  Change the tooltip to say "Click to enable/disable"
                element.className = enabledClass
                var action_taken = "enabled."
                element.setAttribute('data-tooltip', enabledTooltip)
                element.setAttribute('onclick', 'toggle_failover_route(' + route_id + ', "' + enableState + '", "' + color + '")')
            } else if (element.className == enabledClass) {
                element.className = disabledClass
                var action_taken = "disabled."
                element.setAttribute('data-tooltip', disabledTooltip)
                element.setAttribute('onclick', 'toggle_failover_route(' + route_id + ', "' + disableState + '", "' + color + '")')
            }
            M.toast({ html: 'Route ' + action_taken });
        }
    })
}

//-----------------------------------------------------------
// Machine Page Helpers
//-----------------------------------------------------------
function btn_toggle(state) {
    if (state == "show") { document.getElementById('new_machine_modal_confirm').className = 'green btn-flat white-text' }
    else { document.getElementById('new_machine_modal_confirm').className = 'green btn-flat white-text hide' }
}

//-----------------------------------------------------------
// User Page Actions
//-----------------------------------------------------------
function rename_user(user_id, old_name) {
    var new_name = document.getElementById('new_user_name_form').value;
    var data = { "old_name": old_name, "new_name": new_name }

    // String to test against
    var regexIT = /[`!@#$%^&*()_+\=\[\]{};':"\\|,.<>\/?~]/;
    if (regexIT.test(new_name)) { load_modal_generic("error", "Invalid Name", "Name cannot contain special characters ('" + regexIT + "')"); return }
    // If there are characters other than - and alphanumeric, throw an error
    if (new_name.includes(' ')) { load_modal_generic("error", "Name cannot have spaces", "Allowed characters are dashes (-) and alphanumeric characters"); return }
    // If it is longer than 32 characters, throw an error
    if (new_name.length > 32) { load_modal_generic("error", "Name is too long", "The user name is too long.  Maximum length is 32 characters"); return }
    // If the new_name is empty, throw an error
    if (!new_name) { load_modal_generic("error", "Name can't be empty", "The user name cannot be empty."); return }

    $.ajax({
        type: "POST",
        url: "api/rename_user",
        data: JSON.stringify(data),
        contentType: "application/json",
        success: function (response) {
            if (response.status == "True") {
                // Get the modal element and close it
                modal_element = document.getElementById('card_modal')
                M.Modal.getInstance(modal_element).close()

                // Rename the user on the page:
                document.getElementById(user_id + '-name-span').innerHTML = escapeHTML(new_name)

                // Set the button to use the NEW name as the OLD name for both buttons
                var rename_button_sm = document.getElementById(user_id + '-rename-user-sm')
                rename_button_sm.setAttribute('onclick', 'load_modal_rename_user(' + user_id + ', "' + new_name + '")')
                var rename_button_lg = document.getElementById(user_id + '-rename-user-lg')
                rename_button_lg.setAttribute('onclick', 'load_modal_rename_user(' + user_id + ', "' + new_name + '")')

                // Send the completion toast
                M.toast({ html: "User '" + old_name + "' renamed to '" + new_name + "'." })
            } else {
                load_modal_generic("error", "Error setting user name", "Headscale response:  " + JSON.stringify(response.body.message))
            }
        }
    })
}

function delete_user(user_id, user_name) {
    var data = { "name": user_name };
    $.ajax({
        type: "POST",
        url: "api/delete_user",
        data: JSON.stringify(data),
        contentType: "application/json",
        success: function (response) {
            if (response.status == "True") {
                // Get the modal element and close it
                modal_element = document.getElementById('card_modal')
                M.Modal.getInstance(modal_element).close()

                // When the machine is deleted, hide its collapsible:
                document.getElementById(user_id + '-main-collapsible').className = "collapsible popout hide";

                M.toast({ html: 'User deleted.' });
            } else {
                // We errored.  Decipher the error Headscale sent us and display it:
                load_modal_generic("error", "Error deleting user", "Headscale response:  " + JSON.stringify(response.body.message))
            }
        }
    })
}

function add_user() {
    var user_name = document.getElementById('add_user_name_field').value
    var data = { "name": user_name }
    $.ajax({
        type: "POST",
        url: "api/add_user",
        data: JSON.stringify(data),
        contentType: "application/json",
        success: function (response) {
            if (response.status == "True") {
                // Get the modal element and close it
                modal_element = document.getElementById('card_modal')
                M.Modal.getInstance(modal_element).close()

                // Send the completion toast
                M.toast({ html: "User '" + user_name + "' added to Headscale.  Refreshing..." })
                window.location.reload()
            } else {
                // We errored.  Decipher the error Headscale sent us and display it:
                load_modal_generic("error", "Error adding  user", "Headscale response:  " + JSON.stringify(response.body.message))
            }
        }
    })
}

function add_preauth_key(user_name) {
    var date = document.getElementById('preauth_key_expiration_date').value
    var ephemeral = document.getElementById('checkbox-ephemeral').checked
    var reusable = document.getElementById('checkbox-reusable').checked
    var expiration = date + "T00:00:00.000Z" // Headscale format.

    // If there is no date, error:
    if (!date) { load_modal_generic("error", "Invalid Date", "Please enter a valid date"); return }
    var data = { "user": user_name, "reusable": reusable, "ephemeral": ephemeral, "expiration": expiration }

    $.ajax({
        type: "POST",
        url: "api/add_preauth_key",
        data: JSON.stringify(data),
        contentType: "application/json",
        success: function (response) {
            if (response.status == "True") {
                // Send the completion toast
                M.toast({ html: 'PreAuth key created in user ' + user_name })
                // If this is successfull, we should reload the table and close the modal:
                var user_data = { "name": user_name }
                $.ajax({
                    type: "POST",
                    url: "api/build_preauthkey_table",
                    data: JSON.stringify(user_data),
                    contentType: "application/json",
                    success: function (table_data) {
                        table = document.getElementById(user_name + '-preauth-keys-collection')
                        table.innerHTML = table_data
                        // The tooltips need to be re-initialized afterwards:
                        M.Tooltip.init(document.querySelectorAll('.tooltipped'))
                    }
                })
                // Get the modal element and close it
                modal_element = document.getElementById('card_modal')
                M.Modal.getInstance(modal_element).close()

                // The tooltips need to be re-initialized afterwards:
                M.Tooltip.init(document.querySelectorAll('.tooltipped'))

            } else {
                load_modal_generic("error", "Error adding a pre-auth key", "Headscale response:  " + JSON.stringify(response.body.message))
            }
        }
    })
}

function expire_preauth_key(user_name, key) {
    var data = { "user": user_name, "key": key }

    $.ajax({
        type: "POST",
        url: "api/expire_preauth_key",
        data: JSON.stringify(data),
        contentType: "application/json",
        success: function (response) {
            if (response.status == "True") {
                // Send the completion toast
                M.toast({ html: 'PreAuth expired in ' + user_name })
                // If this is successfull, we should reload the table and close the modal:
                var user_data = { "name": user_name }
                $.ajax({
                    type: "POST",
                    url: "api/build_preauthkey_table",
                    data: JSON.stringify(user_data),
                    contentType: "application/json",
                    success: function (table_data) {
                        table = document.getElementById(user_name + '-preauth-keys-collection')
                        table.innerHTML = table_data
                        // The tooltips need to be re-initialized afterwards:
                        M.Tooltip.init(document.querySelectorAll('.tooltipped'))
                    }
                })
                // Get the modal element and close it
                modal_element = document.getElementById('card_modal')
                M.Modal.getInstance(modal_element).close()

                // The tooltips need to be re-initialized afterwards:
                M.Tooltip.init(document.querySelectorAll('.tooltipped'))

            } else {
                load_modal_generic("error", "Error expiring a pre-auth key", "Headscale response:  " + JSON.stringify(response.body.message))
            }
        }
    })
}

//-----------------------------------------------------------
// User Page Helpers
//-----------------------------------------------------------
// Toggle expired items on the Users PreAuth section:
function toggle_expired() {
    var toggle_hide = document.getElementsByClassName('expired-row');
    var hidden = document.getElementsByClassName('expired-row hide');

    if (hidden.length == 0) {
        for (var i = 0; i < toggle_hide.length; i++) {
            toggle_hide[i].className = "expired-row hide";
        }
    } else if (hidden.length > 0) {
        for (var i = 0; i < toggle_hide.length; i++) {
            toggle_hide[i].className = "expired-row";
        }
    }
}

// Copy a PreAuth Key to the clipboard.  Show only the Prefix by default
function copy_preauth_key(key) {
    navigator.clipboard.writeText(key);
    M.toast({ html: 'PreAuth key copied to clipboard.' })
}
