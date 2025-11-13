import logging
import threading
from .database import DatabaseConnection
from .kafka_producer import KafkaProducerManager
from .batch_manager import BatchManager
from .storage_monitor import StorageMonitor

# Logger setup
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s:%(name)s:%(message)s'
)
LOGGER = logging.getLogger(__name__)


def main():
    """Main entry point for the simulation engine."""
    LOGGER.info("Starting Pasta Production Simulation Engine")
    
    # Initialize connections
    LOGGER.info("Initializing database connection...")
    db = DatabaseConnection(db_url='postgresql://user:password@db:5432/mydatabase')
    
    LOGGER.info("Initializing Kafka producer...")
    kafka = KafkaProducerManager(bootstrap_servers='kafka:29092')
    
    # Initialize managers
    LOGGER.info("Initializing batch manager...")
    batch_manager = BatchManager(db, kafka)
    
    LOGGER.info("Initializing storage monitor...")
    storage_monitor = StorageMonitor(db, kafka)
    
    # Create threads for each task
    LOGGER.info("Creating worker threads...")
    
    insert_thread = threading.Thread(
        target=batch_manager.run_insert_cycle,
        kwargs={'interval': 5},
        daemon=True,
        name='BatchInsertWorker'
    )
    
    reduction_thread = threading.Thread(
        target=batch_manager.run_reduction_cycle,
        kwargs={'interval': 10, 'total_reduction': 20},
        daemon=True,
        name='BatchReductionWorker'
    )
    
    monitoring_thread = threading.Thread(
        target=storage_monitor.run_monitoring_cycle,
        kwargs={'interval': 10},
        daemon=True,
        name='StorageMonitorWorker'
    )
    
    # Start all threads
    LOGGER.info("Starting worker threads...")
    insert_thread.start()
    reduction_thread.start()
    monitoring_thread.start()
    
    LOGGER.info("All worker threads started. Simulation engine running...")
    
    # Keep the main thread alive
    try:
        while True:
            threading.Event().wait(1)
    except KeyboardInterrupt:
        LOGGER.info("Shutdown signal received")
        db.close()
        kafka.close()
        LOGGER.info("Simulation engine stopped")


if __name__ == '__main__':
    main()