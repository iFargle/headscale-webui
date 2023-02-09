# headscale-webui
#### This is just a simple front-end for a Headscale server.  
Allows you to do the following:
1.  Enable/Disable routes and exit nodes
2.  Add, move, rename, and remove machines
3.  Add and remove users/namespaces
4.  Add and expire PreAuth keys
5.  Add and remove machine tags
6.  View machine details
    * Hostname
    * User associated with the machine
    * IP addresses in the Tailnet
    * Last seen by the control server
    * Last update with the control server
    * Creation date
    * PreAuth key associated with the machine
    * Enable / disable routes and exit nodes
    * Add and delete machine tags

# Screenshots:
![Machines](screenshots/machines.png)
![Users](screenshots/users.png)
![Add a new machine](screenshots/add-machine.png)
![Machine Details](screenshots/machines.png)
![API Key Test](screenshots/settings.png)


# Installation:
1.  This assumes you have traefik as your reverse proxy.  I'm sure it will work with others, but I don't have experience with any.
2.  Change the following variables in docker-compose.yml:
    1.  TZ - Change to your timezone.  Example: Asia/Tokyo
    2.  HS_SERVER - Change to your headscale's URL
    3.  BASE_PATH - This will be the path your server is served on.  Because the Windows Tailscale GUI expects <HS_SERVER/admin>, I usually put this as "/admin"
    4.  KEY - Your encryption key to store your headscale API key on disk.  Generate a new one with "openssl rand -base64 32".  Do not forget the quotations around the key when entering.
3. You will also need to change the volumes:
    1.  /data - Where your encryption key will reside.  Can be anywhere
    2.  /etc/headscale/ - This is your Headscale configuration file.
4.  Update the build context location to the directory with the Dockerfile.
    1.  Example:  If Dockerfile is in /home/username/headscale-webui, your context will be:
        *      context: /home/username/headscale-webui/

# Traefik
* This was built assuming the use of the Traefik reverse proxy.
* Exmaple config:
```
    labels:
      # Traefik Configs
      - "traefik.enable=true"
      - "traefik.http.routers.headscale-webui.entrypoints=web-secure"
      - "traefik.http.routers.headscale-webui.rule=Host(`headscale.$DOMAIN`) && (PathPrefix(`/admin/`) || PathPrefix(`/admin`))"
      - "traefik.http.services.headscale-webui.loadbalancer.server.port=5000"
      - "traefik.http.routers.headscale-webui.tls.certresolver=letsencrypt"
        # redirect /admin to /
      - "traefik.http.middlewares.headscale-webui-stripprefix.stripprefix.forceslash=true"
      - "traefik.http.middlewares.headscale-webui-stripprefix.stripprefix.prefixes=/admin/"
```
* Replace $DOMAIN with your domain and update /admin to your BASE_PATH, if changed.