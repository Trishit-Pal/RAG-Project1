"""Quick check that the Gemini key works: one embedding and one answer.

Run from the project root:
    python -m evals.smoke_test
"""
import math

from core.embed import embed_texts
from core.generate import generate_text

SENTENCE = "hello, how are you?"
PROMPT = "Reply with one word: Bonjour, ca va"

vector = embed_texts([SENTENCE], task_type="RETRIEVAL_DOCUMENT")[0]
norm = math.sqrt(sum(x * x for x in vector))

print(f"length : {len(vector)}")
print(f"norm : {norm}")

reply, model = generate_text(PROMPT)
print(f"Generated text ({model}): {reply}")
