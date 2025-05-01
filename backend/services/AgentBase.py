import json

class AgentBase:
    def __init__(self, expected_agent_name):
        self.expected_agent_name = expected_agent_name

    def should_process_message(self, message):
        """
        Returns True if the message is intended for this agent.
        - If no target_agent is specified, assume the message is for all agents (accept it).
        - If target_agent exists, only process if it matches this agent's expected name.
        """
        target_agent = message.get("target_agent")
        if target_agent is None:
            # ✨ Allow non-targeted messages by default
            return True
        if target_agent != self.expected_agent_name:
            print(f"⚠️ Message for '{target_agent}', not '{self.expected_agent_name}'. Skipping.")
            return False
        return True

    def parse_message(self, body):
        """
        Safely parse a message from RabbitMQ.
        """
        try:
            return json.loads(body)
        except Exception as e:
            print(f"❌ Failed to parse message: {e}")
            return None
