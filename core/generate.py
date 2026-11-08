"""Ask Gemini to write an answer.

Used by core/ask.py. If Google says "too many requests" (a rate limit), we wait
and try again. If it still fails, we try a cheaper backup model once.
"""
import time

from google import genai

from core.config import GEMINI_API_KEY

MAIN_MODEL = "gemini-3.5-flash"
BACKUP_MODEL = "gemini-2.5-flash-lite"  # used only when the main model is rate-limited
MAX_TRIES = 3

client = genai.Client(api_key=GEMINI_API_KEY)


def is_rate_limit(error: Exception) -> bool:
    # Google's "too many requests" errors contain "429" or "RESOURCE_EXHAUSTED".
    text = str(error)
    return "429" in text or "RESOURCE_EXHAUSTED" in text


def call_model(prompt: str, model: str) -> str:
    """Send the prompt to one model. Retry up to 3 times when rate-limited."""
    for attempt in range(1, MAX_TRIES + 1):
        try:
            response = client.models.generate_content(model=model, contents=prompt)
        except Exception as error:
            # Only rate limits are worth retrying. Any other error, or the last try, stops here.
            if not is_rate_limit(error) or attempt == MAX_TRIES:
                raise
            time.sleep(2 * attempt)  # wait 2 seconds, then 4 seconds
            continue

        if response.text is None:
            raise RuntimeError("Gemini returned no text")
        return response.text


def generate_text(prompt: str) -> tuple[str, str]:
    """Return (answer, name of the model that wrote it)."""
    try:
        return call_model(prompt, MAIN_MODEL), MAIN_MODEL
    except Exception as error:
        if not is_rate_limit(error):
            raise
        # Still rate-limited after all tries: try the backup model.
        return call_model(prompt, BACKUP_MODEL), BACKUP_MODEL
