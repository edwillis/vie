#!/bin/bash

# Start the Terrain Generation Service if its lock file is not present
if [ -f "/tmp/terrain_generation_service.lock" ]; then
    echo "Terrain Generation Service is already running."
    exit 1
fi
echo "Starting Terrain Generation Service..."
python3 python_services/terrain_generation/terrain_generation_service.py &
TERRAIN_GEN_PID=$!

# Start the Persistence Service if its lock file is not present
if [ -f "/tmp/persistence_service.lock" ]; then
    echo "Persistence Service is already running."
    exit 1
fi
echo "Starting Persistence Service..."
python3 python_services/persistence/persistence_service.py &
PERSISTENCE_PID=$!

# Save the PIDs to a file for later termination
echo $TERRAIN_GEN_PID > service_pids.txt
echo $PERSISTENCE_PID >> service_pids.txt

# Start Envoy proxy
echo "Starting Envoy..."
docker run -d --network host --name envoy -v $(pwd)/config/envoy.yaml:/etc/envoy/envoy.yaml -p 8080:8080 envoyproxy/envoy:v1.18.3 -c /etc/envoy/envoy.yaml

# Wait for the services to exit
wait $TERRAIN_GEN_PID
wait $PERSISTENCE_PID

echo "All services started."