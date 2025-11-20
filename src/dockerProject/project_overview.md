# Pasta Production System - Complete Project Overview

## Architecture Summary

Docker-based pasta factory simulation with Java microservices (scheduler, cutting machines, DB interface, sorting subsystem) communicating via Kafka/MQTT bridge. Python simulation engine manages batch production to maintain 200-unit total stock. Leader election coordinates two scheduler instances via Redis. React dashboard visualizes operations.

---

## Folder Structure

```
dockerProject/
├── cuttingMachine/              # Java project for cutting machines
│   ├── pom.xml
│   ├── Dockerfile               # Multi-stage build (JDK→JRE)
│   ├── src/main/java/com/pasta/cuttingmachine/
│   │   ├── CuttingMachine.java         # Main entry point
│   │   ├── state/MachineState.java     # State machine (INITIALIZING→WAITING→WORKING)
│   │   └── mqtt/MqttManager.java       # MQTT client wrapper
│   └── src/main/resources/log4j2.xml   # Logging config
│
├── scheduler/                   # Java project for scheduler (active/shadow)
│   ├── pom.xml
│   ├── Dockerfile
│   ├── src/main/java/com/pasta/scheduler/
│   │   ├── Scheduler.java
│   │   ├── kafka/
│   │   │   ├── KafkaConsumerManager.java     # Consumes heartbeats, storageAlerts
│   │   │   └── KafkaProducerManager.java     # Sends AssignBlade, SwapBlade, ChangeFreshAmount
│   │   ├── machine/
│   │   │   ├── Machine.java
│   │   │   └── MachineManager.java           # Tracks machines, deduplicates heartbeats
│   │   ├── redis/RedisManager.java           # Leader election & state persistence
│   │   ├── storage/StorageAlertHandler.java  # Reacts to storage threshold violations
│   │   └── enums/BladeType.java
│   └── src/main/resources/log4j2.xml
│
├── dbInterface/                 # Java project for DB monitoring
│   ├── pom.xml
│   ├── Dockerfile
│   ├── src/main/java/com/pasta/dbinterface/
│   │   ├── DbInterface.java
│   │   ├── db/DatabaseManager.java           # JDBC wrapper with retry logic
│   │   ├── kafka/KafkaProducerManager.java   # Sends StorageAlert to Kafka
│   │   └── storage/StorageMonitor.java       # Queries DB, sends alerts on threshold breach
│   └── src/main/resources/log4j2.xml
│
├── sortingSubsystem/            # Java project for sorting
│   ├── pom.xml
│   ├── Dockerfile
│   ├── src/main/java/com/pasta/sortingsubsystem/
│   │   ├── SortingSubsystem.java
│   │   ├── FreshAmountManager.java            # Manages freshAmount (0-10)
│   │   └── kafka/
│   │       ├── KafkaConsumerManager.java      # Consumes ChangeFreshAmount
│   │       └── KafkaProducerManager.java      # Sends FreshAmountChanged confirmation
│   └── src/main/resources/log4j2.xml
│
├── simulationEngine/            # Python project for batch production
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── app.py                               # Main entry
│   ├── database.py                          # SQLAlchemy DB wrapper
│   ├── kafka_producer.py                    # Confluent Kafka producer
│   └── batch_manager.py                     # Creates batches, balances stock, sends storage levels
│
├── mqttKafkaBridge/             # Python bridge for MQTT↔Kafka
│   ├── Dockerfile
│   ├── requirements.txt
│   └── mqtt_kafka_broker.py                 # Bidirectional message forwarding with topic routing
│
├── kafka-monitor/               # Python console for Kafka monitoring
│   ├── Dockerfile
│   ├── requirements.txt
│   └── kafka_monitor.py                     # Colored terminal output of heartbeats & productionPlan
│
├── mosquitto/
│   └── config/mosquitto.conf               # MQTT broker configuration
│
├── pasta-dashboard/             # React dashboard (not our focus)
│
├── docker-compose.yml           # Orchestrates all 12+ services
├── init.sql                     # Database schema & initial data
├── run_experiment.sh            # Cleanup & rebuild script
└── kafka_messages_summary.md    # Message format documentation

```

---

## Component Details

### CuttingMachine (Java)
**Role**: Simulates physical cutting machines; sends heartbeats; receives blade assignment/swap commands via MQTT.

**State Machine**:
- `INITIALIZING` → `WAITING_FOR_ASSIGNMENT` → `WORKING`
- Only sends heartbeats with `bladeType` when in `WORKING` state
- Sends heartbeats every 5 seconds (with or without bladeType depending on state)

**Key Features**:
- Connects to Mosquitto MQTT broker with 30-retry logic (2s backoff)
- Subscribes to: `productionPlan/assignBlade`, `productionPlan/swapBlade`, `updateManager/killMachine`
- Uses message queue for async MQTT callbacks (prevents callback starvation)
- Publishes initial heartbeat (no blade) → receives AssignBlade → transitions to WORKING → sends heartbeats with blade
- Handles blade swaps (2s sleep before confirmation) and machine recovery

**Fixed Issues**:
- Callback starvation: Added message queue processing in separate thread
- MQTT topic routing: Use exact topics (`productionPlan/assignBlade`) not wildcards
- Initial heartbeat: Send every 5s in WAITING state to be discovered by Scheduler

---

### Scheduler (Java, 2 instances for failover)
**Role**: Orchestrates production by discovering machines, assigning blades, reacting to storage alerts.

**Architecture**:
- Primary + Shadow instance
- Redis leader election (5s lease, NX set)
- Reads machine heartbeats & storage alerts from Kafka
- Sends AssignBlade, SwapBlade, ChangeFreshAmount to productionPlan topic

**Key Components**:
- **MachineManager**: Tracks machines, deduplicates heartbeats (1s window), balances blade types
- **StorageAlertHandler**: Reacts to storage level violations (<20% or >80%)
- **RedisManager**: Leader election, persists machine state & freshAmount
- **KafkaConsumerManager**: Subscribes to `heartbeats` & `storageAlerts` (latest offset, group='scheduler-group')

**Fixed Issues**:
- Duplicate AssignBlade: Added `lastHeartbeatTime` map with 1s deduplication window
- Missing heartbeats: Scheduler now deduplicates to prevent spam
- Machine discovery: 12s discovery phase before sending commands

---

### DbInterface (Java)
**Role**: Monitors database storage levels; sends alerts to Scheduler when thresholds breach.

**Components**:
- **DatabaseManager**: JDBC wrapper with 30-retry connection logic
- **StorageMonitor**: Every 10s queries DB (sum inStock by blade_type × isFresh)
- Calculates storage % (stock/100×100), sends StorageAlert if <20% or >80%
- Deduplicates alerts (only sends if levels changed >1% since last alert)

**Message Flow**: DB → query totals → calculate % → breach threshold → StorageAlert to Kafka

---

### SortingSubsystem (Java)
**Role**: Maintains `freshAmount` state; receives updates from Scheduler.

**Components**:
- **FreshAmountManager**: Tracks freshAmount (0-10, clamped)
- Consumes `ChangeFreshAmount` from `productionPlan` topic
- Sends `FreshAmountChanged` confirmation back to productionPlan

**Purpose**: Controls fresh vs dry batch ratio. BatchManager reads this to split batches.

---

### SimulationEngine (Python)
**Role**: Simulates real factory; creates batches based on heartbeats; balances stock to 200.

**Components**:
- **BatchManager**: 
  - Consumes heartbeats → creates 2 batches per heartbeat (fresh=freshAmount, dry=10-freshAmount)
  - Consumes ChangeFreshAmount messages to update freshAmount
  - Balances total stock to 200 by randomly reducing batches
  - Sends StorageLevels to dashboard every rebalance

**Database Schema**:
- `pasta_db.batches`: id, blade_type, isFresh, productionDate, inStock
- Initial: 20 rows (5 per type: A/B × fresh/dry), 10 units each

**Kafka Topics**: Consumes `heartbeats`, `productionPlan` (latest offset)

---

### MqttKafkaBridge (Python)
**Role**: Bridges MQTT ↔ Kafka with intelligent topic routing.

**Message Flow**:
- **MQTT → Kafka**: `heartbeats` topic, `productionPlan` topic
- **Kafka → MQTT** (with routing):
  - `AssignBlade` → `productionPlan/assignBlade`
  - `SwapBlade` → `productionPlan/swapBlade`
  - `killMachine` → `updateManager/killMachine`

**Fixed Issues**:
- Removed `retain=True` flag to prevent message replay
- Added topic-based routing in `_forward_kafka_to_mqtt()` to map Kafka messages to MQTT subtopics
- Handles JSON parsing to extract message title for routing

---

### KafkaMonitor (Python)
**Role**: Real-time terminal dashboard for debugging.

**Output**: 
- Color-coded messages (heartbeats 💓, productionPlan 📋)
- Shows timestamp, topic, JSON payload
- Consumes both topics from beginning (earliest offset)

---

## Infrastructure

### Docker Services (docker-compose.yml)
1. **Zookeeper**: Kafka coordination
2. **Kafka**: Message broker (5 partitions, 1 replication factor)
   - Topics: `heartbeats`, `productionPlan`, `storageAlerts`, `storageLevels`, `updateManager`
   - Healthcheck: `kafka-topics --list`
3. **PostgreSQL**: Production data
   - Schema: `pasta_db` with `batches` table
4. **pgAdmin**: DB UI (port 5000)
5. **Redis**: Leader election & state persistence
6. **Mosquitto**: MQTT broker (port 1883)
   - Healthcheck: netcat on port 1883
7. **mqtt-kafka-bridge**: Message forwarding (depends_on: mosquitto healthy, kafka healthy)
8. **cutting-machine-0/1/2**: Simulated cutting machines (depends_on: mosquitto healthy)
9. **scheduler** + **scheduler-shadow**: Active/shadow scheduler
10. **db-interface**: Storage level monitor
11. **sorting-subsystem**: Batch sorting management
12. **pasta-system**: Batch production simulation
13. **kafka-monitor**: Console monitor (depends_on: kafka healthy)

---

## Message Protocol

### Heartbeats (MQTT → Kafka)
```json
// Without blade (WAITING_FOR_ASSIGNMENT)
{"title": "heartbeat", "machineId": 0}

// With blade (WORKING)
{"title": "heartbeat", "machineId": 0, "bladeType": "A"}
```

### AssignBlade (Scheduler → Kafka → MQTT)
```json
{"title": "AssignBlade", "machineId": 0, "bladeType": "A"}
// Routed to: productionPlan/assignBlade
```

### SwapBlade (Scheduler → Kafka → MQTT)
```json
{"title": "SwapBlade", "machineId": 0, "bladeType": "B"}
// Routed to: productionPlan/swapBlade
```

### StorageAlert (DbInterface → Kafka)
```json
{"title": "StorageAlert", "aFresh": 35.5, "aDry": 42.0, "bFresh": 28.3, "bDry": 31.2}
```

### ChangeFreshAmount (Scheduler → Kafka → SortingSubsystem)
```json
{"title": "ChangeFreshAmount", "freshAmount": 6}
```

---

## Key Workflows

### Machine Discovery & Blade Assignment
1. Machine 0 starts → sends heartbeat without blade every 5s
2. Scheduler receives heartbeat → creates Machine(0, WAITING_FOR_ASSIGNMENT)
3. After discovery phase (12s) → sends AssignBlade(0, A) to Kafka
4. Bridge routes to `productionPlan/assignBlade` MQTT topic
5. Machine 0 receives on MQTT → transitions to WORKING
6. Next heartbeat includes bladeType "A"
7. Scheduler deduplicates (1s window) → no duplicate AssignBlade

### Storage-Based Production Adjustment
1. DbInterface queries every 10s: SUM(inStock) per blade_type × isFresh
2. If <20% or >80% → sends StorageAlert to Kafka
3. Scheduler receives alert → StorageAlertHandler analyzes
4. Identifies problem category (e.g., "fresh" too low)
5. Sends ChangeFreshAmount(+2) to increase fresh production
6. SortingSubsystem receives → updates freshAmount
7. BatchManager reads new freshAmount → splits next batches accordingly

### Batch Production Cycle
1. Every 5s: Cutting machine sends heartbeat
2. BatchManager consumes heartbeat → creates 2 batches (fresh=freshAmount, dry=10-freshAmount)
3. Total stock calculated
4. If >200 → randomly reduce batches until =200
5. Calculate storage % → send StorageLevels to dashboard
6. DbInterface monitors → sends StorageAlert if threshold breached

---

## Development Notes

### Key Fixes Applied
1. **Mosquitto healthcheck**: Changed from `mosquitto_sub` to `netcat` probe (`nc localhost 1883`)
2. **Java Dockerfiles**: Multi-stage build with `eclipse-temurin:21` (JDK) → `eclipse-temurin:21-jre` (runtime)
3. **Log4j2 configuration**: Added `log4j2.xml` to all Java projects for console logging
4. **MQTT callbacks**: Implemented message queue processing to prevent callback starvation
5. **Bridge topic routing**: Parse message JSON to route subtopics (`AssignBlade` → `productionPlan/assignBlade`)
6. **Heartbeat deduplication**: Track heartbeat times per machine; ignore duplicates within 1s window
7. **Exact MQTT topics**: Subscribe to exact topics, not wildcards (Paho 1.2.5 limitation)
8. **Bridge retain flag**: Disabled `retain=True` to prevent message replay

### Running the System
```bash
# Full setup
./run_experiment.sh

# View logs
docker logs <container_id> -f

# Monitor Kafka messages
docker logs kafka-monitor -f

# Check database
# UI: http://localhost:5000 (pgAdmin)

# Test MQTT directly
docker exec -it mosquitto sh
mosquitto_sub -h localhost -t 'productionPlan/assignBlade' -v
```

---

## Quality Attributes Achieved

- **Availability**: 2 schedulers with Redis leader election; machines auto-reconnect
- **Scalability**: Kafka partitioning; machines added via heartbeat discovery
- **Modifiability**: Microservices architecture; easy to change production logic
- **Deployability**: Docker Compose orchestration; zero-downtime scheduler failover
- **Integrability**: MQTT↔Kafka bridge enables external device integration
