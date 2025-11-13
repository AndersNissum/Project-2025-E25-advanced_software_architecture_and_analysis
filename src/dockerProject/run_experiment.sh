#!/bin/bash

set -e  # Exit immediately if any command fails

# Stop and remove containers, networks, and volumes
echo "Stopping and removing containers, networks, and volumes..."
docker-compose down -v

# Build the images
echo "Building Docker images..."
if ! docker-compose build; then
    echo "ERROR: Docker build failed!"
    exit 1
fi

# Start containers in detached mode
echo "Starting containers in detached mode..."
docker-compose up -d

echo "Experiment setup complete!"