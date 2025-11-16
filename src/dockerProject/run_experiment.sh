#!/bin/bash

set -e

echo "Stopping and removing containers, networks, and volumes..."
docker-compose down -v

echo "Building Docker images..."
if ! docker-compose build; then
    echo "ERROR: Docker build failed!"
    exit 1
fi

echo "Starting containers in detached mode..."
docker-compose up -d

echo "Experiment setup complete!"