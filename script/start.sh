#!/bin/bash

# Get the directory where the script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Start Nginx with the configuration in ./config/nginx.conf
#nohup nginx -c "$SCRIPT_DIR/../config/nginx.conf" -p "$SCRIPT_DIR/../" > "$SCRIPT_DIR/../nginx.log" 2>&1 &

# Start Envoy with the configuration in ./config/envoy.yaml without root privileges
nohup envoy -c "$SCRIPT_DIR/../config/envoy.yaml" --log-level info > "$SCRIPT_DIR/../envoy.log" 2>&1 &

# Start Python Services in the background
nohup python3 "$SCRIPT_DIR/../python_services/terrain_generation/terrain_generation_service.py" > "$SCRIPT_DIR/../terrain_gen_service.log" 2>&1 &
nohup python3 "$SCRIPT_DIR/../python_services/persistence_service.py" > "$SCRIPT_DIR/../persistence_service.log" 2>&1 &

# Navigate to the React app directory and start the React app
cd "$SCRIPT_DIR/../javascript_services/vie_ui/" || { echo "Failed to navigate to vie_ui directory"; exit 1; }
nohup npm start > "$SCRIPT_DIR/../javascript_services/vie_ui/vie_ui.log" 2>&1 &

echo "Nginx, Python services, and React app 'vie_ui' started."