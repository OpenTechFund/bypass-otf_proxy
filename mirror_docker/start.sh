# define the default config file.
CONF_FILE="/etc/nginx/conf.d/default.conf"

# Extract the domain
WGET_DOMAIN="$(echo $WGET_URL | sed -e 's/[^/]*\/\/\([^@]*@\)\?\([^:/]*\).*/\2/')"

# Substitute domain in configuration file
/bin/sed -i "s,<wget_domain>,${WGET_DOMAIN}," ${CONF_FILE}

nginx -g "daemon off;"