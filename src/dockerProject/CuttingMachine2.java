package dockerProject; 
import java.io.IOException;

import javax.net.ssl.SSLSocketFactory;
import org.eclipse.paho.client.mqttv3.persist.MemoryPersistence;
import org.eclipse.paho.client.mqttv3.persist.MqttDefaultFilePersistence;

import org.eclipse.paho.client.mqttv3.*;


import org.eclipse.paho.client.mqttv3.*;

public class CuttingMachine2 implements MqttCallback {

    public static void main(String[] args) {
        String broker = "tcp://192.168.1.183:1883";
        String clientId = "CuttingMachine";

        try {
            // Create client (in-memory persistence)
            MqttClient client = new MqttClient(broker, clientId, new MemoryPersistence());

            // Set callback
            client.setCallback(new CuttingMachine2());

            // Connection options
            MqttConnectOptions options = new MqttConnectOptions();
            options.setAutomaticReconnect(true);
            options.setCleanSession(true);

            // Connect
            System.out.println("Connecting to broker...");
            client.connect(options);
            System.out.println("Connected!");

            // Subscribe
            String topic = "ProductionPlan";
            client.subscribe(topic, 1);
            System.out.println("Subscribed to topic: " + topic);

            // Keep app alive
            System.out.println("Waiting for messages...");
            
            // Block indefinitely so the program keeps running
            synchronized (CuttingMachine2.class) {
                CuttingMachine2.class.wait();
            }

        } catch (Exception e) {
            e.printStackTrace();
        }
    }

    @Override
    public void connectionLost(Throwable cause) {
        System.out.println("Connection lost: " + cause.getMessage());
    }

    @Override
    public void messageArrived(String topic, MqttMessage message) {
        System.out.println("Message on " + topic + ": " + new String(message.getPayload()));
        // ---- Publish in response ----
        String responseTopic = "Machine2Response";
        String payload = "Machine2 switched blade successfully";

        MqttMessage reply = new MqttMessage(payload.getBytes());
        reply.setQos(1);

        client.publish(responseTopic, reply);
        System.out.println("Published response on " + responseTopic);
    }

    @Override
    public void deliveryComplete(IMqttDeliveryToken token) {
        // Not used for consumers
    }
}


