"""Turn technical errors into short messages a person can act on."""
import psycopg


def friendly_message(err: Exception) -> str:
    text = str(err)
    if isinstance(err, psycopg.OperationalError):
        return "Cannot reach the database. Check DATABASE_URL in your .env file and your internet connection."
    if "429" in text or "RESOURCE_EXHAUSTED" in text:
        return "Gemini is busy or the free limit was reached. Please wait a minute and try again."
    if "API key" in text or "API_KEY" in text or "403" in text:
        return "Gemini rejected the API key. Check GEMINI_API_KEY in your .env file."
    # Unknown error: say so plainly. The details are in the terminal log, not on screen.
    return "Something went wrong. The details were written to the terminal log."
