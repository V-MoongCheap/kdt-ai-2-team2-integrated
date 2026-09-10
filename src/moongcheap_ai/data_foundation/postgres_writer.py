"""Write Part A labels to the Backend-owned demand table."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from datetime import datetime, timezone
from typing import Any, Protocol


class WritableCursor(Protocol):
    def __enter__(self) -> "WritableCursor": ...
    def __exit__(self, exc_type: Any, exc_value: Any, traceback: Any) -> None: ...
    def execute(self, query: str, params: tuple[Any, ...]) -> Any: ...


class WritableConnection(Protocol):
    def cursor(self) -> WritableCursor: ...
    def commit(self) -> None: ...
    def rollback(self) -> None: ...


UPDATE_LABEL_SQL = """
UPDATE demand
SET label = %s,
    processed_at = %s,
    updated_at = %s
WHERE id = %s
  AND processed_at IS NULL
""".strip()


def write_labels(
    connection: WritableConnection,
    rows: Iterable[Mapping[str, Any]],
    *,
    processed_at: datetime | None = None,
) -> int:
    """Persist successful labels and leave review rows pending."""

    timestamp = processed_at or datetime.now(timezone.utc)
    prepared = [
        (str(row.get("label", "")), timestamp, timestamp, row["demand_id"])
        for row in rows
        if str(row.get("status", "")).strip() != "REVIEW"
    ]
    if not prepared:
        return 0
    try:
        updated = 0
        with connection.cursor() as cursor:
            for params in prepared:
                result = cursor.execute(UPDATE_LABEL_SQL, params)
                rowcount = getattr(result, "rowcount", None)
                updated += int(rowcount if rowcount is not None else 1)
        connection.commit()
        return updated
    except Exception:
        connection.rollback()
        raise
