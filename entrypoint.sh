#!/bin/sh
. /app/.venv/bin/activate
chown -R 1000:1000 /data
exec "$@"