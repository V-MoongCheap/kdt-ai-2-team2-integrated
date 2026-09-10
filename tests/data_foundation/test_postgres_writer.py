from datetime import datetime, timezone

import pytest

from moongcheap_ai.data_foundation.postgres_writer import write_labels


class _Result:
    rowcount = 1


class _Cursor:
    def __init__(self, fail=False):
        self.fail = fail
        self.calls = []

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        return None

    def execute(self, query, params):
        if self.fail:
            raise RuntimeError("db failure")
        self.calls.append((query, params))
        return _Result()


class _Connection:
    def __init__(self, fail=False):
        self.cursor_value = _Cursor(fail=fail)
        self.committed = 0
        self.rolled_back = 0

    def cursor(self):
        return self.cursor_value

    def commit(self):
        self.committed += 1

    def rollback(self):
        self.rolled_back += 1


def test_writer_commits_successful_rows_and_leaves_review_pending():
    connection = _Connection()
    timestamp = datetime(2026, 9, 10, tzinfo=timezone.utc)
    updated = write_labels(
        connection,
        [
            {"demand_id": 1, "label": "1-2", "status": "PARSED"},
            {"demand_id": 2, "label": "", "status": "REVIEW"},
        ],
        processed_at=timestamp,
    )
    assert updated == 1
    assert connection.committed == 1
    assert connection.rolled_back == 0
    assert connection.cursor_value.calls[0][1] == ("1-2", timestamp, timestamp, 1)


def test_writer_rolls_back_on_database_error():
    connection = _Connection(fail=True)
    with pytest.raises(RuntimeError, match="db failure"):
        write_labels(connection, [{"demand_id": 1, "label": "1", "status": "PARSED"}])
    assert connection.committed == 0
    assert connection.rolled_back == 1
