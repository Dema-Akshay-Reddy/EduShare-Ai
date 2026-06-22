import database as db
import pytest


@pytest.fixture
def isolated_db(tmp_path, monkeypatch):
    db_path = tmp_path / "resource_platform.db"
    monkeypatch.setattr(db, "DB_PATH", str(db_path))
    db.init_db()
    return db
