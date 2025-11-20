"""
Machine state management for cutting machines
"""

from enum import Enum
import threading
from typing import Optional


class OperationalState(Enum):
    """Machine operational states"""
    INITIALIZING = "INITIALIZING"
    WAITING_FOR_ASSIGNMENT = "WAITING_FOR_ASSIGNMENT"
    WORKING = "WORKING"
    RECOVERY = "RECOVERY"


class MachineState:
    """Manages the operational state of a cutting machine"""

    def __init__(self):
        """Initialize machine state"""
        self._state = OperationalState.INITIALIZING
        self._blade_type: Optional[str] = None
        self._recovery_end_time: float = 0
        self._lock = threading.Lock()

    def get_state(self) -> OperationalState:
        """Get current operational state"""
        with self._lock:
            return self._state

    def set_state(self, new_state: OperationalState) -> None:
        """Set operational state"""
        with self._lock:
            self._state = new_state

    def get_blade_type(self) -> Optional[str]:
        """Get current blade type"""
        with self._lock:
            return self._blade_type

    def set_blade_type(self, blade_type: str) -> None:
        """Set blade type"""
        with self._lock:
            self._blade_type = blade_type

    def assign_blade(self, blade_type: str) -> None:
        """Assign blade and transition to WORKING state"""
        with self._lock:
            self._blade_type = blade_type
            self._state = OperationalState.WORKING

    def swap_blade(self, new_blade_type: str) -> tuple:
        """Swap blade and return old and new types"""
        with self._lock:
            old_blade_type = self._blade_type
            self._blade_type = new_blade_type
            return old_blade_type, new_blade_type

    def enter_recovery(self, recovery_seconds: int) -> None:
        """Enter recovery mode for specified seconds"""
        with self._lock:
            import time
            self._recovery_end_time = time.time() + recovery_seconds

    def is_in_recovery(self) -> bool:
        """Check if machine is in recovery mode"""
        with self._lock:
            import time
            if self._recovery_end_time > 0:
                if time.time() < self._recovery_end_time:
                    return True
                else:
                    self._recovery_end_time = 0
                    return False
            return False

    def exit_recovery(self) -> None:
        """Exit recovery mode"""
        with self._lock:
            self._recovery_end_time = 0

    def is_working(self) -> bool:
        """Check if machine is in working state with blade assigned"""
        with self._lock:
            return self._state == OperationalState.WORKING and self._blade_type is not None

    def is_waiting_for_assignment(self) -> bool:
        """Check if machine is waiting for blade assignment"""
        with self._lock:
            return self._state == OperationalState.WAITING_FOR_ASSIGNMENT