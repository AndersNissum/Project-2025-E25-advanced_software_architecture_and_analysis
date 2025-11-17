from sqlalchemy import create_engine, text
import logging
import time
from faker import Faker
import random
import threading
from kafka import KafkaAdminClient
from kafka.admin import NewTopic
from kafka import KafkaProducer
from confluent_kafka import Producer
import json
import os



# Logger setup
logging.basicConfig(level=logging.INFO)
LOGGER = logging.getLogger(__name__)

# Connect to database through url
def get_db_engine():
    return create_engine('postgresql://user:password@db:5432/mydatabase')

# Initialize Faker
fake = Faker('en_US')

# Initialize the admin client
"""
admin_client = KafkaAdminClient(
    bootstrap_servers='localhost:9092',  # Use the OUTSIDE listener
    client_id='kafka'
)

# Define the new topic
new_topic = NewTopic(
    name='ProductionPlan',
    num_partitions=1,
    replication_factor=1
)
# Create the topic
while True:
    try:
        admin_client.create_topics(new_topics=[new_topic], validate_only=False)
        print("Topic created successfully.")
        break
    except Exception as e:
        print(f"Failed to create topic: {e}")
"""
# Get the Kafka bootstrap server from environment variable

# Initialize Kafka producer with retry logic
producer = None
while producer is None:
    try:
        producer = Producer({'bootstrap.servers': 'kafka:29092'})
    except Exception as e:
        print(f"Connection failed: {e}. Retrying...")
        time.sleep(5)



# Retry logic for connecting to the database
while True:
    try:
        db_engine = get_db_engine()  # Create the engine
        LOGGER.info("Connected successfully")
        break
    except Exception as e:
        LOGGER.warning(f"Retrying connection to the database because of the issue {str(e)}")
        time.sleep(5)  # Wait before retrying


    
    
    


def insertBatch():
    # Insert query with parameters for the batches table
    insert_query = text("""
    INSERT INTO pasta_db.batches (id, blade_type, isFresh, productionDate,inStock ) 
    VALUES (:id, :blade_type, :isFresh, NOW(), :inStock)
    """)

    i = 11  # Initialize `i` for ID calculation, starting from 1
    while True:
        new_inStock = 10  
        new_isFresh = random.choice([True, False])  # Randomly choose between True (fresh) and False (dry)
        new_blade_type = random.choice(['A', 'B'])  # Randomly choose between blade types A and B

        # Assign the current ID
        i += 1  # Increment for the next batch ID
        batch_id = i
        
        try:
            # Use a context manager for transaction handling and execute the query
            with db_engine.connect() as connection:  # Get a connection
                # Begin a transaction
                with connection.begin():  # This begins a new transaction
                    # Execute the insert query with parameters
                    connection.execute(insert_query, {
                        'id': batch_id,
                        'isFresh': new_isFresh,
                        'blade_type': new_blade_type,
                        'inStock': new_inStock
                    })
                    LOGGER.info(f"Inserted batch with id {batch_id}: inStock={new_inStock}, isFresh={new_isFresh}, blade_type={new_blade_type}")
                    # Select query to fetch all rows for logging
                    select_query = text("SELECT * FROM pasta_db.storage_levels")
                    select_query_result = connection.execute(select_query)
                    storage_levels = select_query_result.fetchall()
                    countOfStorageLevelsBelowOrAbove= 0
                    for storage_level in storage_levels:
                        #LOGGER.info(storage_level)
                        if storage_level[3]<20 or storage_level[3]>80:
                            countOfStorageLevelsBelowOrAbove+=1
                            # add scheduler logic to change production plan
                            message = f"Change Production Plan for {storage_level[2]} - {storage_level[1]}"

                            # Send message to Kafka topic
                            producer.produce('ProductionPlan', key='Production', value=message)
                            producer.flush(30)
                            #producer.send('ProductionPlan', value=message)
                            #producer.flush()  # Ensure message is sent
                        if storage_level[3]<5:
                            new_inStock = 10  
                            new_isFresh = random.choice([True, False])  # Randomly choose between True (fresh) and False (dry)
                            new_blade_type = random.choice(['A', 'B'])  # Randomly choose between blade types A and B

                            # Assign the current ID
                            i += 1  # Increment for the next batch ID
                            batch_id = i
                            
                            # Execute the insert query with parameters
                            connection.execute(insert_query, {
                                'id': batch_id,
                                'isFresh': new_isFresh,
                                'blade_type': new_blade_type,
                                'inStock': new_inStock
                            })
                            LOGGER.info("Inserted new batch because a storage level is less than 5%")
                    if countOfStorageLevelsBelowOrAbove>0:
                        LOGGER.warning("Scheduler should change production plan")
                    
                    

        except Exception as e:
            LOGGER.error(f"Error {str(e)}")

        time.sleep(5)  # Pause for 40 seconds before the next iteration

def reduceBatches():
    while True:
        try:
             # Use a context manager for transaction handling and execute the query
            with db_engine.connect() as connection:  # Get a connection
                # Begin a transaction
                with connection.begin():  # This begins a new transaction
                    # Select query to fetch all rows for logging
                    select_query = text("SELECT * FROM pasta_db.batches WHERE inStock > 0")
                    result = connection.execute(select_query)
                    batches = result.fetchall()  # This retrieves all rows from the result
                    #MINIMUM_STOCK_THRESHOLD = 10  # Define a minimum stock level
                    reducedCount=20
                    for batch in batches:
                        batch_id = batch[0]  #  first column is the ID
                        in_stock = batch[4]  #  fifth column is inStock
                        # Generate a random integer to decrease inStock, ensuring it does not reduce below the minimum threshold
                    
                        random_int = fake.random_int(min=0, max=in_stock)  # Adjust max to avoid going below the threshold\
                        
                        amount = min(random_int,reducedCount)
                        reducedCount -= amount
                    
                    
                        random_int = 0  # If in_stock is already low, do not reduce further
                        new_stock = max(in_stock - amount, 0)
                        # Update the inStock value for the batch
                        connection.execute(text("""
                            UPDATE pasta_db.batches
                            SET inStock = :new_stock
                            WHERE id = :batch_id
                        """), {
                            'new_stock': new_stock,
                            'batch_id': batch_id
                        })
                        #LOGGER.info("Reduced batches")
        except Exception as e:
            LOGGER.error(f"Error {str(e)}")
        time.sleep(10)  # Pause for 20 seconds before the next iteration

def check_UpdateStorageLevels():
    while True:
        try:
             # Use a context manager for transaction handling and execute the query
            with db_engine.connect() as connection:  
                # Begin a transaction
                with connection.begin():  
                    storage_level_categories = [
                        ('A', 'fresh'),
                        ('B', 'fresh'),
                        ('A', 'dry'),
                        ('B', 'dry')
                    ]
                    max_storage=100
                    for type, wet_type in storage_level_categories:
                        # Query to sum all inStock for the current storage_level
                        result = connection.execute(text("""
                            SELECT SUM(inStock) AS total
                            FROM pasta_db.batches
                            WHERE blade_type = :blade_type AND isFresh = :is_fresh
                        """), {
                            'blade_type': type,
                            'is_fresh': (wet_type == 'fresh')
                        })
                        
                        total_stock = result.scalar() or 0  # Get the total or 0 if None
                        #LOGGER.info(f"Total stock is {total_stock}")
                        # Calculate storage level percentage
                        new_storage_level = (total_stock / max_storage) * 100
                        
                        # Update the storage level in your storage_levels table
                        connection.execute(text("""
                            UPDATE pasta_db.storage_levels
                            SET level = :storage_level
                            WHERE type = :type AND wet_type = :wet_type
                        """), {
                            'storage_level': new_storage_level,
                            'type': type,
                            'wet_type': wet_type
                        })

                        LOGGER.info(f"Updated storage level for type {type} and wet type {wet_type}: {new_storage_level:.2f}%")
                    
        except Exception as e:
            LOGGER.error(f"Error {str(e)}")
        time.sleep(10)

# Create threads for each task
check_UpdateStorageLevels_thread = threading.Thread(target=check_UpdateStorageLevels)
insertBatch_thread = threading.Thread(target=insertBatch)
reduceBatches_thread = threading.Thread(target=reduceBatches)

# Start the threads
insertBatch_thread.start()
reduceBatches_thread.start()
check_UpdateStorageLevels_thread.start()


"""
MINIMUM_STOCK_THRESHOLD = 10  # Define a minimum stock level
                for batch in batches:
                    batch_id = batch[0]  #  first column is the ID
                    in_stock = batch[4]  #  fifth column is inStock
                    
                    # Generate a random integer to decrease inStock, ensuring it does not reduce below the minimum threshold
                    if in_stock >= MINIMUM_STOCK_THRESHOLD:
                        random_int = fake.random_int(min=0, max=in_stock)  # Adjust max to avoid going below the threshold
                    else:
                        random_int = 0  # If in_stock is already low, do not reduce further
---------------------------------------------------------------------------------------------------------------------------
for batch in batches:
                        batch_id = batch[0]  #  first column is the ID
                        in_stock = batch[4]  #  fifth column is inStock
                        random_int = fake.random_int(min=0, max=in_stock)  # Adjust max to avoid going below the threshold
---------------------------------------------------------------------------------------------------------------------------
#select_query = text("SELECT * FROM pasta_db.storage_levels")
                    #select_query_result = connection.execute(select_query)
                    #storage_levels = select_query_result.fetchall()
                    #for storage_level in storage_levels:
                        #LOGGER.info(storage_level)
                        #if storage_level[3]>80 or storage_level[3]<20:
                            #LOGGER.info("Change production plan")

---------------------------------------------------------------------------------------------------------------------------                                                    
select_query = text("SELECT * FROM pasta_db.batches WHERE inStock > 0")
                    result = connection.execute(select_query)
                    batches = result.fetchall()  # This retrieves all rows from the result
                    
                    for batch in batches:
                        batch_id = batch[0]  #  first column is the ID
                        in_stock = batch[4]  #  fifth column is inStock
                        
                        # Generate a random integer to decrease inStock, ensuring it does not reduce below the minimum threshold
                        if in_stock <= 5:
                            new_inStock = 10  
                            new_isFresh = random.choice([True, False])  # Randomly choose between True (fresh) and False (dry)
                            new_blade_type = random.choice(['A', 'B'])  # Randomly choose between blade types A and B

                            # Assign the current ID
                            i += 1  # Increment for the next batch ID
                            batch_id = i
                            
                            # Execute the insert query with parameters
                            connection.execute(insert_query, {
                                'id': batch_id,
                                'isFresh': new_isFresh,
                                'blade_type': new_blade_type,
                                'inStock': new_inStock
                            })
                            
---------------------------------------------------------------------------------------------------------------------------    
i = 0
while True:
    new_level = fake.random_int(min=0, max=100)
    new_wet_type = random.choice(['fresh', 'dry'])  # Randomly choose between 'fresh' and 'dry'
    
    # Incrementing the ID for each iteration
    storage_level_id = i + fake.random_int(min=1, max=3)

    try:
        # Use a context manager for transaction handling and execute the query
        with db_engine.connect() as connection:  # Get a connection
            # Begin a transaction
            with connection.begin():  # This begins a new transaction
                # Execute the update query with parameters
                connection.execute(update_query, {
                    'level': new_level,
                    'wet_type': new_wet_type,
                    'id': storage_level_id
                })
                LOGGER.info(f"Updated storage_levels with id {storage_level_id}: level={new_level}, wet_type={new_wet_type}")
                
                
                select_query = text("SELECT * FROM pasta_db.storage_levels")
                # here i check for values >80 <20

                result = connection.execute(select_query)
                rows = result.fetchall()  # This retrieves all rows from the result
                for row in rows:
                    LOGGER.info(row)  # Log each row
        
    except Exception as e:
        LOGGER.error(f"Error updating storage_levels with id {storage_level_id}: {str(e)}")

    time.sleep(20)
"""

    

"""
    def updateStorageLevels(max_storage=100):
    # Define the categories based on your table structure
    storage_level_categories = [
        ('A', 'fresh'),
        ('B', 'fresh'),
        ('A', 'dry'),
        ('B', 'dry')
    ]
    while True:
        try:
            with db_engine.connect() as connection:
                for type, wet_type in storage_level_categories:
                    # Query to sum all inStock for the current storage_level
                    result = connection.execute(text(""
                        SELECT SUM(inStock) AS total
                        FROM pasta_db.batches
                        WHERE blade_type = :blade_type AND isFresh = :is_fresh
                    ""), {
                        'blade_type': type,
                        'is_fresh': (wet_type == 'fresh')
                    })
                    
                    total_stock = result.scalar() or 0  # Get the total or 0 if None
                    LOGGER.info(f"Total stock is {total_stock}")
                    # Calculate storage level percentage
                    new_storage_level = (total_stock / max_storage) * 100
                    
                    # Update the storage level in your storage_levels table
                    connection.execute(text(""
                        UPDATE pasta_db.storage_levels
                        SET level = :storage_level
                        WHERE type = :type AND wet_type = :wet_type
                    ""), {
                        'storage_level': new_storage_level,
                        'type': type,
                        'wet_type': wet_type
                    })

                    LOGGER.info(f"Updated storage level for type {type} and wet type {wet_type}: {new_storage_level:.2f}%")

                    
        except Exception as e:
            LOGGER.error(f"Error updating storage levels: {str(e)}")
        time.sleep(10)  # Pause for 20 seconds before the next iteration
    """

"""
Tools for availability measurement
prometheus:
    image: prom/prometheus
    volumes:
      - ./prometheus.yml:/etc/prometheus/prometheus.yml
    ports:
      - "9090:9090"
    networks:
      - mynetwork

  grafana:
    image: grafana/grafana
    ports:
      - "3000:3000"
    networks:
      - mynetwork
"""
"""
Prometheus.yml
global:
  scrape_interval: 15s

scrape_configs:
  - job_name: 'pasta-system'
    static_configs:
      - targets: ['pasta-system:8000']  # Adjust if your app exposes metrics here
"""
    