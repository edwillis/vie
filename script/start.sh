#!/bin/bash
set -e  # Exit immediately if a command exits with a non-zero status

# Get the directory where the script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Create the 'logs' directory in the project root if it doesn't exist
mkdir -p "$SCRIPT_DIR/../logs"

# Generate a timestamp for the log file name
TIMESTAMP=$(date +"%Y-%m-%d_%H-%M-%S")

# Define the log file path using the generated timestamp
LOG_FILE="$SCRIPT_DIR/../logs/$TIMESTAMP.log"

# Create the certs directory if it doesn't exist
mkdir -p certs

# Generate SSL certificates if they don't exist
if [ ! -f certs/localhost.pem ]; then
    echo "Generating SSL certificates..."
    mkcert -install
    mkcert -cert-file certs/localhost.pem -key-file certs/localhost-key.pem localhost 127.0.0.1 ::1
fi

# Check if we have terrain_generation_service.py
if [ ! -f python_services/terrain_generation/terrain_generation_service.py ]; then
    echo "Error: terrain_generation_service.py not found!"
    exit 1
fi

# Start the Python services with log redirection
cd python_services || { echo "Failed to navigate to python_services directory"; exit 1; }
python -m persistence.persistence_service >> "$LOG_FILE" 2>&1 &
echo $! > ../service_pids.txt
python -m terrain_generation.terrain_generation_service >> "$LOG_FILE" 2>&1 &
echo $! >> ../service_pids.txt
cd ..

# Start Envoy with log redirection
envoy -c config/envoy.yaml --log-level info >> "$LOG_FILE" 2>&1 &
echo $! >> service_pids.txt

# Start the JavaScript UI service
cd javascript_services/vie_ui || { echo "Failed to navigate to vie_ui directory"; exit 1; }
HTTPS=true PORT=3001 SSL_CRT_FILE=../../certs/localhost.pem SSL_KEY_FILE=../../certs/localhost-key.pem npm start &
echo $! >> ../../service_pids.txt

echo "Waiting for app to fully initialize..."
sleep 10

echo "All services started. Logs being written to $LOG_FILE"
echo "Press Ctrl+C to stop."

echo "Envoy, Python services, and React app 'vie_ui' started."
echo "Visit https://localhost:3001 to view the application."
echo "To stop the services, run: ./script/stop.sh"

# Let the script keep running indefinitely
wait
