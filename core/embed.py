import math
from google import genai
from google.genai import types

from core.config import settings

MODEL= "gemini-embedding-2"
DIM= 768

VALID_TASK_TYPES = {"RETRIEVAL_DOCUMENT", "RETRIEVAL_QUERY"}

client= genai.Client(api_key=settings.GEMINI_API_KEY)

def _12_normalize(vec: list[float]) -> list[float]:
    norm = math.sqrt(sum(x*x for x in vec))
    if norm==0:
        raise ValueError("Vector embedding has zero length")
    return [x/norm for x in vec]

def embed_texts(texts: list[str],task_type: str) -> list[list[float]]:
    if task_type not in VALID_TASK_TYPES:
        raise ValueError (f"task_type must be one of {sorted(VALID_TASK_TYPES)}")
    if not texts:
        return []

    # Each text must be its own Content. A plain list of strings is read by
    # Gemini as ONE document and returns only ONE vector for all of them.
    contents = [types.Content(parts=[types.Part(text=t)]) for t in texts]
    response = client.models.embed_content(
        model=MODEL,
        contents=contents,
        config=types.EmbedContentConfig(output_dimensionality=DIM, task_type=task_type),
    )

    vectors = [_12_normalize(e.values) for e in response.embeddings]
    # Never continue with missing vectors: that used to drop chunks without any error.
    if len(vectors) != len(texts):
        raise RuntimeError(f"Gemini returned {len(vectors)} vectors for {len(texts)} texts")
    return vectors
