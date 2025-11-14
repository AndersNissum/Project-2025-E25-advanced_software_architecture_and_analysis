from kafka import KafkaConsumer
import json
import logging
import time
import paho.mqtt.client as mqtt

# Logger setup
logging.basicConfig(level=logging.INFO)
LOGGER = logging.getLogger(__name__)


# MQTT PART

# MQTT Configuration
broker_address = "192.168.1.183"  
port = 1883  # Default MQTT port
 
# Create a new MQTT client instance
client = mqtt.Client()
# Connect to the MQTT broker
client.connect(broker_address, port)
        
client.loop_start()


LOGGER.info("Client connected to mqtt broker")

def publish_message(message):
    topic = "ProductionPlan" 
    try:
        # Convert the message to JSON format
        json_message = json.dumps(message)
        client.publish(topic, json_message)
        LOGGER.info(f"Message sent: {json_message}")
    except Exception as e:
        LOGGER.warning(f"Error sending message: {e}")

# Sample message to be sent to cutting machines
message_to_send = "Message for cutting machines"
#publish_message(message_to_send)

# Kafka Configuration
kafkatopic = 'ChangeMachineBlade'
bootstrap_servers = ['kafka:29092']  





# Create a Kafka consumer
consumer= None
while consumer is None:
    try:
        consumer = KafkaConsumer(
            kafkatopic,
            bootstrap_servers=bootstrap_servers,
            auto_offset_reset='earliest',  # Start reading at the earliest message
            group_id='test-group',
            value_deserializer=lambda x: x.decode('utf-8')  # For plain string messages
            )
    except Exception as e:
        print(f"Connection failed: {e}. Retrying...")
        time.sleep(5)


LOGGER.info(f"Listening for messages on topic: {kafkatopic}")

# Consume messages
while True:
    try:
        for message in consumer:
            # Print the raw message to diagnose the issue
            #print(f"Raw message: key={message.key}, value={message.value}")
            
            
            if message.value is not None and len(message.value) > 0:
                LOGGER.info(f"Consumed: key={message.key}, value={message.value}")
                publish_message(message_to_send)
                
            else:
                print("Received an empty or None message.")
    except KeyboardInterrupt:
        print("Consumer stopped.")
    finally:
        consumer.close()
    time.sleep(5)


