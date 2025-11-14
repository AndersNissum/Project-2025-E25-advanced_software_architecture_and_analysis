#!/bin/sh

CONFIG_FILE="/mosquitto/config/mosquitto.conf"

# Create config file if missing
if [ ! -f "$CONFIG_FILE" ]; then
    echo "mosquitto.conf not found, creating default config..."
    cat <<EOF > "$CONFIG_FILE"
listener 1883
allow_anonymous true
EOF
fi

echo "Starting Mosquitto..."
exec /usr/sbin/mosquitto -c "$CONFIG_FILE"
