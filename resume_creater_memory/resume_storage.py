import os

RESUME_DIR = os.path.join(os.path.dirname(__file__), "resumes")
os.makedirs(RESUME_DIR, exist_ok=True)


def get_resume_path(session_id: str) -> str:
    return os.path.join(RESUME_DIR, f"{session_id}.txt")


def save_resume(session_id: str, text: str):
    """Append resume text to a file for this session/user.

    We *append* instead of overwriting so that multiple sessions for the
    same logical user_id (or session_id) accumulate in a single file.
    A simple separator is added between entries.
    """
    path = get_resume_path(session_id)
    # Ensure file exists and append with a separator
    with open(path, "a", encoding="utf-8") as f:
        if f.tell() != 0:
            f.write("\n\n" + "-" * 40 + "\n\n")
        f.write(text)


def load_resume(session_id: str) -> str:
    """Loads *all* resume text for this session/user. Returns '' if not found."""
    path = get_resume_path(session_id)
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return f.read()
    return ""
