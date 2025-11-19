"""
Message handling for cutting machine commands
"""

import logging
import json
from typing import Callable, Optional
from state import MachineState

LOGGER = logging.getLogger(__name__)


class MessageHandler:
    """Handles incoming MQTT messages and executes commands"""

    def __init__(self, machine_id: int, state: MachineState):
        """
        Initialize message handler.

        Args:
            machine_id (int): Unique machine identifier
            state (MachineState): Reference to machine state
        """
        self.machine_id = machine_id
        self.state = state
        self.publish_callback: Optional[Callable] = None

    def set_publish_callback(self, callback: Callable) -> None:
        """
        Set callback for publishing messages.

        Args:
            callback (Callable): Function to publish messages
        """
        self.publish_callback = callback

    def process_message(self, topic: str, payload: str) -> None:
        """
        Process incoming message.

        Args:
            topic (str): MQTT topic
            payload (str): Message payload
        """
        try:
            json_payload = json.loads(payload)
            message_title = json_payload.get("title", "")

            # IMPORTANT: Ignore our own confirmation messages to prevent loops
            if message_title == "BladeSwapped":
                LOGGER.debug(f"Ignoring BladeSwapped confirmation message (our own output)")
                return

            if message_title == "AssignBlade":
                self._handle_assign_blade(json_payload)
            elif message_title == "SwapBlade":
                self._handle_swap_blade(json_payload)
            elif message_title == "killMachine":
                self._handle_kill_machine(json_payload)
            else:
                LOGGER.debug(f"Unknown message title: {message_title}")

        except json.JSONDecodeError as e:
            LOGGER.error(f"Failed to parse JSON from topic {topic}: {str(e)}")
        except Exception as e:
            LOGGER.error(f"Error processing message: {str(e)}")

    def _handle_assign_blade(self, json_payload: dict) -> None:
        """
        Handle AssignBlade command.

        Args:
            json_payload (dict): Parsed JSON message
        """
        machine_id = json_payload.get("machineId")

        # Filter: only process if for this machine
        if machine_id != self.machine_id:
            LOGGER.debug(f"AssignBlade for different machine {machine_id}, ignoring")
            return

        blade_type = json_payload.get("bladeType")

        if blade_type is None:
            LOGGER.error("AssignBlade message missing bladeType")
            return

        self.state.assign_blade(blade_type)
        LOGGER.info(
            f"✅ Machine {self.machine_id} ASSIGNED blade type {blade_type} - NOW WORKING"
        )

    def _handle_swap_blade(self, json_payload: dict) -> None:
        """
        Handle SwapBlade command.

        Args:
            json_payload (dict): Parsed JSON message
        """
        machine_id = json_payload.get("machineId")

        # Filter: only process if for this machine
        if machine_id != self.machine_id:
            LOGGER.debug(f"SwapBlade for different machine {machine_id}, ignoring")
            return

        new_blade_type = json_payload.get("bladeType")

        if new_blade_type is None:
            LOGGER.error("SwapBlade message missing bladeType")
            return

        # Check if blade type is already set to the new type (prevents duplicate processing)
        current_blade = self.state.get_blade_type()
        LOGGER.info(f"SwapBlade received: current_blade={current_blade}, new_blade={new_blade_type}")
        
        if current_blade == new_blade_type:
            LOGGER.warning(f"⚠️ Blade already set to {new_blade_type}, blocking duplicate")
            return

        try:
            LOGGER.info(
                f"Machine {self.machine_id} received blade swap command, sleeping 2 seconds..."
            )
            old_blade_type, _ = self.state.swap_blade(new_blade_type)

            LOGGER.info(
                f"🔄 Machine {self.machine_id} swapped blade from {old_blade_type} to {new_blade_type}"
            )

            # Send confirmation
            if self.publish_callback:
                message = json.dumps({
                    "title": "BladeSwapped",
                    "machineId": self.machine_id
                })
                LOGGER.info(f"📤 Publishing BladeSwapped message...")
                self.publish_callback("productionPlan/bladeSwapped", message)
                LOGGER.info(f"✅ Machine {self.machine_id} sent BladeSwapped confirmation")
            else:
                LOGGER.error("Publish callback not set!")

        except Exception as e:
            LOGGER.error(f"Error handling blade swap: {str(e)}", exc_info=True)

    def _handle_kill_machine(self, json_payload: dict) -> None:
        """
        Handle killMachine command.

        Args:
            json_payload (dict): Parsed JSON message
        """
        machine_id = json_payload.get("machineId")

        # Filter: only process if for this machine
        if machine_id != self.machine_id:
            LOGGER.debug(f"KillMachine for different machine {machine_id}, ignoring")
            return

        recovery_time = json_payload.get("recoveryTime", 0)

        if recovery_time <= 0:
            LOGGER.error(f"KillMachine message invalid recoveryTime: {recovery_time}")
            return

        self.state.enter_recovery(recovery_time)
        LOGGER.warning(
            f"Machine {self.machine_id} entering recovery mode for {recovery_time} seconds"
        )