"""
Event data structures and enums for experiment analysis
"""

from dataclasses import dataclass, asdict
from enum import Enum
from typing import Optional
import json


class EventType(Enum):
    """Types of events in the experiment"""
    STORAGE_ALERT = "storageAlert"
    MACHINE_FAILURE = "machineFailure"
    NEW_MACHINE = "newMachine"


class ReactionType(Enum):
    """Types of reactions from the scheduler"""
    CHANGE_FRESH_AMOUNT = "ChangeFreshAmount"
    SWAP_BLADE = "SwapBlade"
    ASSIGN_BLADE = "AssignBlade"
    NONE = "none"


@dataclass
class Event:
    """Represents a solved event from the experiment"""
    
    event_id: str                              # Unique event identifier
    event_type: str                            # storageAlert, machineFailure, newMachine
    trigger_ts: int                            # When the event was triggered (ms)
    trigger_source: str                        # Where trigger originated (dbInterface, scheduler, machine)
    reaction_ts: Optional[int]                 # When scheduler reacted (ms) or None
    reaction_type: str                         # What scheduler sent (ChangeFreshAmount, SwapBlade, AssignBlade, none)
    solved_ts: Optional[int]                   # When event was solved (ms) or None
    related_machine_id: Optional[int]          # Machine involved (for failure/new events)
    related_alert_id: Optional[str]            # Alert ID (for storage events)
    resolution_time_ms: Optional[int]          # trigger_ts → reaction_ts (detection latency)
    total_response_time_ms: Optional[int]      # trigger_ts → solved_ts (full latency)
    metadata: str                              # JSON string with additional context
    
    def to_csv_row(self):
        """Convert event to CSV row values"""
        return [
            self.event_id,
            self.event_type,
            self.trigger_ts,
            self.trigger_source,
            self.reaction_ts if self.reaction_ts else "",
            self.reaction_type,
            self.solved_ts if self.solved_ts else "",
            self.related_machine_id if self.related_machine_id else "",
            self.related_alert_id if self.related_alert_id else "",
            self.resolution_time_ms if self.resolution_time_ms else "",
            self.total_response_time_ms if self.total_response_time_ms else "",
            self.metadata
        ]
    
    @staticmethod
    def csv_header():
        """CSV header row"""
        return [
            "event_id",
            "event_type",
            "trigger_ts",
            "trigger_source",
            "reaction_ts",
            "reaction_type",
            "solved_ts",
            "related_machine_id",
            "related_alert_id",
            "resolution_time_ms",
            "total_response_time_ms",
            "metadata"
        ]


@dataclass
class StorageAlertTrigger:
    """Trigger data for storage alert events"""
    alert_id: str
    trigger_ts: int
    problem_category: str
    a_fresh: float
    a_dry: float
    b_fresh: float
    b_dry: float


@dataclass
class MachineFailureTrigger:
    """Trigger data for machine failure events"""
    machine_id: int
    trigger_ts: int  # When health check detected failure
    failed_blade_type: str


@dataclass
class NewMachineTrigger:
    """Trigger data for new machine discovery events"""
    machine_id: int
    trigger_ts: int  # When first heartbeat without blade received
    

@dataclass
class Reaction:
    """Scheduler reaction to an event"""
    reaction_ts: int
    reaction_type: str
    command_json: dict  # The actual command message


@dataclass
class Resolution:
    """Resolution of an event"""
    solved_ts: int
    resolution_type: str  # heartbeat_with_blade, state_change, etc.
    evidence: dict  # Supporting evidence from logs