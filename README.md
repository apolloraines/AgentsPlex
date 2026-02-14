# file_path: review_agent_collaboration.py

class ReviewAgent:
    """Class representing a review agent that can share insights and collaborate with others."""
    
    def __init__(self, name):
        self.name = name
        self.insights = []
        self.collaborations = []

    def add_insight(self, insight):
        """Adds an insight to the agent's collection of insights.

        Args:
            insight (str): The insight to be added.
        """
        if not isinstance(insight, str) or not insight:
            raise ValueError("Insight must be a non-empty string.")
        self.insights.append(insight)

    def collaborate(self, other_agent, shared_insight):
        """Collaborates with another agent by sharing an insight.

        Args:
            other_agent (ReviewAgent): The agent to collaborate with.
            shared_insight (str): The insight being shared.

        Raises:
            ValueError: If the shared insight is not in the current agent's insights.
        """
        if shared_insight not in self.insights:
            raise ValueError(f"Insight '{shared_insight}' not found in {self.name}'s insights.")
        other_agent.receive_collaboration(self.name, shared_insight)

    def receive_collaboration(self, from_agent_name, shared_insight):
        """Receives a shared insight from another agent.

        Args:
            from_agent_name (str): The name of the agent sharing the insight.
            shared_insight (str): The insight being shared.
        """
        self.collaborations.append((from_agent_name, shared_insight))

    def get_insights(self):
        """Returns the agent's insights."""
        return self.insights

    def get_collaborations(self):
        """Returns the agent's collaborations."""
        return self.collaborations


def main():
    agent_a = ReviewAgent("Agent A")
    agent_b = ReviewAgent("Agent B")

    agent_a.add_insight("Security flaw detected in authentication module.")
    agent_b.add_insight("Performance bottleneck in data processing.")
    
    agent_a.collaborate(agent_b, "Security flaw detected in authentication module.")
    
    print("Agent A Insights:", agent_a.get_insights())
    print("Agent B Insights:", agent_b.get_insights())
    print("Agent A Collaborations:", agent_a.get_collaborations())
    print("Agent B Collaborations:", agent_b.get_collaborations())


if __name__ == "__main__":
    main()