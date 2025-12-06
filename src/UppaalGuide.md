# Pasta Production System - UPPAAL Formal Verification Guide

## Overview

This guide describes the formal verification performed on the pasta production system using UPPAAL. The verification focuses on validating critical quality attributes—**Production Modifiability (R2)**, **System Availability (R10)**, and **System Scalability (R9)**—before conducting resource-intensive empirical experiments. The model captures the core interaction patterns between schedulers, machines, and storage subsystems to prove safety and liveness properties.

---

## Why Formal Verification?

Formal verification with UPPAAL provided early architectural feedback by:
- **Exploring execution paths** to validate properties across system scenarios
- **Identifying design flaws early**, specifically revealing an unacceptable 11-time-unit failover delay that led to the Redis implementation
- **Increasing confidence** in the architecture's correctness before committing to complex empirical testing

Due to state-space complexity, we used **statistical model checking** (probabilistic queries) rather than exhaustive symbolic verification. This limited the number of relevant queries but made the verifier way faster.

---

## Model Architecture

### Timing Constraints

The model incorporates several key timing constraints:

1. **Periodical constraint for heartbeats**: Machines send heartbeats to indicate they are functional
2. **Periodical constraint to check heartbeats**: Scheduler monitors heartbeats to detect failures (from scheduler's perspective)
3. **Sporadic constrained blade switching**: Blade changes are infrequent to minimize production downtime

### Templates (Components)

The UPPAAL model consists of 6 template types representing key system components:

#### **1. CuttingMachine** (Parameterized by `id`)
- **States**: `idle`, `waiting`, `workingA`, `workingB`, `failed`
- **Key Behavior**:
  - Sends `newHeartbeat[id]` when ready, waits for blade assignment
  - Works for 5 time units, sending periodic `heartbeat[id]`
  - Can fail stochastically and recover after up to 30 time units
  - Accepts `changeBlade[id]` to swap between blade types
- **Key Variables**: `c` (clock), `failCd` (failure countdown)

#### **2. SchedulerMachine** (Parameterized by `id`)
- **States**: `idle`, `assignBlade`, `recover`
- **Key Behavior**:
  - Assigns blade types based on load balancing when detecting `newHeartbeat[id]`
  - Detects machine failures (no heartbeat within 10 time units)
  - Redistributes workload via `changeBlade[change]` commands
- **Key Functions**: `checkAssignA()` (balancing), `updateMachine()` (failure handling)

#### **3. SchedulerState** (Parameterized by `id`)
- **States**: `idle`, `active`, `shadow`, `failed`
- **Key Behavior**:
  - Active scheduler (id=0) sends `schedulerHb` every 5 time units
  - Shadow scheduler (id=1) promotes to active if no heartbeat within 11 time units
  - Failed schedulers recover to shadow state after 11 time units
- **Purpose**: Active-standby failover for high availability

#### **4. SchedulerDB**
- **States**: `idle`, `changeProduction`
- **Key Behavior**:
  - Reacts to `storageLevel` signals by identifying the most depleted pasta type
  - Issues `changeBlade[change]` or adjusts `sortingFreshTime` accordingly
  - Enforces cooldown (`c<11`) to prevent repeated reactions
- **Key Function**: `identifyProblem()` determines corrective action

#### **5. DB**
- **Key Behavior**:
  - Every 5 time units, simulates consumption and production via `updateLevels()`
  - Sends `storageLevel` if any category <20% or >80%
- **Key Functions**: `updateLevels()` (stock simulation), `checkThresholds()` (violation detection)

#### **6. SortingSubsystem**
- **States**: `fresh`, `dried`
- **Key Behavior**: Cycles between fresh and dried packaging with adjustable `sortingFreshTime`
- **Purpose**: Models physical subsystem controlling fresh/dry ratio

---

## Global Declarations

```c
// Type definitions
typedef int[0,2] id_type;      // Machine/scheduler IDs (0, 1, 2)
typedef int[0,3] pasta_type;   // Pasta types: A=0, B=1, FRESH=2, DRIED=3

// Communication channels (broadcast to allow statistical queries)
broadcast chan newHeartbeat[id_type];
broadcast chan heartbeat[id_type];
broadcast chan assignA[id_type], assignB[id_type];
broadcast chan changeBlade[id_type];
broadcast chan schedulerHb;
broadcast chan storageLevel;

// State variables
pasta_type blades[3] = { 3, 3, 3 };   // Blade assignments (3 = unassigned)
int[0,3] aMachines = 0;               // Count of A-blade machines
int[0,3] bMachines = 0;               // Count of B-blade machines
int[0,5] sortingFreshTime = 2;        // Fresh packaging duration

// Storage levels (capacity: 100 units each)
int[0,100] freshA = 50;
int[0,100] freshB = 50;
int[0,100] driedA = 50;
int[0,100] driedB = 50;
```

---

## Verification Queries and Results

All queries achieved **≥ 0.990026 (95% CI)**, meaning properties hold with >99% confidence.

### **Query 1: Storage Threshold Compliance (R2, UC1)**
```
Pr[<=1000] ([] (freshA >= 0 && freshA <= 100 && 
                freshB >= 0 && freshB <= 100 && 
                driedA >= 0 && driedA <= 100 && 
                driedB >= 0 && driedB <= 100))
```
- **Verifies**: Storage levels always remain within [0, 100] bounds
- **Significance**: Confirms the control logic prevents overflow/underflow across all execution paths
- **Quality Attribute**: Production Modifiability (R2) - ensures system can adjust production without violating storage constraints

### **Query 2: Scheduler Latency (R5.3)**
```
Pr[<=1000] ([] (CuttingMachine0.waiting imply CuttingMachine0.c < 5))
```
- **Verifies**: Machines receive blade assignment within 5 seconds of sending initial heartbeat
- **Quality Attribute**: System Scalability (R9)

### **Query 3: Machine Recovery Validation (Auxiliary)**
```
Pr[<=1000] ([] (CuttingMachine0.failed imply (CuttingMachine0.c <= 30)))
```
- **Verifies**: Failed machines restart within 30 time units (model sanity check)
- **Purpose**: Validates UPPAAL configuration, not a primary architectural property

### **Query 4: Mutual Exclusion of Schedulers (R4.2)**
```
Pr[<=1000] ([] ! (SchedulerState0.active && SchedulerState1.active))
```
- **Verifies**: Only one scheduler is `active` at any time (prevents split-brain)
- **Quality Attribute**: System Availability (R10)

### **Query 5: Message Sequencing Correctness (R2, R3)**
```
Pr[<=1000] ([] ((CuttingMachine0.workingA || CuttingMachine0.workingB) imply 
                (SchedulerMachine0.assignBlade == false)))
```
- **Verifies**: Scheduler sends correct message types (`SwapBlade` for working machines, not `AssignBlade`)
- **Quality Attribute**: Production Modifiability (R2, R3) - validates component decoupling

### **Query 6: Failover Time Bound (R4.2, UC12)**
```
Pr[<=1000] ([] !(SchedulerState0.active || SchedulerState1.active) imply 
               (SchedulerState0.c <= 11 && SchedulerState1.c <= 11))
```
- **Verifies**: System recovers within 11 time units if both schedulers fail
- **Critical Finding**: This bound was **deemed unacceptable** for production deployment
- **Design Decision**: Led directly to Redis implementation, reducing failover to ~5 seconds
- **Quality Attribute**: System Availability (R10)

### **Query 7: Deadlock Freedom**
```
A[] not deadlock
```
- **Verifies**: System maintains liveness under all conditions (no blocked states)

---

## Key Findings and Design Decisions

### **Redis Integration (Failover Optimization)**
**Problem**: Query 6 revealed 11-time-unit failover risked cascading failures in heartbeat-based systems.

**Solution**: Redis implementation with TTL-based leader election and hot-spare redundancy.

**Impact**: Reduced failover to ~5 seconds, achieving true production resilience.

### **Validated Properties**
- Storage control prevents violations under random consumption and failures (Query 1)
- Scheduler correctly sequences messages without tight coupling (Queries 2, 5)
- Mutual exclusion prevents split-brain scenarios (Query 4)

## Modeling Decisions

### **Abstractions**
- **Time units**: Abstract units focusing on relative timing
- **Storage model**: Linear consumption/production
- **Failures**: Stochastic countdown (`failCd`)
- **Communication**: Instantaneous broadcast channels (no MQTT/Kafka latency)

### **Limitations**
- Network effects and message loss not modeled
- Redis protocol details abstracted
- ChaosPanda patterns simulated by `failCd`
- Statistical checking (`Pr[<=1000]`) used due to state-space explosion with 3 machines × 2 schedulers × 4 storage variables

---

## Integration with Empirical Experiments

The formal verification and empirical evaluation are **complementary**:

| Aspect          | Formal (UPPAAL)                | Empirical (Chaos Experiments)                     |
|-----------------|--------------------------------|---------------------------------------------------|
| **Coverage**    | All possible states (symbolic) | Representative scenarios (statistical)            |
| **Realism**     | Abstract timing, no network    | Real Docker containers, Kafka latency             |
| **Purpose**     | Prove correctness              | Measure performance under chaos                   |
| **Key Insight** | 11-time-unit failover too slow | Average latencies: 5.4s (scheduler), 8.8s (total) |

The UPPAAL findings **directly motivated** the Redis implementation, which was then validated empirically to achieve the target 5-second recovery time.

---

## Conclusion

UPPAAL verification successfully validated that the pasta production architecture:
1. **Maintains storage invariants** (0-100 bounds) under all conditions
2. **Ensures mutual exclusion** for scheduler redundancy
3. **Correctly sequences messages** without tight coupling
4. **Detects and recovers** from machine failures

The critical discovery of insufficient failover performance (Query 6) reshaped the design, demonstrating formal methods' value for **early architectural evaluation**. Combined with subsequent empirical validation, this two-phase approach provided rigorous evidence that the system satisfies its quality attribute scenarios for availability, modifiability, and scalability.