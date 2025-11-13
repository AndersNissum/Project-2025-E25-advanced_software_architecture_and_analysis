import logging
import random
import time
from faker import Faker

# Logger setup
LOGGER = logging.getLogger(__name__)

# Initialize Faker
fake = Faker('en_US')


class BatchManager:
    """Manages batch insertion and reduction operations."""
    
    def __init__(self, db_connection, kafka_producer):
        """
        Initialize batch manager.
        
        Args:
            db_connection (DatabaseConnection): Database connection instance
            kafka_producer (KafkaProducerManager): Kafka producer instance
        """
        self.db = db_connection
        self.kafka = kafka_producer
    
    def insert_batch(self, blade_type=None, is_fresh=None, in_stock=10):
        """
        Insert a new batch into the database with auto-incremented ID.
        
        Args:
            blade_type (str): Blade type ('A' or 'B'). If None, randomly chosen.
            is_fresh (bool): True for fresh, False for dry. If None, randomly chosen.
            in_stock (int): Initial stock quantity (default: 10)
            
        Returns:
            bool: True if insertion successful
        """
        # Randomly choose if not specified
        if blade_type is None:
            blade_type = random.choice(['A', 'B'])
        if is_fresh is None:
            is_fresh = random.choice([True, False])
        
        insert_query = """
            INSERT INTO pasta_db.batches (blade_type, isFresh, productionDate, inStock)
            VALUES (:blade_type, :isFresh, NOW(), :inStock)
        """
        
        try:
            self.db.execute_insert(insert_query, {
                'blade_type': blade_type,
                'isFresh': is_fresh,
                'inStock': in_stock
            })
            LOGGER.info(f"Inserted batch: blade_type={blade_type}, isFresh={is_fresh}, inStock={in_stock}")
            return True
        except Exception as e:
            LOGGER.error(f"Failed to insert batch: {str(e)}")
            raise
    
    def get_all_batches(self):
        """
        Retrieve all batches with stock > 0.
        
        Returns:
            list: List of batch rows from database
        """
        try:
            result = self.db.execute_query("SELECT * FROM pasta_db.batches WHERE inStock > 0")
            return result.fetchall()
        except Exception as e:
            LOGGER.error(f"Failed to fetch batches: {str(e)}")
            return []
    
    def reduce_batch_stock(self, batch_id, amount):
        """
        Reduce stock for a specific batch.
        
        Args:
            batch_id (int): Batch ID to reduce
            amount (int): Amount to reduce by
        """
        update_query = """
            UPDATE pasta_db.batches
            SET inStock = GREATEST(0, inStock - :amount)
            WHERE id = :batch_id
        """
        
        try:
            self.db.execute_update(update_query, {
                'amount': amount,
                'batch_id': batch_id
            })
            LOGGER.info(f"Reduced batch {batch_id} stock by {amount}")
        except Exception as e:
            LOGGER.error(f"Failed to reduce batch stock: {str(e)}")
            raise
    
    def reduce_all_batches(self, total_reduction=20):
        """
        Simulate consumption by reducing stock across all batches.
        Reduces up to total_reduction units distributed across batches.
        
        Args:
            total_reduction (int): Total amount to reduce across all batches (default: 20)
        """
        batches = self.get_all_batches()
        
        if not batches:
            LOGGER.warning("No batches available to reduce")
            return
        
        remaining_reduction = total_reduction
        
        for batch in batches:
            if remaining_reduction <= 0:
                break
            
            batch_id = batch[0]  # First column is ID
            in_stock = batch[4]  # Fifth column is inStock
            
            # Randomly determine reduction amount, but not more than remaining or in_stock
            max_reduction = min(remaining_reduction, in_stock)
            reduction_amount = fake.random_int(min=0, max=max_reduction)
            
            if reduction_amount > 0:
                self.reduce_batch_stock(batch_id, reduction_amount)
                remaining_reduction -= reduction_amount
        
        LOGGER.info(f"Batch reduction cycle complete. Total reduced: {total_reduction - remaining_reduction}")
    
    def run_insert_cycle(self, interval=5):
        """
        Continuously insert new batches at regular intervals.
        
        Args:
            interval (int): Seconds between insertions (default: 5)
        """
        LOGGER.info("Starting batch insertion cycle")
        try:
            while True:
                self.insert_batch()
                time.sleep(interval)
        except Exception as e:
            LOGGER.error(f"Error in insert cycle: {str(e)}")
            raise
    
    def run_reduction_cycle(self, interval=10, total_reduction=20):
        """
        Continuously reduce batch stock at regular intervals.
        
        Args:
            interval (int): Seconds between reductions (default: 10)
            total_reduction (int): Total amount to reduce per cycle (default: 20)
        """
        LOGGER.info("Starting batch reduction cycle")
        try:
            while True:
                self.reduce_all_batches(total_reduction)
                time.sleep(interval)
        except Exception as e:
            LOGGER.error(f"Error in reduction cycle: {str(e)}")
            raise