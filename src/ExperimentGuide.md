# Pasta Production System - Experiment Architecture Guide

## Overview

This system simulates a pasta production factory with cutting machines, a scheduler, and storage monitoring. The experiment measures **end-to-end latency** for three types of events: machine discovery, machine failures, and storage alerts. ChaosPanda (inspired by Netflix's Chaos Monkey) injects failures to simulate real-world conditions and test system resilience under varying chaos levels.

---

## Component Descriptions

### **1. Cutting Machines** (`cuttingMachine/`)
- **Role**: Simulate physical pasta cutting machines
- **Behavior**: 
  - Send heartbeats every 5 seconds via MQTT
  - Heartbeats include `machineId`, `bladeType` (A or B), and operational `state`
  - Receive `AssignBlade` and `SwapBlade` commands from Scheduler
- **Communication**: MQTT → MQTT-Kafka Bridge → Kafka

### **2. Scheduler** (`scheduler/`)
- **Role**: Central orchestrator for production planning
- **Responsibilities**:
  - Discover new machines (via heartbeats without `bladeType`)
  - Assign blade types to balance A/B distribution
  - Detect machine failures (missing heartbeats >10s)
  - React to storage alerts by swapping blades or adjusting fresh amount
- **High Availability**: Shadow tactic adopted. Uses Redis for leader election; supports active/standby failover
- **Communication**: Kafka (consumer: heartbeats, storageAlerts; producer: productionPlan)

### **3. Simulation Engine** (`simulationEngine/`)
- **Role**: Simulates pasta batch production and consumption
- **Behavior**:
  - Creates batches (fresh + dry) on each machine heartbeat with `bladeType`
  - Batch sizes controlled by `freshAmount` (from Scheduler)
  - Randomly consumes stock to maintain ~200 total units
- **Communication**: Kafka consumer (heartbeats, productionPlan); PostgreSQL writer

### **4. DB Interface** (`dbInterface/`)
- **Role**: Monitors storage levels and triggers alerts
- **Behavior**:
  - Queries PostgreSQL every 10 seconds for stock levels (A-fresh, A-dry, B-fresh, B-dry)
  - Calculates percentages (max capacity: 100 units per category)
  - Sends `StorageAlert` if any category < 20% or > 80%
- **Communication**: PostgreSQL reader; Kafka producer (storageAlerts)

### **5. Sorting Subsystem** (`sortingSubsystem/`)
- **Role**: Simulates sorting machinery that controls fresh/dry ratio
- **Behavior**:
  - Listens for `ChangeFreshAmount` messages from Scheduler
  - Confirms changes by publishing `FreshAmountChanged` to Kafka
- **Communication**: Kafka (consumer/producer on productionPlan topic)

### **6. MQTT-Kafka Bridge** (`mqttKafkaBridge/`)
- **Role**: Bidirectional message translator between MQTT and Kafka
- **Filters**: Only forwards specific message types (`AssignBlade`, `SwapBlade`, `heartbeat`, etc.)
- **Communication**: MQTT Broker ↔ Kafka

### **7. ChaosPanda** (`chaosPanda/`)
- **Role**: Chaos engineering tool to inject machine/scheduler failures
- **Behavior**:
  - Randomly kills cutting machines and schedulers (Docker containers)
  - Restarts them after 10-30 seconds
  - Controlled by scenario parameters (e.g., max 2 machines killed simultaneously)
- **Purpose**: Simulate real-world failures to measure latency under stress

### **8. Kafka Collector** (`kafkaCollector/`)
- **Role**: Records all Kafka messages during experiments
- **Output**: JSONL files (`heartbeats.jsonl`, `productionPlan.jsonl`, `storageAlerts.jsonl`, `storageLevels.jsonl`)
- **Usage**: Feeds data to Latency Analyzer for post-experiment analysis

### **9. Latency Analyzer** (`latency_analyzer/`)
- **Role**: Post-experiment analysis tool
- **Process**:
  1. Reads JSONL files from Kafka Collector
  2. Correlates messages into complete events (trigger → reaction → resolution)
  3. Calculates latencies and exports results
- **Output**: `events.csv`, `summary.txt`

---

## Measured Events & Latency Calculation

### **Event 1: New Machine (`newMachine`)**
- **Trigger** (`trigger_ts`): First heartbeat without `bladeType` (machine waiting for assignment)
- **Reaction** (`reaction_ts`): Scheduler sends `AssignBlade` message
- **Solved** (`solved_ts`): First heartbeat with the assigned `bladeType`
- **Latencies**:
  - `scheduler_latency`: reaction_ts - trigger_ts (detection time)
  - `machine_latency`: solved_ts - reaction_ts (machine assignment time)
  - `total_latency`: solved_ts - trigger_ts (end-to-end)

### **Event 2: Machine Failure (`machineFailure`)**
- **Trigger** (`trigger_ts`): Last heartbeat before ≥10s gap
- **Reaction** (`reaction_ts`): Scheduler sends `SwapBlade` to another machine
- **Solved** (`solved_ts`): Target machine sends heartbeat with new `bladeType`
- **Latencies**: Same structure as above

### **Event 3: Storage Alert (`storageAlert`)**
- **Trigger** (`trigger_ts`): DB Interface detects storage level < 20% or > 80%
- **Reaction** (`reaction_ts`): Scheduler sends:
  - `SwapBlade` (if blade type A/B is low)
  - `ChangeFreshAmount` (if fresh/dry is imbalanced)
- **Solved** (`solved_ts`):
  - For blade swaps: Machine heartbeat with new `bladeType`
  - For fresh amount changes: Sorting Subsystem sends `FreshAmountChanged`
- **Latencies**: Same structure as above

---

## Experiment Scenarios

Scenarios test how latency changes with different chaos injection levels:

| Scenario | Machines | Max Machines Killed | Max Schedulers Killed |
|----------|----------|---------------------|-----------------------|
| `5m_1k`  | 5        | 1                   | 1                     |
| `5m_2k`  | 5        | 2                   | 1                     |
| `5m_3k`  | 5        | 3                   | 1                     |
| `5m_4k`  | 5        | 4                   | 1                     |
| `3m_1k`  | 3        | 1                   | 1                     |
| `3m_2k`  | 3        | 2                   | 1                     |

**Format**: `{#machines}m_{#max_kills}k`

---

## Results Analysis (`analysis_outputs/`)

### **1. Event Counts** (`counts_by_scenario_eventtype.csv`)
- Shows how many events of each type occurred per scenario
- Example: `5m_2k` had 79 newMachine, 11 machineFailure, 3 storageAlert events

### **2. Latency Summary** (`latency_summary.txt`)
- **Global statistics** across all scenarios:
  - Average scheduler latency: ~5.4 seconds
  - Average machine latency: ~3.4 seconds
  - Average total latency: ~8.8 seconds
- **Per-event breakdowns** showing detection vs. resolution times

### **3. Mean Latency Tables** 
- `mean_table_seconds.csv`: Average total response time (in seconds) per event type per scenario
- Key insight: machineFailure events take longest in high-chaos scenarios (e.g., 11.3s for `3m_2k`)

### **4. Percentile Analysis** (`summary_by_scenario_eventtype.csv`)
- Includes median, quartiles (Q25/Q75), standard deviation
- Helps identify latency variability under different chaos levels

---

## Key Insights

1. **Chaos increases latency**: More simultaneous failures → longer detection and recovery times
2. **Machine failures are slowest**: Require detecting absence + coordinating replacement
3. **Storage alerts are fastest**: Direct trigger-reaction path with minimal coordination
4. **Scheduler latency dominates**: Detection time (trigger → reaction) is typically longer than resolution time (reaction → solved)