package com.pasta.dbinterface.storage;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.pasta.dbinterface.db.DatabaseManager;
import com.pasta.dbinterface.kafka.KafkaProducerManager;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.util.HashMap;
import java.util.Map;

public class StorageMonitor {
    private static final Logger LOGGER = LoggerFactory.getLogger(StorageMonitor.class);

    private static final double LOW_THRESHOLD = 20.0;
    private static final double HIGH_THRESHOLD = 80.0;
    private static final long MAX_STORAGE_CAPACITY = 100L;

    private final DatabaseManager databaseManager;
    private final KafkaProducerManager kafkaProducer;
    private final ObjectMapper objectMapper = new ObjectMapper();

    // Track last sent alert to avoid continuous sends
    private Map<String, Double> lastSentLevels = new HashMap<>();
    private final Object lock = new Object();

    public StorageMonitor(DatabaseManager databaseManager, KafkaProducerManager kafkaProducer) {
        this.databaseManager = databaseManager;
        this.kafkaProducer = kafkaProducer;
    }

    public void runMonitoringCycle(int intervalSeconds) {
        while (true) {
            try {
                checkStorageLevels();
                Thread.sleep(intervalSeconds * 1000L);
            } catch (InterruptedException e) {
                LOGGER.error("Monitoring cycle interrupted", e);
                Thread.currentThread().interrupt();
                break;
            }
        }
    }

    private void checkStorageLevels() {
        Map<String, Double> storageLevels = new HashMap<>();
        boolean thresholdViolated = false;

        // Check all four combinations
        double aFresh = calculateStorageLevel(databaseManager.getTotalStockByBladeTypeAndFreshness("A", true));
        double aDry = calculateStorageLevel(databaseManager.getTotalStockByBladeTypeAndFreshness("A", false));
        double bFresh = calculateStorageLevel(databaseManager.getTotalStockByBladeTypeAndFreshness("B", true));
        double bDry = calculateStorageLevel(databaseManager.getTotalStockByBladeTypeAndFreshness("B", false));

        storageLevels.put("aFresh", aFresh);
        storageLevels.put("aDry", aDry);
        storageLevels.put("bFresh", bFresh);
        storageLevels.put("bDry", bDry);

        // Check if any threshold is violated
        if (isThresholdViolated(aFresh) || isThresholdViolated(aDry) ||
                isThresholdViolated(bFresh) || isThresholdViolated(bDry)) {
            thresholdViolated = true;
        }

        // Send alert only if threshold violated AND levels have changed since last alert
        if (thresholdViolated && hasLevelsChanged(storageLevels)) {
            sendStorageAlert(storageLevels);
        }
    }

    private double calculateStorageLevel(long totalStock) {
        return (totalStock / (double) MAX_STORAGE_CAPACITY) * 100.0;
    }

    private boolean isThresholdViolated(double level) {
        return level < LOW_THRESHOLD || level > HIGH_THRESHOLD;
    }

    private boolean hasLevelsChanged(Map<String, Double> currentLevels) {
        synchronized (lock) {
            if (lastSentLevels.isEmpty()) {
                return true;  // First alert
            }

            // Check if any level has significantly changed (more than 1% difference)
            for (String key : currentLevels.keySet()) {
                Double lastLevel = lastSentLevels.get(key);
                if (lastLevel == null) {
                    return true;
                }
                if (Math.abs(currentLevels.get(key) - lastLevel) > 1.0) {
                    return true;
                }
            }
            return false;
        }
    }

    private void sendStorageAlert(Map<String, Double> storageLevels) {
        try {
            synchronized (lock) {
                // Update last sent levels
                lastSentLevels.putAll(storageLevels);
            }

            Map<String, Object> message = new HashMap<>();
            message.put("title", "StorageAlert");
            message.put("aFresh", Math.round(storageLevels.get("aFresh") * 100.0) / 100.0);
            message.put("aDry", Math.round(storageLevels.get("aDry") * 100.0) / 100.0);
            message.put("bFresh", Math.round(storageLevels.get("bFresh") * 100.0) / 100.0);
            message.put("bDry", Math.round(storageLevels.get("bDry") * 100.0) / 100.0);

            String jsonMessage = objectMapper.writeValueAsString(message);
            kafkaProducer.sendMessage("storageAlerts", jsonMessage);

            LOGGER.info("Storage alert sent: aFresh={}, aDry={}, bFresh={}, bDry={}",
                    storageLevels.get("aFresh"), storageLevels.get("aDry"),
                    storageLevels.get("bFresh"), storageLevels.get("bDry"));
        } catch (Exception e) {
            LOGGER.error("Error sending storage alert: " + e.getMessage());
        }
    }
}