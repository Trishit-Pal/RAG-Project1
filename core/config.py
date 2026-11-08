"""Settings: the database address and the Gemini key, read from the .env file.

Every other file gets its settings from here. app.py calls missing_settings()
first, so a missing setting shows a clear message instead of a crash.
"""
import os

from dotenv import load_dotenv

# Copy the lines of the .env file into the environment, so os.getenv() can read them.
load_dotenv()

REQUIRED_SETTINGS = ["DATABASE_URL", "GEMINI_API_KEY"]

DATABASE_URL = os.getenv("DATABASE_URL", "").strip()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "").strip()


def missing_settings() -> list[str]:
    """Return the names of required settings that are empty or not set."""
    missing = []
    for name in REQUIRED_SETTINGS:
        if not os.getenv(name, "").strip():
            missing.append(name)
    return missing
