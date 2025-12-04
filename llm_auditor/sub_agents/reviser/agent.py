"""Reviser agent for correcting inaccuracies based on verified findings."""

import os
from google.adk import Agent
from google.adk.agents.callback_context import CallbackContext
from google.adk.models import LlmResponse

import sys
sys.path.append("..")
from callback_logging import log_query_to_model, log_model_response

from . import prompt

_END_OF_EDIT_MARK = '---END-OF-EDIT---'


def _remove_end_of_edit_mark(
    callback_context: CallbackContext,
    llm_response: LlmResponse,
) -> LlmResponse:
    del callback_context  # unused
    if not llm_response.content or not llm_response.content.parts:
        return llm_response
    for idx, part in enumerate(llm_response.content.parts):
        if _END_OF_EDIT_MARK in part.text:
            del llm_response.content.parts[idx + 1 :]
            part.text = part.text.split(_END_OF_EDIT_MARK, 1)[0]
    return llm_response


reviser_agent = Agent(
    model=os.getenv("MODEL"),
    name='reviser_agent',
    instruction=prompt.REVISER_PROMPT,
    before_model_callback=log_query_to_model,
    after_model_callback=_remove_end_of_edit_mark,
)
