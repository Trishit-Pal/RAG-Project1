import psycopg

from utils.messages import friendly_message


def test_database_errors_point_to_the_env_file():
    msg = friendly_message(psycopg.OperationalError("connection refused"))
    assert "database" in msg.lower()
    assert ".env" in msg


def test_rate_limit_errors_say_to_wait():
    msg = friendly_message(RuntimeError("429 RESOURCE_EXHAUSTED"))
    assert "wait" in msg.lower()


def test_unknown_errors_do_not_leak_details():
    msg = friendly_message(ValueError("password=hunter2 in /secret/path"))
    assert "hunter2" not in msg
