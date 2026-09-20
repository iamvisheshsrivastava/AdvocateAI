from unittest.mock import MagicMock

from db import database


def test_unclosed_connection_returned_to_pool(monkeypatch):
    pool = MagicMock()
    raw = MagicMock(closed=0)
    pool.getconn.return_value = raw
    monkeypatch.setattr(database, "_pool", pool)

    conn = database.get_db_connection()
    del conn  # simulates a code path that raised before close()
    pool.putconn.assert_called_once_with(raw)
    raw.rollback.assert_called_once()


def test_context_manager_releases_on_error(monkeypatch):
    pool = MagicMock()
    raw = MagicMock(closed=0)
    pool.getconn.return_value = raw
    monkeypatch.setattr(database, "_pool", pool)
    try:
        with database.db_connection():
            raise RuntimeError("boom")
    except RuntimeError:
        pass
    pool.putconn.assert_called_once_with(raw)
