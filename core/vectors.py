"""Helpers for pgvector.

pgvector stores vectors as text like "[0.1,0.2,0.3]".
Python lists must be converted to that text before they are sent to Postgres.
"""


def to_vector_literal(vec: list[float]) -> str:
    # Turn each number into text and join them with commas inside [ ].
    return "[" + ",".join(str(float(x)) for x in vec) + "]"