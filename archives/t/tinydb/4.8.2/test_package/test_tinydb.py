"""R34 consumer check: import packaged TinyDB and exercise document queries."""
import tempfile
from pathlib import Path

from tinydb import Query, TinyDB

with tempfile.TemporaryDirectory(prefix="tinydb-consumer-") as temp_dir:
    db = TinyDB(str(Path(temp_dir) / "db.json"))
    first_id = db.insert({"name": "Ada", "active": True})
    second_id = db.insert({"name": "Lin", "active": False})
    Person = Query()
    assert first_id == 1
    assert second_id == 2
    assert db.search(Person.active == True) == [
        {"name": "Ada", "active": True}
    ]
    assert len(db) == 2
    db.close()

print("OK: TinyDB import, insert, query, and JSON storage")