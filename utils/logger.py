"""One shared logger. Details go to the terminal, never to the browser."""
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")


def get_logger(name: str = "rag") -> logging.Logger:
    return logging.getLogger(name)
