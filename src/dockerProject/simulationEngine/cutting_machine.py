import logging
import time
import json
import threading
from enum import Enum
from kafka import KafkaConsumer
from threading import Thread

# Logger setup
LOGGER = logging.getLogger(__name__)


class MachineState(Enum):
    """Machine operational states."""
    INITIALIZING = "initializing"
    WAITING_FOR_ASSIGNMENT = "waiting_for_assignment"
    WORKING = "working"


class CuttingMachine:
    """Simulates a cutting machine that sends heartbeat signals and responds to scheduler commands."""
    
    def __init__(self, machine_id, kafka_producer, kafka_bootstrap_servers):
        """
        Initialize a cutting machine.
        
        Args:
            machine_id (int): Unique identifier for this machine (0, 1, or 2)
            kafka_producer (KafkaProducerManager): Kafka producer instance
            kafka_bootstrap_servers (str): Kafka bootstrap servers
        """
        self.machine_id = machine_id
        self.kafka = kafka_producer
        self.kafka_bootstrap_servers = kafka_bootstrap_servers
        self.blade_type = None
        self.state = MachineState.INITIALIZING
        self.running = True
        self.lock = threading.Lock()
        
        LOGGER.info(f"Machine {self.machine_id} initialized in {self.state.value} state")
    
    def start(self):
        """Start the machine's operational threads."""
        # Send initial heartbeat
        self.send_heartbeat()
        
        # Update state to waiting for assignment
        with self.lock:
            self.state = MachineState.WAITING_FOR_ASSIGNMENT
        LOGGER.info(f"Machine {self.machine_id} waiting for blade assignment")
        
        # Start consumer thread to listen for scheduler commands
        consumer_thread = Thread(
            target=self.consume_scheduler_commands,
            daemon=True,
            name=f'CuttingMachine-{self.machine_id}-Consumer'
        )
        consumer_thread.start()
        
        # Start heartbeat thread (will begin after assignment)
        heartbeat_thread = Thread(
            target=self.run_heartbeat_cycle,
            kwargs={'interval': 5},
            daemon=True,
            name=f'CuttingMachine-{self.machine_id}-Heartbeat'
        )
        heartbeat_thread.start()
    
    def send_heartbeat(self):
        """Send a heartbeat message to Kafka."""
        with self.lock:
            # Send heartbeats when waiting for assignment or working
            if self.state not in [MachineState.WAITING_FOR_ASSIGNMENT, MachineState.WORKING]:
                return
            
            heartbeat = {
                "title": "heartbeat",
                "machineId": self.machine_id
            }
            
            # Add bladeType only if assigned (WORKING state)
            if self.state == MachineState.WORKING:
                heartbeat["bladeType"] = self.blade_type
        
        message = json.dumps(heartbeat)
        
        try:
            self.kafka.send_message('heartbeats', message, key=f'machine-{self.machine_id}')
            if self.state == MachineState.WORKING:
                LOGGER.debug(f"Machine {self.machine_id} sent heartbeat with blade {self.blade_type}")
            else:
                LOGGER.debug(f"Machine {self.machine_id} sent heartbeat (waiting for assignment)")
        except Exception as e:
            LOGGER.error(f"Failed to send heartbeat from machine {self.machine_id}: {str(e)}")
    
    def run_heartbeat_cycle(self, interval=5):
        """
        Continuously send heartbeat signals at regular intervals.
        Only sends heartbeats when in WORKING state.
        
        Args:
            interval (int): Seconds between heartbeats (default: 5)
        """
        while self.running:
            try:
                self.send_heartbeat()
                time.sleep(interval)
            except Exception as e:
                LOGGER.error(f"Error in heartbeat cycle for machine {self.machine_id}: {str(e)}")
    
    def consume_scheduler_commands(self):
        """Consume messages from productionPlan topic and handle scheduler commands."""
        max_retries = 10
        retry_count = 0
        
        while retry_count < max_retries and self.running:
            try:
                consumer = KafkaConsumer(
                    'productionPlan',
                    bootstrap_servers=self.kafka_bootstrap_servers,
                    auto_offset_reset='latest',
                    enable_auto_commit=True,
                    value_deserializer=lambda m: json.loads(m.decode('utf-8')) if m else None,
                    group_id=f'cutting-machine-{self.machine_id}'
                )
                
                LOGGER.info(f"Machine {self.machine_id} consumer started")
                retry_count = 0
                
                for message in consumer:
                    if message.value:
                        try:
                            self.handle_scheduler_message(message.value)
                        except Exception as e:
                            LOGGER.error(f"Error handling message on machine {self.machine_id}: {str(e)}")
            
            except Exception as e:
                retry_count += 1
                LOGGER.warning(f"Error consuming from productionPlan (machine {self.machine_id}, attempt {retry_count}/{max_retries}): {str(e)}")
                if retry_count < max_retries:
                    time.sleep(2)
                else:
                    LOGGER.error(f"Machine {self.machine_id} failed to connect after {max_retries} attempts")
                    break
    
    def handle_scheduler_message(self, message):
        """
        Handle messages from the scheduler.
        
        Args:
            message (dict): Message from Kafka
        """
        title = message.get("title")
        
        if title == "AssignBlade":
            if message.get("machineId") == self.machine_id:
                self.handle_assign_blade(message)
        
        elif title == "SwapBlade":
            if message.get("machineId") == self.machine_id:
                self.handle_blade_swap(message)
    
    def handle_assign_blade(self, message):
        """
        Handle blade assignment from scheduler.
        
        Args:
            message (dict): AssignBlade message
        """
        new_blade_type = message.get("bladeType")
        
        if new_blade_type is None:
            LOGGER.error(f"Machine {self.machine_id} received AssignBlade without bladeType")
            return
        
        with self.lock:
            self.blade_type = new_blade_type
            self.state = MachineState.WORKING
        
        LOGGER.info(f"Machine {self.machine_id} assigned blade type {new_blade_type} and started working")
    
    def handle_blade_swap(self, message):
        """
        Handle blade swap command from scheduler.
        
        Args:
            message (dict): SwapBlade message
        """
        new_blade_type = message.get("bladeType")
        
        if new_blade_type is None:
            LOGGER.error(f"Machine {self.machine_id} received SwapBlade without bladeType")
            return
        
        LOGGER.info(f"Machine {self.machine_id} received blade swap command, sleeping 2 seconds...")
        time.sleep(2)
        
        with self.lock:
            old_blade_type = self.blade_type
            self.blade_type = new_blade_type
        
        LOGGER.info(f"Machine {self.machine_id} swapped blade from {old_blade_type} to {new_blade_type}")
        
        # Send BladeSwapped confirmation
        self.send_blade_swapped_confirmation()
    
    def send_blade_swapped_confirmation(self):
        """Send BladeSwapped confirmation message to scheduler."""
        confirmation = {
            "title": "BladeSwapped",
            "machineId": self.machine_id
        }
        
        message = json.dumps(confirmation)
        
        try:
            self.kafka.send_message('productionPlan', message, key=f'machine-{self.machine_id}')
            LOGGER.info(f"Machine {self.machine_id} sent BladeSwapped confirmation")
        except Exception as e:
            LOGGER.error(f"Failed to send BladeSwapped confirmation from machine {self.machine_id}: {str(e)}")
    
    def stop(self):
        """Stop the machine."""
        self.running = False
        LOGGER.info(f"Machine {self.machine_id} stopped")


class CuttingMachineSimulator:
    """Manages multiple cutting machines."""
    
    def __init__(self, kafka_producer, kafka_bootstrap_servers, num_machines=3):
        """
        Initialize the cutting machine simulator.
        
        Args:
            kafka_producer (KafkaProducerManager): Kafka producer instance
            kafka_bootstrap_servers (str): Kafka bootstrap servers
            num_machines (int): Number of cutting machines to simulate (default: 3)
        """
        self.kafka = kafka_producer
        self.kafka_bootstrap_servers = kafka_bootstrap_servers
        self.machines = [CuttingMachine(i, kafka_producer, kafka_bootstrap_servers) for i in range(num_machines)]
        self.threads = []
    
    def start_all(self):
        """Start all cutting machines."""
        LOGGER.info(f"Starting {len(self.machines)} cutting machines")
        for machine in self.machines:
            machine.start()
    
    def stop_all(self):
        """Stop all cutting machines."""
        LOGGER.info("Stopping all cutting machines")
        for machine in self.machines:
            machine.stop()