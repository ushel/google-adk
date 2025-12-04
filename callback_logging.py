import logging
from typing import Optional

from google.adk.agents.callback_context import CallbackContext
from google.adk.models import LlmRequest, LlmResponse

# For resume_creater_memory: load/save stored resumes so we can inject
# them into the prompt when the same user comes back later.
try:
    from resume_creater_memory.resume_storage import load_resume  # type: ignore
except Exception:  # pragma: no cover - defensive; other agents may not need this
    load_resume = None  # type: ignore


# Configure local logging (console + file)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(),  # prints to terminal
        logging.FileHandler("agent.log"),  # writes to agent.log locally
    ],
)


def _compute_persistence_id(callback_context: CallbackContext) -> str:
    """Derive a stable id for storing/retrieving resumes.

    Priority:
    1. session_state["user_id"]  (if provided by the app / ADK Web)
    2. session_state["session_id"]
    3. callback_context.session_id
    4. "default" (fallback)
    """

    session_state = getattr(callback_context, "session_state", None)
    persistence_id: Optional[str] = None

    if isinstance(session_state, dict):
        persistence_id = (
            session_state.get("user_id")
            or session_state.get("session_id")
        )

    if not persistence_id:
        persistence_id = getattr(callback_context, "session_id", None)

    if not persistence_id:
        persistence_id = "default"

    return str(persistence_id)


def _looks_like_candidate_info(text: str) -> bool:
    """Heuristic to decide if the user message already contains full resume data.

    If it does, we should NOT inject the stored resume, so a fresh
    resume can be generated purely from the new info.
    """

    lowered = text.lower()

    # If it's long and structured, it's likely candidate info
    if len(text) > 300:
        return True

    # Common resume field markers
    keywords = [
        "experience:",
        "skills:",
        "education:",
        "projects:",
        "summary:",
        "work experience",
        "years of experience",
        "responsibilities",
    ]
    return any(k in lowered for k in keywords)


def log_query_to_model(callback_context: CallbackContext, llm_request: LlmRequest):
    """Log the last user message and, for resume agent, optionally inject stored resume.

    Behavior for `resume_generator_agent`:
    - If the user message already looks like full candidate info, we do
      NOT inject memory (so a brand-new resume is generated).
    - If the user message is short/control-like (e.g. "show my resume",
      "print my resume"), we prepend the stored resume so the model can
      answer without the user re-sending details.
    """

    if not llm_request.contents or llm_request.contents[-1].role != "user":
        return

    user_content = llm_request.contents[-1]
    part = user_content.parts[-1]

    if not part.text:
        return

    original_text = part.text
    agent_name = getattr(callback_context, "agent_name", None)

    # Only apply memory injection for this specific agent
    if agent_name == "resume_generator_agent" and load_resume is not None:
        # If this looks like fresh candidate info, don't inject memory
        if not _looks_like_candidate_info(original_text):
            persistence_id = _compute_persistence_id(callback_context)
            stored_resume = load_resume(persistence_id)

            if stored_resume:
                part.text = (
                    "Stored resume for this user (from previous sessions):\n"
                    f"{stored_resume}\n\n"
                    "User request:\n"
                    f"{original_text}"
                )

    # Log whatever text is now going to the model
    logging.info(f"[query to {agent_name}]: {part.text}")


def log_model_response(callback_context: CallbackContext, llm_response: LlmResponse):
    if llm_response.content and llm_response.content.parts:
        for part in llm_response.content.parts:
            if part.text:
                logging.info(
                    f"[response from {callback_context.agent_name}]: {part.text}"
                )
            elif part.function_call:
                logging.info(
                    f"[function call from {callback_context.agent_name}]: "
                    f"{part.function_call.name}"
                )
