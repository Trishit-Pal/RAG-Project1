"""Settings for the tests. pytest reads this file before any test.

The Gemini library refuses to start without a key, even though the tests never
call Gemini (they use stand-ins). A placeholder key lets the tests run on a
fresh copy of the project with no .env file.
"""
import os

# Missing or empty both count as "no key".
if not os.environ.get("GEMINI_API_KEY"):
    os.environ["GEMINI_API_KEY"] = "placeholder-key-tests-never-call-gemini"
