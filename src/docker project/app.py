from flask import Flask, jsonify
import random
import time

app = Flask(__name__)

@app.route('/start_production')
def start_production():
    """Simulate normal production."""
    uptime = random.choice([True, False])
    if not uptime:
        return jsonify({"status": "downtime", "message": "Downtime occurred"}), 500
    return jsonify({"status": "running", "message": "Production running smoothly"}), 200

@app.route('/stop_production', methods=['POST'])
def stop_production():
    # Logic to stop production
    return jsonify({"status": "stopped", "message": "Production has been stopped."}), 200

@app.route('/simulate_failure')
def simulate_failure():
    """Simulate a failure scenario."""
    time.sleep(5)  # Simulate a delay
    return jsonify({"status": "failure", "message": "Failure simulated"}), 500

@app.route('/heartbeat')
def heartbeat():
    """Simulate a heartbeat."""
    return jsonify({"status": "alive", "message": "System is operational"}), 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8000)