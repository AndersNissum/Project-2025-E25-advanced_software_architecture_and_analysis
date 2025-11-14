from kafka import KafkaConsumer
import json
import logging
import time
import paho.mqtt.client as mqtt

# Logger setup
logging.basicConfig(level=logging.INFO)
LOGGER = logging.getLogger(__name__)

# MQTT CONFIG
broker_address = "192.168.1.183"
port = 1883
topic = "ProductionPlan"

# Create ONE MQTT client
client = mqtt.Client()

# ------------------------------------
# PUBLISH FUNCTION
# ------------------------------------
def publish_message(message):
    try:
        json_message = json.dumps(message)
        client.publish(topic, json_message)
        LOGGER.info(f"Message sent: {json_message}")
    except Exception as e:
        LOGGER.warning(f"Error sending message: {e}")


message_to_send = "Machine blade switched"

# ------------------------------------
# CALLBACKS
# ------------------------------------

def on_connect(client, userdata, flags, rc):
    if rc == 0:
        LOGGER.info("Connected to MQTT broker")
        client.subscribe(topic)
        LOGGER.info(f"Subscribed to topic: {topic}")
    else:
        LOGGER.error(f"Connection failed. Return code {rc}")


def on_message(client, userdata, msg):
    payload = msg.payload.decode()
    LOGGER.info(f"Received message from {msg.topic}: {payload}")

    # Example response publish
    publish_message(message_to_send)

    try:
        json_data = json.loads(payload)
        LOGGER.info(f"Decoded JSON: {json_data}")
    except json.JSONDecodeError:
        LOGGER.warning("Message is not valid JSON")


# Assign callbacks BEFORE connecting
client.on_connect = on_connect
client.on_message = on_message

# Connect to broker
client.connect(broker_address, port)

# Blocking loop — keeps listening
client.loop_forever()