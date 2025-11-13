import logging
import time
from sqlalchemy import text

# Logger setup
LOGGER = logging.getLogger(__name__)


class StorageMonitor:
    """Monitors and updates storage levels based on batch inventory."""
    
    # Storage level thresholds
    LOW_THRESHOLD = 20            # Below 20%: low stock alert
    HIGH_THRESHOLD = 80           # Above 80%: reduce production alert
    MAX_STORAGE_CAPACITY = 100    # Maximum storage capacity (for percentage calculation)
    
    # Storage level categories
    STORAGE_CATEGORIES = [
        ('A', 'fresh'),
        ('A', 'dry'),
        ('B', 'fresh'),
        ('B', 'dry')
    ]
    
    def __init__(self, db_connection, kafka_producer):
        """
        Initialize storage monitor.
        
        Args:
            db_connection (DatabaseConnection): Database connection instance
            kafka_producer (KafkaProducerManager): Kafka producer instance
        """
        self.db = db_connection
        self.kafka = kafka_producer
    
    def _get_total_stock(self, blade_type, is_fresh):
        """
        Get total stock for a specific blade type and freshness.
        
        Args:
            blade_type (str): Blade type ('A' or 'B')
            is_fresh (bool): True for fresh, False for dry
            
        Returns:
            int: Total stock quantity
        """
        query = """
            SELECT SUM(inStock) AS total
            FROM pasta_db.batches
            WHERE blade_type = :blade_type AND isFresh = :is_fresh
        """
        
        try:
            result = self.db.execute_query(query, {
                'blade_type': blade_type,
                'is_fresh': is_fresh
            })
            total = result.scalar() or 0
            return total
        except Exception as e:
            LOGGER.error(f"Failed to get total stock for {blade_type}-{is_fresh}: {str(e)}")
            return 0
    
    def _calculate_storage_level(self, total_stock):
        """
        Calculate storage level as a percentage.
        
        Args:
            total_stock (int): Total stock quantity
            
        Returns:
            float: Storage level percentage (0-100)
        """
        return (total_stock / self.MAX_STORAGE_CAPACITY) * 100
    
    def _create_category_label(self, blade_type, is_fresh):
        """
        Create a human-readable label for a storage category.
        
        Args:
            blade_type (str): Blade type ('A' or 'B')
            is_fresh (bool): True for fresh, False for dry
            
        Returns:
            str: Label like "A-fresh" or "B-dry"
        """
        freshness = "fresh" if is_fresh else "dry"
        return f"{blade_type}-{freshness}"
    
    def check_and_update_storage_levels(self):
        """
        Check current stock levels and send Kafka alerts if thresholds are breached.
        Sends a single message containing all four storage levels if any threshold violation occurs.
        
        Returns:
            dict: Summary of storage levels and alerts
        """
        alerts = []
        storage_summary = {}
        threshold_violated = False
        
        try:
            for blade_type, freshness_str in self.STORAGE_CATEGORIES:
                is_fresh = (freshness_str == 'fresh')
                category_label = self._create_category_label(blade_type, is_fresh)
                
                # Get total stock
                total_stock = self._get_total_stock(blade_type, is_fresh)
                
                # Calculate percentage
                storage_level = self._calculate_storage_level(total_stock)
                
                storage_summary[category_label] = {
                    'total_stock': total_stock,
                    'level_percent': storage_level
                }
                
                LOGGER.info(f"Storage level for {category_label}: {storage_level:.2f}% ({total_stock} units)")
                
                # Check thresholds
                if storage_level < self.LOW_THRESHOLD or storage_level > self.HIGH_THRESHOLD:
                    threshold_violated = True
                    alert_msg = f"{category_label}: {storage_level:.2f}%"
                    alerts.append(alert_msg)
            
            # Send single consolidated message if any threshold is violated
            if threshold_violated:
                message = "Production Plan Alert - Storage Levels: " + " | ".join(alerts)
                LOGGER.warning(message)
                self.kafka.send_message('ProductionPlan', message, key='StorageAlert')
        
        except Exception as e:
            LOGGER.error(f"Error checking storage levels: {str(e)}")
        
        return {
            'summary': storage_summary,
            'alerts': alerts,
            'threshold_violated': threshold_violated
        }
    
    def run_monitoring_cycle(self, interval=10):
        """
        Continuously monitor storage levels at regular intervals.
        
        Args:
            interval (int): Seconds between checks (default: 10)
        """
        LOGGER.info("Starting storage monitoring cycle")
        try:
            while True:
                self.check_and_update_storage_levels()
                time.sleep(interval)
        except Exception as e:
            LOGGER.error(f"Error in monitoring cycle: {str(e)}")
            raise