"""Phase 7b: call Gemini to write answers.

Rate-limit errors (HTTP 429) are retried a few times. If they keep failing,
the request falls back to a cheaper model.
"""
from google import genai
from tenacity import retry, retry_if_exception, stop_after_attempt, wait_exponential

from core.config import settings

PRIMARY_MODEL = "gemini-3.5-flash"
# Approved fallback. Free-tier availability is NOT yet verified (see notes).
FALLBACK_MODEL = "gemini-2.5-flash-lite"

client = genai.Client(api_key=settings.GEMINI_API_KEY)


def _is_rate_limit(err: Exception) -> bool:
    # Google's rate-limit errors contain "429" or "RESOURCE_EXHAUSTED".
    text = str(err)
    return "429" in text or "RESOURCE_EXHAUSTED" in text


@retry(
    retry=retry_if_exception(_is_rate_limit),  # only retry rate limits
    stop=stop_after_attempt(3),                # 3 tries in total
    wait=wait_exponential(multiplier=2, min=2, max=20),  # waits grow: 2s, 4s, ...
    reraise=True,                              # if all tries fail, raise the error
)
def _call_model(prompt: str, model: str) -> str:
    response = client.models.generate_content(model=model, contents=prompt)
    if response.text is None:
        raise RuntimeError("Gemini returned no text")
    return response.text


def generate_text(prompt: str, model: str = PRIMARY_MODEL) -> tuple[str, str]:
    # Returns (answer, model that wrote it), so callers can record which one was used.
    try:
        return _call_model(prompt, model), model
    except Exception as err:
        # Still rate-limited after retries: try the fallback once.
        if _is_rate_limit(err) and model != FALLBACK_MODEL:
            return _call_model(prompt, FALLBACK_MODEL), FALLBACK_MODEL
        raise