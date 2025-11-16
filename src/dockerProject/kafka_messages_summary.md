# Kafka Messages Summary

## Overview
This document describes all messages sent across the Kafka bus in the Pasta Production System.

---

## Messages

### CuttingMachine → heartbeats
Sent every 5 seconds by each cutting machine to report its operational status.

**During initialization (waiting for blade assignment):**
```json
{
  "title": "heartbeat",
  "machineId": ""
}
```

**During operation (after blade assignment):**
```json
{
  "title": "heartbeat",
  "machineId": "",
  "bladeType": ""
}
```

---

### CuttingMachine → productionPlan
Sent by a cutting machine when responding to scheduler commands.

**Report completion of blade swap operation:**
```json
{
  "title": "BladeSwapped",
  "machineId": ""
}
```

---

### SimulationEngine (BatchManager) → heartbeats
Consumed from heartbeats topic to trigger batch creation.

---

### SimulationEngine (BatchManager) → productionPlan
Consumed from productionPlan topic to track freshAmount updates.

---

### SimulationEngine (DbInterface) → storageLevels
Sent when storage levels breach thresholds (<20% or >80%).

```json
{
  "title": "StorageAlert",
  "aFresh": "",
  "aDry": "",
  "bFresh": "",
  "bDry": ""
}
```

---

### SimulationEngine (BatchManager) → batches
Sent when new batches are created (for monitoring purposes).

```json
{
  "title": "NewBatch",
  "bladeType": "",
  "freshness": ""
}
```

---

### Scheduler → productionPlan
Sent by the scheduler in response to machine discovery, health monitoring, and storage alerts.

**Assign blade to newly discovered machine without blade type:**
```json
{
  "title": "AssignBlade",
  "machineId": "",
  "bladeType": ""
}
```

**Swap blade on existing machine when another fails:**
```json
{
  "title": "SwapBlade",
  "machineId": "",
  "bladeType": ""
}
```

**Change fresh pasta production amount:**
```json
{
  "title": "ChangeFreshAmount",
  "freshAmount": ""
}
```

---

### Scheduler → storageLevels
Consumed from storageLevels topic to react to storage alert conditions.

---

### SortingSubsystem → productionPlan
Consumed from productionPlan topic (ChangeFreshAmount messages).

**Confirm fresh amount change:**
```json
{
  "title": "FreshAmountChanged",
  "freshAmount": ""
}
```

---

## Topics Summary

| Topic | Producers | Consumers | Purpose |
|-------|-----------|-----------|---------|
| `heartbeats` | CuttingMachine | Scheduler, BatchManager, KafkaMonitor | Machine health monitoring and batch creation |
| `productionPlan` | Scheduler, SortingSubsystem | CuttingMachine, BatchManager, KafkaMonitor | Production directives, alerts, and fresh amount tracking |
| `storageLevels` | DbInterface | Scheduler, KafkaMonitor | Storage level monitoring and alerts |

---

## Message Flow

### Initialization & Machine Assignment
1. CuttingMachine starts → sends heartbeat without bladeType
2. Scheduler receives heartbeat → sends AssignBlade message
3. CuttingMachine receives AssignBlade → transitions to WORKING state
4. CuttingMachine heartbeats now include bladeType

### Batch Production
1. CuttingMachine sends heartbeat (with bladeType)
2. BatchManager receives heartbeat → creates fresh and dry batches
3. BatchManager balances stock to maintain total of 200

### Fresh Amount Control
1. Scheduler receives StorageAlert from DbInterface
2. If fresh/dry imbalance detected → Scheduler sends ChangeFreshAmount
3. SortingSubsystem receives ChangeFreshAmount → updates freshAmount
4. SortingSubsystem sends FreshAmountChanged confirmation
5. BatchManager reads ChangeFreshAmount → updates local freshAmount
6. Next batch production uses updated freshAmount

### Machine Failure Recovery
1. Scheduler detects missing heartbeat (>10 seconds)
2. Scheduler identifies machine with opposite blade type
3. Scheduler sends SwapBlade message
4. CuttingMachine sleeps 2 seconds, updates blade type
5. CuttingMachine sends BladeSwapped confirmation
6. Next heartbeat shows new blade type

### Scheduler Failover
1. Active scheduler loses Redis lease after 5 seconds
2. Shadow scheduler acquires active status
3. Shadow scheduler loads machine state from Redis
4. Shadow scheduler resumes operations (no duplicate AssignBlade for existing machines with blade types)

---

## Notes
- All timestamps are in ISO 8601 format
- Machine IDs are integers (0, 1, 2, etc.)
- Blade types are either "A" or "B"
- Freshness values are either "fresh" or "dry"
- Storage levels are percentages (0-100)
- Fresh amount is between 0 and 10 (determines fresh vs dry split in batches)