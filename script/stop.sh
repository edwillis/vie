#!/bin/bash

# Check for lock files under /tmp
lock_files=$(ls /tmp | grep -E '.lock*')
if [ -n "$lock_files" ]; then
  echo "Lock files found: $lock_files"
  
  # Look for any python3 processes running scripts from the python_services directory and terminate them
  pids=$(pgrep -f "python3 .*python_services")
  if [ -n "$pids" ]; then
    echo "Terminating python3 processes running scripts from python_services..."
    echo "$pids" | xargs kill
  fi
  # delete the lock files
  echo "Deleting lock files..."
  rm /tmp/*.lock
fi

# Check if the PID file exists
if [ ! -f service_pids.txt ]; then
  echo "No services are currently running."
  exit 1
fi

# Read the PIDs from the file and terminate the processes
while read -r PID; do
  echo "Terminating process with PID $PID..."
  kill $PID
done < service_pids.txt

# Remove the PID file
rm service_pids.txt

echo "All services terminated."
