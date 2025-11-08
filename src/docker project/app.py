from sqlalchemy import create_engine, text
import logging
import time
from faker import Faker
import random
import threading



# Logger setup
logging.basicConfig(level=logging.INFO)
LOGGER = logging.getLogger(__name__)

# Connect to database through url
def get_db_engine():
    return create_engine('postgresql://user:password@db:5432/mydatabase')

# Initialize Faker
fake = Faker('en_US')



# Retry logic for connecting to the database
while True:
    try:
        db_engine = get_db_engine()  # Create the engine
        LOGGER.info("Connected successfully")
        break
    except Exception as e:
        LOGGER.warning(f"Retrying connection to the database because of the issue {str(e)}")
        time.sleep(5)  # Wait before retrying

def update_storage_levels():
    # Update query with parameters
    update_query = text("UPDATE pasta_db.storage_levels SET level = :level, wet_type = :wet_type WHERE id = :id")
    i = 0  # Initialize `i` for ID calculation
    while True:
        new_level = random.randint(0, 100)  # Random integer between 0 and 100
        new_wet_type = random.choice(['fresh', 'dry'])  # Randomly choose between 'fresh' and 'dry'
        
        # Incrementing the ID for each iteration
        storage_level_id = fake.random_int(min=1, max=4)

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

                    # Select query to fetch all rows for logging
                    select_query = text("SELECT * FROM pasta_db.storage_levels")
                    result = connection.execute(select_query)
                    rows = result.fetchall()  # This retrieves all rows from the result
                    
                    # Check for values > 80 or < 20 and log them
                    for row in rows:
                        LOGGER.info(f"Level Alert: {row}")  # Log if level is outside the defined range

        except Exception as e:
            LOGGER.error(f"Error updating storage_levels with id {storage_level_id}: {str(e)}")

        time.sleep(20)  # Pause for 20 seconds before the next iteration


def insertBatches():
    # Insert query with parameters for the batches table
    insert_query = text("""
        INSERT INTO pasta_db.batches (id, inStock, isFresh, productionDate, blade_type) 
        VALUES (:id, :inStock, :isFresh, NOW(), :blade_type)
    """)
    
    i = 1  # Initialize `i` for ID calculation, starting from 1
    while True:
        new_inStock = random.randint(10, 100)  # Random integer for inStock between 10 and 100
        new_isFresh = random.choice([True, False])  # Randomly choose between True (fresh) and False (dry)
        new_blade_type = random.choice(['A', 'B'])  # Randomly choose between blade types A and B
        
        # Assign the current ID
        batch_id = i
        i += 1  # Increment for the next batch ID

        try:
            # Use a context manager for transaction handling and execute the query
            with db_engine.connect() as connection:  # Get a connection
                # Begin a transaction
                with connection.begin():  # This begins a new transaction
                    # Execute the insert query with parameters
                    connection.execute(insert_query, {
                        'id': batch_id,
                        'inStock': new_inStock,
                        'isFresh': new_isFresh,
                        'blade_type': new_blade_type
                    })
                    LOGGER.info(f"Inserted batch with id {batch_id}: inStock={new_inStock}, isFresh={new_isFresh}, blade_type={new_blade_type}")
                    # Select query to fetch all rows for logging
                    select_query = text("SELECT id, inStock FROM pasta_db.batches WHERE inStock > 0")
                    result = connection.execute(select_query)
                    batches = result.fetchall()  # This retrieves all rows from the result
                    
                    for batch_id, in_stock in batches:
                        # Generate a random integer to decrease inStock
                        random_int = random.randint(1, in_stock)
                        new_stock = max(in_stock - random_int, 0)
                        connection.execute("""
                            UPDATE batches
                            SET inStock = ?
                            WHERE id = ?
                        """, (new_stock, batch_id))
        except Exception as e:
            LOGGER.error(f"Error inserting batch with id {batch_id}: {str(e)}")

        time.sleep(5)  # Pause for 20 seconds before the next iteration





# Create threads for each task
updateStorageLevels_thread = threading.Thread(target=update_storage_levels)
insertBatches_thread = threading.Thread(target=insertBatches)

# Start the threads
updateStorageLevels_thread.start()
insertBatches_thread.start()

# Optionally, you can join the threads if you want the main program to wait for them
#update_thread.join()
#another_thread.join()


"""
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

    


    