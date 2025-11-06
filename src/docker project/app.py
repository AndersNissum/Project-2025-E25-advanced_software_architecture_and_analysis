from flask import Flask, jsonify

import random
import time
from sqlalchemy import create_engine
from sqlalchemy import text
from faker import Faker
import logging
# Configure database
import os
#app = Flask(__name__)

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
LOGGER = logging.getLogger(__name__)

#create_engine => username, password, hostname:port, database
def get_db_engine():
    return create_engine('postgresql://{}:{}@{}:{}/{}'.format('user', 'password', 'db', '5432', 'mydatabase'))

while True:
    try:
        db_engine = get_db_engine().connect()
        if db_engine:
            update_query = f"UPDATE pasta_db.storage_levels SET level = {52}, wet_type = 'dry' WHERE id = {2}"
            db_engine.execute(text(update_query).execution_options(autocommit=True))
            print("se gamao poutanoskilo")
            break
    except Exception as e:
        LOGGER.warning(f"++++ Retrying connection to the database because of the issue {str(e)}++++")

#retry mechanism for connect to database
fake = Faker('en_US')
i = 0


while True:
    new_level = fake.random_int(min=0, max=100)
    new_wet_type = random.choice(['fresh', 'dry'])  # Randomly choose between 'fresh' and 'dry'
    storage_level_id = i+1

    update_query = f"UPDATE pasta_db.storage_levels SET level = {new_level}, wet_type = '{new_wet_type}' WHERE id = {storage_level_id}"
    db_engine.execute(text(update_query).execution_options(autocommit=True))
    time.sleep(20)





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
    