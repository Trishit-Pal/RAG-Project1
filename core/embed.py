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

    response = client.models.embed_content(
    model= MODEL,
    contents= texts,
    config= types.EmbedContentConfig(
        output_dimensionality = DIM,
        task_type= task_type,
    ),
    )

    return [_12_normalize(e.values) for e in response.embeddings]
