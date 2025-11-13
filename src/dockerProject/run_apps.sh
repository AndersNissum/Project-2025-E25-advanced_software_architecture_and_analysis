#!/bin/bash

# Run both applications in the background
python dbatch.py &
python sensor_mqtt.py &

# Wait for both applications to finish
wait