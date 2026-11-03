#!/bin/sh
# Create the broker's password file from course.env, then start Mosquitto.
set -eu

: "${MQTT_USERNAME:?MQTT_USERNAME is not set (see course.env)}"
: "${MQTT_PASSWORD:?MQTT_PASSWORD is not set (see course.env)}"

conf="$(dirname "$0")/mosquitto.conf"
# Read the path from the config so it is written down in one place only.
passwd_file="$(sed -n 's/^plugin_opt_password_file[[:space:]]*//p' "$conf")"

# Start from an empty file on every start (restarts included), so the file
# always matches course.env. -c refuses to overwrite an existing file.
rm -f "$passwd_file"
# -c creates the file, -b takes the password from the command line.
mosquitto_passwd -c -b "$passwd_file" "$MQTT_USERNAME" "$MQTT_PASSWORD"
# Mosquitto runs as the "mosquitto" user and refuses password files that
# other users can read.
chown mosquitto:mosquitto "$passwd_file"
chmod 0600 "$passwd_file"

exec mosquitto -c "$conf"
