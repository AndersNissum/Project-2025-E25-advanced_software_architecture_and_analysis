package com.pasta.scheduler;

import com.pasta.scheduler.kafka.KafkaConsumerManager;
import com.pasta.scheduler.kafka.KafkaProducerManager;
import com.pasta.scheduler.machine.MachineManager;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

public class Scheduler {
    private static final Logger LOGGER = LoggerFactory.getLogger(Scheduler.class);
    private static final int INITIAL_FRESH_AMOUNT = 4;

    private final MachineManager machineManager;
    private final KafkaConsumerManager kafkaConsumer;
    private final KafkaProducerManager kafkaProducer;
    private int freshAmount;
    private int lastSentFreshAmount;

    public Scheduler(String kafkaBootstrapServers) {
        this.machineManager = new MachineManager();
        this.kafkaConsumer = new KafkaConsumerManager(kafkaBootstrapServers);
        this.kafkaProducer = new KafkaProducerManager(kafkaBootstrapServers);
        this.freshAmount = INITIAL_FRESH_AMOUNT;
        this.lastSentFreshAmount = -1;
    }

    public void start() {
        LOGGER.info("Starting Scheduler");

        // Send initial ChangeFreshAmount message
        sendChangeFreshAmountMessage(freshAmount);

        // Start Kafka consumer in a separate thread (handles heartbeats, storage alerts, and health checks)
        Thread consumerThread = new Thread(() -> {
            LOGGER.info("Starting Kafka consumer");
            kafkaConsumer.consumeHeartbeats(machineManager, kafkaProducer, this);
        }, "KafkaConsumerWorker");
        consumerThread.setDaemon(true);
        consumerThread.start();

        // Start machine health checker in a separate thread with a delay
        Thread healthCheckThread = new Thread(() -> {
            try {
                // Wait 10 seconds for initial machines to be discovered via heartbeats
                LOGGER.info("Waiting 10 seconds for initial machine discovery...");
                Thread.sleep(10000);
                LOGGER.info("Starting machine health checker");
                machineManager.startHealthCheck(kafkaProducer);
            } catch (InterruptedException e) {
                LOGGER.error("Health check thread interrupted", e);
                Thread.currentThread().interrupt();
            }
        }, "MachineHealthCheckerWorker");
        healthCheckThread.setDaemon(true);
        healthCheckThread.start();

        LOGGER.info("Scheduler started successfully with freshAmount={}", freshAmount);
    }

    public synchronized void updateFreshAmount(int delta) {
        int newFreshAmount = freshAmount + delta;

        // Clamp freshAmount between 0 and 10
        if (newFreshAmount < 0) {
            newFreshAmount = 0;
            LOGGER.warn("freshAmount would be negative, clamped to 0");
        } else if (newFreshAmount > 10) {
            newFreshAmount = 10;
            LOGGER.warn("freshAmount would exceed 10, clamped to 10");
        }

        freshAmount = newFreshAmount;
        LOGGER.info("Updated freshAmount: {} (delta: {})", freshAmount, delta);
        sendChangeFreshAmountMessage(freshAmount);
    }

    private void sendChangeFreshAmountMessage(int amount) {
        // Only send if value has actually changed
        if (amount == lastSentFreshAmount) {
            LOGGER.debug("freshAmount unchanged ({}), skipping message", amount);
            return;
        }

        lastSentFreshAmount = amount;
        String message = String.format(
                "{\"title\":\"ChangeFreshAmount\",\"freshAmount\":%d}",
                amount
        );
        kafkaProducer.sendMessage("productionPlan", message);
        LOGGER.info("Sent ChangeFreshAmount message with freshAmount={}", amount);
    }

    public int getFreshAmount() {
        return freshAmount;
    }

    public static void main(String[] args) {
        String kafkaBootstrapServers = "kafka:29092";
        Scheduler scheduler = new Scheduler(kafkaBootstrapServers);
        scheduler.start();

        // Keep main thread alive
        try {
            Thread.currentThread().join();
        } catch (InterruptedException e) {
            LOGGER.error("Main thread interrupted", e);
            Thread.currentThread().interrupt();
        }
    }
}