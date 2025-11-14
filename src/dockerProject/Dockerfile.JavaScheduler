# Use JDK for building and running the application
FROM eclipse-temurin:11

# Set the working directory
WORKDIR /app

# Copy your Java source file into the container
COPY Scheduler.java .

# Download Kafka client JARs
RUN mkdir -p libs && \
    curl -o libs/kafka-clients.jar https://repo1.maven.org/maven2/org/apache/kafka/kafka-clients/3.5.1/kafka-clients-3.5.1.jar && \
    curl -o libs/slf4j-api.jar https://repo1.maven.org/maven2/org/slf4j/slf4j-api/1.7.32/slf4j-api-1.7.32.jar && \
    curl -o libs/slf4j-simple.jar https://repo1.maven.org/maven2/org/slf4j/slf4j-simple/1.7.32/slf4j-simple-1.7.32.jar && \
    curl -o libs/log4j-core.jar https://repo1.maven.org/maven2/log4j/log4j/1.2.17/log4j-1.2.17.jar

# Specify the command to run the application by running the .java source file
CMD ["java", "-cp", "libs/*:.", "Scheduler.java"]