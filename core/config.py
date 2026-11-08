import os
from dataclasses import dataclass

from dotenv import load_dotenv

load_dotenv()


def _require(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise RuntimeError(f"Missing required environment variable: {name}. Set it in .env")
    return value


@dataclass(frozen=True)
class Settings:
    DATABASE_URL: str
    GEMINI_API_KEY: str


settings = Settings(
    DATABASE_URL=_require("DATABASE_URL"),
    GEMINI_API_KEY=_require("GEMINI_API_KEY"),
)