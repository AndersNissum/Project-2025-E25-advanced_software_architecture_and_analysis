from kafka import KafkaConsumer
import json
import logging
import time


# Logger setup
logging.basicConfig(level=logging.INFO)
LOGGER = logging.getLogger(__name__)
# Configuration
topic = 'ChangeMachineBlade'
bootstrap_servers = ['kafka:29092']  # Change to your Kafka server address

# Create a Kafka consumer
consumer= None
while consumer is None:
    try:
        consumer = KafkaConsumer(
            topic,
            bootstrap_servers=bootstrap_servers,
            auto_offset_reset='earliest',  # Start reading at the earliest message
            group_id='test-group',
            value_deserializer=lambda x: x.decode('utf-8')  # For plain string messages,  # Assuming messages are in JSON format
            )
    except Exception as e:
        print(f"Connection failed: {e}. Retrying...")
        time.sleep(5)


print(f"Listening for messages on topic: {topic}")

# Consume messages
while True:
    try:
        for message in consumer:
            # Print the raw message to diagnose the issue
            #print(f"Raw message: key={message.key}, value={message.value}")
            
            # Check if value is None or empty before deserializing
            if message.value is not None and len(message.value) > 0:
                LOGGER.info(f"Consumed: key={message.key}, value={message.value}")
            else:
                print("Received an empty or None message.")
    except KeyboardInterrupt:
        print("Consumer stopped.")
    finally:
        consumer.close()
    time.sleep(5)
