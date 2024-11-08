#!/bin/bash

# Start the Terrain Generation Service if it's lock file is not present
if [ -f "/tmp/terrain_generation_service.lock" ]; then
    echo "Terrain Generation Service is already running."
    exit 1
fi
echo "Starting Terrain Generation Service..."
python3 python_services/terrain_generation/terrain_generation_service.py &
TERRAIN_GEN_PID=$!

# Start the Persistence Service if it's lock file is not present
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

# Wait for the services to exit
wait $TERRAIN_GEN_PID
wait $PERSISTENCE_PID

echo "All services started."
