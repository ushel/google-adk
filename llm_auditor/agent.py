"""LLM Auditor for verifying & refining LLM-generated answers using the web."""

from google.adk.agents import SequentialAgent

# import sys
# sys.path.append("..")
# from callback_logging import log_model_response, log_query_to_model
from callback_logging import log_model_response, log_query_to_model

from .sub_agents.critic import critic_agent
from .sub_agents.reviser import reviser_agent

llm_auditor = SequentialAgent(
    name="llm_auditor",
    description=(
        "Evaluates LLM-generated answers, verifies actual accuracy using the"
        " web, and refines the response to ensure alignment with real-world"
        " knowledge."
    ),
    sub_agents=[critic_agent, reviser_agent],
)

root_agent = llm_auditor
