#!/bin/bash

# Get the directory where the script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Create the 'logs' directory in the project root if it doesn't exist
mkdir -p "$SCRIPT_DIR/../logs"  # Ensures the 'logs' directory exists for storing log files

# Generate a timestamp for the log file name in the format YYYY-MM-DD_HH-MM-SS
TIMESTAMP=$(date +"%Y-%m-%d_%H-%M-%S")  # Generates a timestamp to uniquely name the log file

# Define the log file path using the generated timestamp
LOG_FILE="$SCRIPT_DIR/../logs/$TIMESTAMP.log"  # Sets the log file path in the 'logs' directory

# Generate self-signed certificates for localhost
mkcert -cert-file "$SCRIPT_DIR/../localhost.pem" -key-file "$SCRIPT_DIR/../localhost-key.pem" localhost

# Start Envoy with the configuration in ./config/envoy.yaml and redirect logs to the log file
envoy -c "$SCRIPT_DIR/../config/envoy.yaml" --log-level info >> "$LOG_FILE" 2>&1 &  # Starts Envoy and redirects both stdout and stderr to the log file

# Start Python Services in the background and redirect logs to the same log file
python3 "$SCRIPT_DIR/../python_services/terrain_generation/terrain_generation_service.py" >> "$LOG_FILE" 2>&1 &  # Starts Terrain Generation Service and appends logs to the log file
python3 "$SCRIPT_DIR/../python_services/persistence/persistence_service.py" >> "$LOG_FILE" 2>&1 &  # Starts Persistence Service and appends logs to the log file

# Navigate to the React app directory and start the React app without redirecting logs
cd "$SCRIPT_DIR/../javascript_services/vie_ui/" || { echo "Failed to navigate to vie_ui directory"; exit 1; }
npm start &  # Starts the React app in the background and logs are emitted to stdout

echo "Envoy, Python services, and React app 'vie_ui' started."  # Confirms that all services have been started