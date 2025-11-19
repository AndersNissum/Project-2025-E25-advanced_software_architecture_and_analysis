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

# Wait for system to stabilize
echo "Waiting 30 seconds for system to stabilize..."
sleep 30

# Run ChaosPanda with custom parameters
echo "Starting ChaosPanda chaos testing..."
docker run -d \
    --name chaospanda-experiment \
    --network dockerproject_mynetwork \
    -v /var/run/docker.sock:/var/run/docker.sock \
    -e PYTHONUNBUFFERED=1 \
    chaospanda-image:latest \
    python main.py \
    --max-cutting-machines 2 \
    --max-schedulers 1 \
    --kafka-bootstrap kafka:29092 \
    --redis-host redis \
    --redis-port 6379 \
    --test-name "resilience-test-001"

echo "Experiment running! Monitor with:"
echo "  docker logs chaospanda-experiment -f"
echo "  docker logs kafkamonitor -f"
echo ""
echo "Stop with: docker stop chaospanda-experiment"