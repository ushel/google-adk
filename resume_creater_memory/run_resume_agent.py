"""Simple CLI runner for the resume_creater_memory agent.

This lets you test that state and resumes are persisted correctly.
Usage (from project root):

    python -m resume_creater_memory.run_resume_agent

You can then:
- Press Enter to start a NEW session, or
- Paste an existing session_id to continue a previous session.
"""

import asyncio

from resume_creater_memory.agent import run_resume_agent


async def main() -> None:
    # Get or create session
    raw = input("Enter existing session_id (or press Enter for new): ").strip()
    session_id = raw or None

    print("\nPaste candidate info (end with an empty line, then Ctrl+C if needed):\n")
    lines = []
    try:
        while True:
            line = input()
            if line == "":
                # Stop on empty line to avoid hanging indefinitely
                break
            lines.append(line)
    except EOFError:
        # End of input (e.g., piped input)
        pass

    candidate_info = "\n".join(lines).strip()

    if not candidate_info:
        print("No candidate info provided. Exiting.")
        return

    response, session_id = await run_resume_agent(
        candidate_info=candidate_info,
        session_id=session_id,
    )

    print("\n=== Session ID ===")
    print(session_id)
    print("\n=== Generated Resume ===\n")
    print(response.content.parts[0].text)


if __name__ == "__main__":
    asyncio.run(main())
