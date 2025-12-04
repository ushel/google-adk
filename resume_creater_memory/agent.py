import os
import uuid
from typing import Dict, Optional, Tuple

from google.adk import Agent
from google.adk.agents.callback_context import CallbackContext
from google.adk.models import LlmResponse

from . import prompt
from .resume_storage import load_resume, save_resume
from callback_logging import log_query_to_model, log_model_response


# -----------------------------
# Callback to format and save resume
# -----------------------------

def _format_resume_output(
    callback_context: CallbackContext,
    llm_response: LlmResponse,
) -> LlmResponse:
    """Merge LLM output into a single text block and persist the resume.

    This callback is compatible with ADK Web's expected signature:
    (callback_context, llm_response).

    Persistence key priority:
    1. session_state["user_id"]  (if you set this for a logical user)
    2. session_state["session_id"]
    3. callback_context.session_id
    4. "default" (fallback)

    This means you can have multiple ADK Web sessions share the same
    stored resume by ensuring they all set the same "user_id" in
    session_state.
    """
    if not llm_response.content or not llm_response.content.parts:
        return llm_response

    # Combine all text parts into one
    combined = "\n".join(
        part.text for part in llm_response.content.parts if part.text
    )
    llm_response.content.parts[0].text = combined
    del llm_response.content.parts[1:]

    # Inspect session_state if present
    session_state = getattr(callback_context, "session_state", None)
    persistence_id: Optional[str] = None

    if isinstance(session_state, dict):
        # Keep in-memory previous_resume for same ADK Web session
        session_state["previous_resume"] = combined

        # Prefer a stable logical user_id if you provide one via ADK Web
        persistence_id = (
            session_state.get("user_id")  # logical user identifier, if set
            or session_state.get("session_id")  # ADK session id, if present
        )

    # Fallback to callback_context.session_id if nothing from session_state
    if not persistence_id:
        persistence_id = getattr(callback_context, "session_id", None)

    # Final fallback so we always write *something*
    if not persistence_id:
        persistence_id = "default"

    # Persist to disk
    save_resume(persistence_id, combined)

    # No grounding metadata for this agent
    llm_response.grounding_metadata = None
    return llm_response


# -----------------------------
# Create the Resume Generator Agent
# -----------------------------

resume_generator_agent = Agent(
    model=os.getenv("MODEL") or "gemini-1.5-pro",
    name="resume_generator_agent",  # valid identifier
    instruction=prompt.RESUME_CREATOR_PROMPT,  # base prompt; overridden per call when using helper
    tools=[],  # No external tools required
    before_model_callback=log_query_to_model,
    after_model_callback=_format_resume_output,
)

# Root agent used by ADK Web
root_agent = resume_generator_agent


# -----------------------------
# Helper: generate session ID
# -----------------------------

def _generate_session_id() -> str:
    return str(uuid.uuid4())


# -----------------------------
# Public helper to run the agent with memory (Python-side)
# -----------------------------

async def run_resume_agent(
    candidate_info: str,
    session_id: Optional[str] = None,
    session_state: Optional[Dict] = None,
) -> Tuple[LlmResponse, str]:
    """Run the Resume Generator with disk-backed memory (Python helper).

    - If ``session_id`` is None, a new one is created.
    - Previous resume (if any) is loaded from disk and included in the prompt.
    - The latest resume is saved back to disk by the callback.

    NOTE: This helper is *not* used automatically by ADK Web. ADK Web
    uses ``root_agent`` directly, but the callback above will still
    persist the resume using the rules described there.
    """

    # Create or reuse session_id
    if session_id is None:
        session_id = _generate_session_id()

    # Load previously saved resume (if any)
    previous_resume = load_resume(session_id)

    # Build session_state
    if session_state is None:
        session_state = {}

    session_state.setdefault("session_id", session_id)
    session_state.setdefault("previous_resume", previous_resume or "")

    # Dynamic instruction including previous resume
    instruction = prompt.build_dynamic_prompt(
        previous_resume=session_state["previous_resume"],
        candidate_info=candidate_info,
    )

    # Run the agent
    response = await resume_generator_agent.run_async(
        instruction=instruction,
        session_state=session_state,
        session_id=session_id,
    )

    return response, session_id
