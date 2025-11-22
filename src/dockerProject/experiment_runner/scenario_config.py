"""
Experiment scenario configuration
"""

from dataclasses import dataclass
from typing import List


@dataclass
class Scenario:
    """Represents an experiment scenario"""
    
    id: str                              # Unique scenario identifier (e.g., "3m_0k")
    num_cutting_machines: int            # Number of cutting machines (3 or 5)
    max_killable_machines: int           # Max concurrent machines to kill (0-4)
    max_killable_schedulers: int         # Max concurrent schedulers to kill (always 1)
    description: str                     # Human readable description


def get_all_scenarios() -> List[Scenario]:
    """
    Get all experiment scenarios.
    
    Returns:
        List of 8 scenarios (3 machines: 3 scenarios, 5 machines: 5 scenarios)
    """
    scenarios = [
        # 3 cutting machines
        Scenario(
            id="3m_0k",
            num_cutting_machines=3,
            max_killable_machines=0,
            max_killable_schedulers=1,
            description="3 machines, no chaos (baseline)"
        ),"""
        Scenario(
            id="3m_1k",
            num_cutting_machines=3,
            max_killable_machines=1,
            max_killable_schedulers=1,
            description="3 machines, max 1 killed"
        ),
        Scenario(
            id="3m_2k",
            num_cutting_machines=3,
            max_killable_machines=2,
            max_killable_schedulers=1,
            description="3 machines, max 2 killed"
        ),
        
        # 5 cutting machines
        Scenario(
            id="5m_0k",
            num_cutting_machines=5,
            max_killable_machines=0,
            max_killable_schedulers=1,
            description="5 machines, no chaos (baseline)"
        ),
        Scenario(
            id="5m_1k",
            num_cutting_machines=5,
            max_killable_machines=1,
            max_killable_schedulers=1,
            description="5 machines, max 1 killed"
        ),
        Scenario(
            id="5m_2k",
            num_cutting_machines=5,
            max_killable_machines=2,
            max_killable_schedulers=1,
            description="5 machines, max 2 killed"
        ),
        Scenario(
            id="5m_3k",
            num_cutting_machines=5,
            max_killable_machines=3,
            max_killable_schedulers=1,
            description="5 machines, max 3 killed"
        ),
        Scenario(
            id="5m_4k",
            num_cutting_machines=5,
            max_killable_machines=4,
            max_killable_schedulers=1,
            description="5 machines, max 4 killed"
        )"""
    ]
    
    return scenarios