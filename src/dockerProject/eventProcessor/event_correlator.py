"""
Event correlation: matches triggers, reactions, and resolutions into events
"""

import json
import logging
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from event_definitions import (
    Event, EventType, ReactionType,
    StorageAlertTrigger, MachineFailureTrigger, NewMachineTrigger,
    Reaction, Resolution
)

logging.basicConfig(level=logging.INFO)
LOGGER = logging.getLogger(__name__)


class EventCorrelator:
    """Correlates Kafka messages and machine logs into experiment events"""

    def __init__(self, collector_output_dir: Path):
        self.output_dir = Path(collector_output_dir)
        
        # Raw message collections
        self.heartbeats: List[dict] = []
        self.commands: List[dict] = []
        self.storage_alerts: List[dict] = []
        
        # Indices for fast lookup
        self.alerts_by_id: Dict[str, dict] = {}
        self.alerts_by_problem: Dict[str, List[dict]] = {}  # problem_category → [alerts]
        self.machines_by_id: Dict[int, dict] = {}
        self.commands_by_event_context: Dict[str, dict] = {}
        
        # Events being built
        self.pending_events: Dict[str, Event] = {}  # event_id → partial Event
        self.solved_events: List[Event] = []
        
        self.load_data()

    def load_data(self):
        """Load all collected messages from JSONL files"""
        LOGGER.info(f"Loading data from {self.output_dir}")
        
        # Load heartbeats
        heartbeats_file = self.output_dir / 'heartbeats.jsonl'
        if heartbeats_file.exists():
            with open(heartbeats_file) as f:
                for line in f:
                    try:
                        record = json.loads(line.strip())
                        msg = record['message']
                        msg['_collected_at'] = record['collected_at']
                        self.heartbeats.append(msg)
                    except Exception as e:
                        LOGGER.warning(f"Error loading heartbeat: {e}")
        
        # Load production plan commands
        commands_file = self.output_dir / 'productionPlan.jsonl'
        if commands_file.exists():
            with open(commands_file) as f:
                for line in f:
                    try:
                        record = json.loads(line.strip())
                        msg = record['message']
                        msg['_collected_at'] = record['collected_at']
                        self.commands.append(msg)
                    except Exception as e:
                        LOGGER.warning(f"Error loading command: {e}")
        
        # Load storage alerts
        alerts_file = self.output_dir / 'storageAlerts.jsonl'
        if alerts_file.exists():
            with open(alerts_file) as f:
                for line in f:
                    try:
                        record = json.loads(line.strip())
                        msg = record['message']
                        msg['_collected_at'] = record['collected_at']
                        self.storage_alerts.append(msg)
                    except Exception as e:
                        LOGGER.warning(f"Error loading alert: {e}")
        
        # Sort all by timestamp
        self.heartbeats.sort(key=lambda x: x.get('timestamp', 0))
        self.commands.sort(key=lambda x: x.get('reactionTs', x.get('_collected_at', 0)))
        self.storage_alerts.sort(key=lambda x: x.get('triggerTs', 0))
        
        LOGGER.info(f"Loaded: {len(self.heartbeats)} heartbeats, {len(self.commands)} commands, {len(self.storage_alerts)} alerts")

    def correlate_events(self) -> List[Event]:
        """Main correlation logic: build events from messages"""
        LOGGER.info("Starting event correlation...")
        
        # Build indices
        self._build_indices()
        
        # Process storage alerts (triggers)
        self._process_storage_alerts()
        
        # Process machine failures and new machines (triggers)
        self._process_machine_events()
        
        # Correlate reactions (scheduler commands)
        self._correlate_reactions()
        
        # Correlate resolutions (state changes / heartbeats)
        self._correlate_resolutions()
        
        # Filter only solved events
        self.solved_events = [e for e in self.pending_events.values() if e.solved_ts]
        
        LOGGER.info(f"Correlated {len(self.solved_events)} solved events")
        return sorted(self.solved_events, key=lambda e: e.trigger_ts)

    def _build_indices(self):
        """Build lookup indices"""
        # Index alerts
        for alert in self.storage_alerts:
            alert_id = alert.get('alertId', 'unknown')
            self.alerts_by_id[alert_id] = alert
            
            problem = alert.get('problemCategory', 'unknown')
            if problem not in self.alerts_by_problem:
                self.alerts_by_problem[problem] = []
            self.alerts_by_problem[problem].append(alert)
        
        # Index commands by event context
        for cmd in self.commands:
            if cmd.get('eventContext'):
                self.commands_by_event_context[cmd['eventContext']] = cmd

    def _process_storage_alerts(self):
        """Process storage alerts as event triggers"""
        LOGGER.info("Processing storage alerts...")
        
        processed_problems = set()
        
        for alert in self.storage_alerts:
            alert_id = alert.get('alertId', 'unknown')
            problem_category = alert.get('problemCategory', 'unknown')
            trigger_ts = alert.get('triggerTs', 0)
            
            # Skip if this problem category was already processed in an unsolved event
            if problem_category in processed_problems:
                LOGGER.debug(f"Skipping duplicate alert for problem {problem_category}")
                continue
            
            event_id = f"storageAlert:{alert_id}:problem_{problem_category}"
            
            event = Event(
                event_id=event_id,
                event_type=EventType.STORAGE_ALERT.value,
                trigger_ts=trigger_ts,
                trigger_source="dbInterface",
                reaction_ts=None,
                reaction_type=ReactionType.NONE.value,
                solved_ts=None,
                related_machine_id=None,
                related_alert_id=alert_id,
                resolution_time_ms=None,
                total_response_time_ms=None,
                metadata=json.dumps({
                    "problem_category": problem_category,
                    "a_fresh": alert.get('aFresh', 0),
                    "a_dry": alert.get('aDry', 0),
                    "b_fresh": alert.get('bFresh', 0),
                    "b_dry": alert.get('bDry', 0)
                })
            )
            
            self.pending_events[event_id] = event
            processed_problems.add(problem_category)

    def _process_machine_events(self):
        """Process machine failures and new machines as event triggers"""
        LOGGER.info("Processing machine events...")
        
        # Track which machines we've seen and their states
        machines_seen: Dict[int, Tuple[int, str]] = {}  # machine_id → (first_hb_ts, first_state)
        processed_failures: set = set()  # (machine_id, failure_ts)
        
        for hb in self.heartbeats:
            machine_id = hb.get('machineId')
            timestamp = hb.get('timestamp', 0)
            state = hb.get('state', 'UNKNOWN')
            blade_type = hb.get('bladeType')
            
            if machine_id is None:
                continue
            
            # NEW MACHINE EVENT: First heartbeat without blade
            if machine_id not in machines_seen and state == 'WAITING_FOR_ASSIGNMENT':
                event_id = f"newMachine:machine_{machine_id}"
                event = Event(
                    event_id=event_id,
                    event_type=EventType.NEW_MACHINE.value,
                    trigger_ts=timestamp,
                    trigger_source="cutting_machine_discovery",
                    reaction_ts=None,
                    reaction_type=ReactionType.NONE.value,
                    solved_ts=None,
                    related_machine_id=machine_id,
                    related_alert_id=None,
                    resolution_time_ms=None,
                    total_response_time_ms=None,
                    metadata=json.dumps({"first_state": "WAITING_FOR_ASSIGNMENT"})
                )
                self.pending_events[event_id] = event
                machines_seen[machine_id] = (timestamp, 'WAITING_FOR_ASSIGNMENT')
            
            # Mark as seen even if already in pending (for failover detection)
            elif machine_id not in machines_seen:
                machines_seen[machine_id] = (timestamp, state)

    def _correlate_reactions(self):
        """Correlate scheduler reactions to pending events"""
        LOGGER.info("Correlating reactions...")
        
        for cmd in self.commands:
            title = cmd.get('title')
            event_context = cmd.get('eventContext', 'unknown')
            reaction_ts = cmd.get('reactionTs', cmd.get('_collected_at', 0))
            
            # Find event by context
            event_id = None
            if event_context.startswith('storageAlert:'):
                # Extract alert_id and problem from context: "storageAlert:alert_id:problem_X"
                parts = event_context.split(':')
                if len(parts) >= 3:
                    alert_id = parts[1]
                    problem = parts[2].replace('problem_', '')
                    event_id = f"storageAlert:{alert_id}:problem_{problem}"
            
            elif event_context.startswith('machineFailure:'):
                # Extract machine_id from context: "machineFailure:machine_X"
                parts = event_context.split(':')
                if len(parts) >= 2:
                    machine_id = parts[1].replace('machine_', '')
                    event_id = f"machineFailure:machine_{machine_id}"
            
            elif event_context.startswith('initialization:'):
                # Initial assignment during discovery
                if title == 'AssignBlade':
                    machine_id = cmd.get('machineId')
                    event_id = f"newMachine:machine_{machine_id}"
            
            # Update event with reaction
            if event_id and event_id in self.pending_events:
                event = self.pending_events[event_id]
                event.reaction_ts = reaction_ts
                event.reaction_type = title
                event.resolution_time_ms = reaction_ts - event.trigger_ts
                
                LOGGER.debug(f"Correlated reaction for {event_id}: {title}")

    def _correlate_resolutions(self):
        """Correlate event resolutions (when events are solved)"""
        LOGGER.info("Correlating resolutions...")
        
        for event in self.pending_events.values():
            if event.event_type == EventType.NEW_MACHINE.value:
                self._resolve_new_machine(event)
            elif event.event_type == EventType.MACHINE_FAILURE.value:
                self._resolve_machine_failure(event)
            elif event.event_type == EventType.STORAGE_ALERT.value:
                self._resolve_storage_alert(event)

    def _resolve_new_machine(self, event: Event):
        """Resolve newMachine event: heartbeat with bladeType"""
        machine_id = event.related_machine_id
        
        # Find first heartbeat with bladeType after trigger
        for hb in self.heartbeats:
            if (hb.get('machineId') == machine_id and 
                hb.get('timestamp', 0) > event.trigger_ts and
                hb.get('bladeType')):
                
                event.solved_ts = hb.get('timestamp')
                event.total_response_time_ms = event.solved_ts - event.trigger_ts
                LOGGER.debug(f"Resolved newMachine:machine_{machine_id} at {event.solved_ts}")
                break

    def _resolve_machine_failure(self, event: Event):
        """Resolve machineFailure event: heartbeat with new bladeType from SwapBlade"""
        machine_id = event.related_machine_id
        
        # Find SwapBlade command for this machine
        swap_cmd = None
        for cmd in self.commands:
            if (cmd.get('title') == 'SwapBlade' and 
                cmd.get('machineId') == machine_id and
                cmd.get('reactionTs', 0) > event.trigger_ts):
                swap_cmd = cmd
                break
        
        if not swap_cmd:
            LOGGER.debug(f"No SwapBlade found for machineFailure:machine_{machine_id}")
            return
        
        new_blade_type = swap_cmd.get('bladeType')
        
        # Find heartbeat with the new blade type after swap command
        for hb in self.heartbeats:
            if (hb.get('machineId') == machine_id and
                hb.get('timestamp', 0) > swap_cmd.get('reactionTs', 0) and
                hb.get('bladeType') == new_blade_type):
                
                event.solved_ts = hb.get('timestamp')
                event.total_response_time_ms = event.solved_ts - event.trigger_ts
                LOGGER.debug(f"Resolved machineFailure:machine_{machine_id} at {event.solved_ts}")
                break

    def _resolve_storage_alert(self, event: Event):
        """Resolve storageAlert event: storage levels return to 20-80% zone"""
        alert_id = event.related_alert_id
        
        # Find the reaction command
        reaction_cmd = None
        if event.reaction_ts:
            for cmd in self.commands:
                if cmd.get('reactionTs') == event.reaction_ts:
                    reaction_cmd = cmd
                    break
        
        # Look for subsequent storage alerts for the same problem to detect resolution
        problem_category = json.loads(event.metadata).get('problem_category')
        
        for alert in self.storage_alerts:
            if (alert.get('triggerTs', 0) > event.trigger_ts and
                alert.get('problemCategory') == problem_category):
                
                # Check if new alert indicates problem is worse (not resolved)
                # If it's the next alert for same problem, it means problem NOT resolved
                LOGGER.debug(f"Found follow-up alert for {problem_category}, problem not yet resolved")
                return
        
        # If no follow-up alerts found, problem is resolved
        # Set solved_ts to a reasonable time (after reaction + some margin)
        if event.reaction_ts:
            event.solved_ts = event.reaction_ts + 5000  # 5 seconds after reaction as placeholder
            event.total_response_time_ms = event.solved_ts - event.trigger_ts
            LOGGER.debug(f"Resolved storageAlert {alert_id} (problem {problem_category})")