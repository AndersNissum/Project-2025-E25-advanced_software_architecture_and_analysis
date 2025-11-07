from flask import Flask, jsonify
from sqlalchemy import create_engine, text
import logging
import time
from faker import Faker
import random

# Logger setup
logging.basicConfig(level=logging.INFO)
LOGGER = logging.getLogger(__name__)

# Create database engine
def get_db_engine():
    return create_engine('postgresql://user:password@db:5432/mydatabase')

# Initialize Faker
fake = Faker('en_US')

# Define your update query using parameterized input
update_query = text("UPDATE pasta_db.storage_levels SET level = :level, wet_type = :wet_type WHERE id = :id")

# Retry mechanism for connecting to the database
while True:
    try:
        db_engine = get_db_engine()  # Create the engine
        LOGGER.info("Connected successfully")
        break
    except Exception as e:
        LOGGER.warning(f"++++ Retrying connection to the database because of the issue {str(e)}++++")
        time.sleep(5)  # Wait before retrying

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
                
                # Fetch and log the current state of the table
                select_query = text("SELECT * FROM pasta_db.storage_levels")
                result = connection.execute(select_query)
                rows = result.fetchall()  # This retrieves all rows from the result
                for row in rows:
                    LOGGER.info(row)  # Log each row
        
    except Exception as e:
        LOGGER.error(f"Error updating storage_levels with id {storage_level_id}: {str(e)}")

    time.sleep(20)
    

db_engine.close()
#app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL', 'postgresql://user:password@db:5432/mydatabase')
#app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
# Initialize the database
#db = SQLAlchemy(app)


@app.route('/start_production')
def start_production():
    """Simulate normal production."""
    uptime = random.choice([True, False])
    if not uptime:
        return jsonify({"status": "downtime", "message": "Downtime occurred"}), 500
    
    # Save production status to the database
    production_status = ProductionStatus(status='running', message='Production running smoothly')
    db.session.add(production_status)
    db.session.commit()
    
    return jsonify({"status": "running", "message": "Production running smoothly"}), 200

@app.route('/stop_production', methods=['POST'])
def stop_production():
    """Stop production."""
    production_status = ProductionStatus(status='stopped', message='Production has been stopped.')
    db.session.add(production_status)
    db.session.commit()
    
    return jsonify({"status": "stopped", "message": "Production has been stopped."}), 200

@app.route('/simulate_failure')
def simulate_failure():
    """Simulate a failure scenario."""
    time.sleep(5)  # Simulate a delay
    production_status = ProductionStatus(status='failure', message='Failure simulated')
    db.session.add(production_status)
    db.session.commit()
    
    return jsonify({"status": "failure", "message": "Failure simulated"}), 500

@app.route('/heartbeat')
def heartbeat():
    """Simulate a heartbeat."""
    return jsonify({"status": "alive", "message": "System is operational"}), 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8000)
    