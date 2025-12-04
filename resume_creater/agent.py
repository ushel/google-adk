"""Resume Generator agent for creating polished candidate resumes without using external references."""

import os

from google.adk import Agent
from google.adk.agents.callback_context import CallbackContext
from google.adk.models import LlmResponse

# Local imports (NO sys.path hacks)
from callback_logging import log_model_response, log_query_to_model

from . import prompt


def _format_resume_output(
    callback_context: CallbackContext,
    llm_response: LlmResponse,
) -> LlmResponse:
    """
    Ensures the response is returned as clean Markdown/plain text.
    No external references or grounding metadata should exist for this agent.
    """
    del callback_context

    if not llm_response.content or not llm_response.content.parts:
        return llm_response

    # Merge all text parts into a single clean text block
    if all(part.text is not None for part in llm_response.content.parts):
        combined = "\n".join(part.text for part in llm_response.content.parts)
        llm_response.content.parts[0].text = combined
        del llm_response.content.parts[1:]

    # Resume generator should never include metadata or references
    llm_response.grounding_metadata = None

    return llm_response


resume_generator_agent = Agent(
    model=os.getenv("MODEL"),
    name="resume_generator_agent",
    instruction=prompt.RESUME_CREATOR_PROMPT,
    tools=[],  # Resume generator does NOT call search tools
    before_model_callback=log_query_to_model,
    after_model_callback=_format_resume_output,
)

root_agent = resume_generator_agent
