
package dockerProject; 

import org.apache.kafka.clients.producer.KafkaProducer;
import org.apache.kafka.clients.producer.ProducerRecord;
import org.apache.kafka.clients.consumer.ConsumerRecords;
import org.apache.kafka.clients.consumer.KafkaConsumer;

import org.apache.log4j.Level;
import org.apache.log4j.Logger;

import java.time.Duration;
import java.util.Collections;
import java.util.Properties;


 

public class Scheduler {

    private static String topic = "ProductionPlan";

    public static void main(String[] args) {
        //System.out.println("Eisai boge");
        // Set log level to ERROR to suppress all logs below ERROR
        // Suppress all logging
        Logger.getLogger("org.apache.kafka").setLevel(Level.OFF);
        Logger.getLogger("org.apache.zookeeper").setLevel(Level.OFF);

        // Set the root logger level to OFF
        Logger rootLogger = Logger.getLogger("");
        rootLogger.setLevel(Level.OFF);
        consumeMessages();
    }

    private static void produceMessage() {
        
    }

    private static void consumeMessages() {
        Properties props = new Properties();
        props.put("bootstrap.servers", "kafka:29092");
        props.put("group.id", "test-group");
        props.put("key.deserializer", "org.apache.kafka.common.serialization.StringDeserializer");
        props.put("value.deserializer", "org.apache.kafka.common.serialization.StringDeserializer");
        props.put("auto.offset.reset", "earliest");

        try (KafkaConsumer<String, String> consumer = new KafkaConsumer<>(props)) {
            consumer.subscribe(Collections.singletonList(topic));

            while (true) {
                ConsumerRecords<String, String> records = consumer.poll(Duration.ofMillis(1000));
                records.forEach(record -> {
                    System.out.printf("Consumed: key=%s, value=%s%n", record.key(), record.value());
                    Properties producerProps = new Properties();
                    producerProps.put("bootstrap.servers", "kafka:29092");
                    producerProps.put("key.serializer", "org.apache.kafka.common.serialization.StringSerializer");
                    producerProps.put("value.serializer", "org.apache.kafka.common.serialization.StringSerializer");

                    try (KafkaProducer<String, String> producer = new KafkaProducer<>(producerProps)) {
                        
                        ProducerRecord<String, String> producerRecord = new ProducerRecord<>("ChangeMachineBlade", "Change Production Plan", "Change Blade to Cutting Machine 1");
                        producer.send(producerRecord);
                        System.out.println("Produced: key 1, value Change Production Plan");
                        
                    }
                });

                    // Sleep for 5 seconds
                try {
                    Thread.sleep(5000);
                } catch (InterruptedException e) {
                    Thread.currentThread().interrupt(); // Restore interrupted status
                    System.out.println("Thread was interrupted, stopping the consumer.");
                    break; // Exit the loop if interrupted
                }
            }
        }
    }
}

 