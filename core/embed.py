"""Turn text into vectors (lists of 768 numbers) with Gemini.

Texts with similar meaning get similar vectors. That is how search finds
passages related to a question. Used by core/ingest.py and core/retrieve.py.
"""
import math

from google import genai
from google.genai import types

from core.config import GEMINI_API_KEY

MODEL = "gemini-embedding-2"
DIM = 768  # numbers per vector; must match vector(768) in sql/001_init.sql

# Documents and questions are embedded slightly differently, which improves search.
VALID_TASK_TYPES = ["RETRIEVAL_DOCUMENT", "RETRIEVAL_QUERY"]

client = genai.Client(api_key=GEMINI_API_KEY)


def normalize(vector: list[float]) -> list[float]:
    """Scale the vector to length 1, so only its direction matters when comparing."""
    total = 0.0
    for number in vector:
        total += number * number
    length = math.sqrt(total)
    if length == 0:
        raise ValueError("Vector embedding has zero length")

    scaled = []
    for number in vector:
        scaled.append(number / length)
    return scaled


def embed_texts(texts: list[str], task_type: str) -> list[list[float]]:
    """Return one vector per text, in the same order."""
    if task_type not in VALID_TASK_TYPES:
        raise ValueError(f"task_type must be one of {VALID_TASK_TYPES}")
    if not texts:
        return []

    # Each text must be its own Content. A plain list of strings is read by
    # Gemini as ONE document and returns only ONE vector for all of them.
    contents = []
    for text in texts:
        contents.append(types.Content(parts=[types.Part(text=text)]))

    response = client.models.embed_content(
        model=MODEL,
        contents=contents,
        config=types.EmbedContentConfig(output_dimensionality=DIM, task_type=task_type),
    )

    vectors = []
    for embedding in response.embeddings:
        vectors.append(normalize(embedding.values))

    # Never continue with missing vectors: that used to drop chunks without any error.
    if len(vectors) != len(texts):
        raise RuntimeError(f"Gemini returned {len(vectors)} vectors for {len(texts)} texts")
    return vectors
