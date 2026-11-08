from core.ingest import hourly_to_frame, sha256_bytes
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_fixed


def test_sha256_bytes_is_stable_and_different_for_different_input():
    assert sha256_bytes(b"abc") == sha256_bytes(b"abc")
    assert sha256_bytes(b"abc") != sha256_bytes(b"abd")


def test_hourly_to_frame_builds_one_row_per_time():
    data = {"hourly": {"time": ["t1", "t2"], "temperature_2m": [10.0, 11.0]}}
    df = hourly_to_frame(data)
    assert list(df.columns) == ["time", "temperature_2m"]
    assert len(df) == 2