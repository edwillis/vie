#!/bin/bash

# Stop Envoy
pkill -f envoy
#pkill nginx

# Stop JavaScript Services
cd javascript_services/vie_ui || { echo "Failed to navigate to vie_ui directory"; exit 1; }
npm stop

# Stop Python Services
pkill -f terrain_generation_service.py
pkill -f persistence_service.py
rm /tmp/*.lock

echo "gateway and Python services stopped."
