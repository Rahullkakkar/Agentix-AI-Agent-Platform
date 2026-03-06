from engine.campaign_loader import load_campaigns
from engine.runtime import AgentRuntime
from agents.lead_qualification import LeadQualificationAgent
from agents.outbound_recommendation import OutboundRecommendationAgent
from engine.llm import llm


def main():
    print("Select agent:")
    print("1. Lead Qualification")
    print("2. Outbound Recommendation")

    choice = input("Enter choice (1 or 2): ").strip()

    campaign = None

    if choice == "2":
        campaigns = load_campaigns("campaigns.xlsx")
        campaign = campaigns[3]  # later → loop for outbound calls
        agent = OutboundRecommendationAgent()
    else:
        agent = LeadQualificationAgent()

    runtime = AgentRuntime(
        agent=agent,
        campaign_context=campaign
    )

    if hasattr(agent, "prepare"):
        agent.prepare(runtime.state_memory)

    runtime.run()


if __name__ == "__main__":
    main()