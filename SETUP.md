*PR's to help expand and improve documentation are always welcome!*

# Installation and Setup
* Use [docker-compose.yml](docker-compose.yml) as an example
* Containers are published to [GHCR](https://github.com/users/iFargle/packages/container/package/headscale-webui) and [Docker Hub](https://hub.docker.com/r/ifargle/headscale-webui)

# Contents
  * [Docker Compose](#docker-compose)
  * [Reverse Proxies](#reverse-proxies)
  * [Authentication](#authentication)

---
# Docker Compose
## Environment Settings
  * `TZ` - Set this to your current timezone.  Example:  `Asia/Tokyo`
  * `COLOR` Set this to your preferred color scheme.  See the [MaterializeCSS docs](https://materializecss.github.io/materialize/color.html#palette) for examples.  Only set the "base" color -- ie, instead of `blue-gray darken-1`, just use `blue-gray`.
  * `HS_SERVER` is the URL for your Headscale control server.
  * `SCRIPT_NAME` is your "Base Path" for hosting.  For example, if you want to host on http://localhost/admin, set this to `/admin`, otherwise remove this variable entirely.
  * `KEY` is your encryption key.  Set this to a random value generated from `openssl rand -base64 32`
  * `AUTH_TYPE` can be set to `Basic` or `OIDC`.  See the [Authentication](#Authentication) section below for more information.
  * `LOG_LEVEL` can be one of `Debug`, `Info`, `Warning`, `Error`, or `Critical` for decreasing verbosity.  Default is `Info` if removed from your Environment.
---
# Podman rootless container

A rootless container can be a good choice when running headscale-webui with Podman.

To achieve this, the option `allow_host_loopback` for the slirp4netns network driver must be explicitly set. This will allow the container to contact sockets listening on the host (specifically, headscale).

By default, slirp4netns will present the host on the IP address `10.0.2.2` (adjust accordingly if you specify different addressing options), so this IP will be the address to set in the HS_SERVER environment variable (along with the port number) when spinning the container.
For the rest of the enviroment settings, the considerations done for the Docker example above still hold.

* Example:
```
podman run -d --network slirp4netns:allow_host_loopback=true -v /etc/headscale:/etc/headscale:ro \
           -p 5000:5000 --name headscale-webui -e HS_SERVER=http://10.0.2.2:8080 -e KEY=YOUR_ENC_KEY \
           -e DOMAIN_NAME=http://headscale-webui:5000 -e SCRIPT_NAME=/admin ifargle/headscale-webui:latest
```

---
# Reverse Proxies
*If your reverse proxy isn't listed or doesn't work, please open up a [new issue](https://github.com/iFargle/headscale-webui/issues/new) and it will be worked on.*

## Traefik with SSL
1.  Use the following labels for your container.  You may need to adjust slightly to fit your setup.
    * You will need to change `[DOMAIN]`, `[SCRIPT_NAME]`, and the `entrypoint` to fit your setup.
    * If you are hosting on `SCRIPT_NAME` of `/`, you can remove `&& (PathPrefix(`/[SCRIPT_NAME]/`) || PathPrefix(`/[SCRIPT_NAME]`)`
```
    labels:
      # Traefik Configs
      - "traefik.enable=true"
      - "traefik.http.routers.headscale-webui.entrypoints=web-secure"
      - "traefik.http.routers.headscale-webui.rule=Host(`[DOMAIN]`) && (PathPrefix(`/[SCRIPT_NAME]/`) || PathPrefix(`/[SCRIPT_NAME]`))"
      - "traefik.http.services.headscale-webui.loadbalancer.server.port=5000"
      - "traefik.http.routers.headscale-webui.tls.certresolver=letsencrypt"
```

## nginx
1.  Replace `[SCRIPT_NAME]` with the one you set above.
```
location /[SCRIPT_NAME] {
proxy_pass http://127.0.0.1:5000/[SCRIPT_NAME];
proxy_http_version 1.1;
proxy_set_header Host $server_name;
proxy_buffering off;
proxy_set_header X-Real-IP $remote_addr;
proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
proxy_set_header X-Forwarded-Proto $http_x_forwarded_proto;
    auth_basic "Administrator's Area";
    auth_basic_user_file /etc/nginx/htpasswd;
}
```

## Caddy
1.  Replace `[DOMAIN]` with your domain, `[HEADSCALE-WEBUI ADDRESS]` with the internal endpoint of your deployment (by default, this will be `http://headscale-webui:5000`), and `[HS_SERVER]` with your Headscale server.
  * This will set up your Headscale Web UI under `[SCRIPT_NAME] `on the same domain as your Headscale control server.
  * Example:
    * Headscale will be reachable at `https://[DOMAIN]`, Headscale-WebUI will be reachable at `https://[DOMAIN]/[SCRIPT_NAME]`
```
https://[DOMAIN] {
        reverse_proxy [SCRIPT_NAME]* [HEADSCALE-WEBUI ADDRESS]
        reverse_proxy * [HS_SERVER]
}
```
* Example:  
```
https://example.com {
        reverse_proxy /admin* http://headscale-webui:5000

        reverse_proxy * http://headscale:8080
}
```

--- 
# Authentication
*If your OIDC provider isn't listed or doesn't work, please open up a [new issue](https://github.com/iFargle/headscale-webui/issues/new) and it will be worked on.*

## No Authentication
1.  If you use your reverse proxy for authentication, simply remove `AUTH_TYPE` from your environment variables.

## Basic Auth
1.  Basic Auth is a relatively simple setup. Set the following environment variables in `docker-compose.yml`:
    * Set `AUTH_TYPE` to `basic`
    * Set `BASIC_AUTH_USER` to a username, i.e. `admin`
    * Set `BASIC_AUTH_PASS` to set your password.

## OpenID Connect Integration
### Authelia
1.  In your Authelia `configuration.yml` file, add a new client:
```
      - id: headscale-webui
        description: Headscale WebUI
        secret: [SECRET]
        public: false
        authorization_policy: two_factor
        redirect_uris:
          - https://[DOMAIN]/[SCRIPT_NAME]/oidc_callback
        scopes:
          - openid
          - profile
          - email
```
2.  Set `AUTH_TYPE` environment variable in your docker-compose.yml to `oidc` and set the following:
    * `OIDC_AUTH_URL` should be set to your providers well-known endpoint.  For example, Authelia is `https://[YourAuthDomain]/.well-known/openid-configuration`.
    * `OIDC_CLIENT_ID` is the `id` in your Authelia configuration.yaml.  In this case, it would be `headscale-webui`.
    * `OIDC_CLIENT_SECRET` is your client secret, in this case `[SECRET]`.  You can generate a secret using `openssl rand -hex 64`.

### KeyCloak
1.  In your Keycloak settings, add the following:
    *  The keycloak endpoint can be found on the realm settings page as the "OpenID Endpoint Configuration" link.
```
Client ID = headscale-webui
Callback URI = https://[DOMAIN]/[SCRIPT_NAME]/oidc_callback
Client Authentication (Previously called confidential access or similar) = True
Client Secret = [SECRET]
```
2.  Set `AUTH_TYPE` environment variable in your docker-compose.yml to `oidc` and set the following:
    * `OIDC_AUTH_URL` should be set to your providers well-known endpoint.  For example, Keycloak is `https://[DOMAIN]/realms/[REALM]/.well-known/openid-configuration`.
    * `OIDC_CLIENT_ID` is the `id` in your Authelia configuration.yaml.  In this case, it would be `headscale-webui`.
    * `OIDC_CLIENT_SECRET` is your client secret, in this case `[SECRET]`.  You can generate a secret using `openssl rand -hex 64`.

---
