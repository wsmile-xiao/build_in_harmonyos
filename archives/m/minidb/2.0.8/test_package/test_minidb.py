import datetime
import os
import sqlite3
import tempfile
import unittest

import minidb


class MiniDBConsumerTests(unittest.TestCase):
    def test_import_uses_runtime_sqlite(self):
        installed_module = os.path.normpath(minidb.__file__)
        self.assertTrue(installed_module.endswith(
            os.path.join("lib", "python3", "site-packages", "minidb.py")))
        self.assertGreaterEqual(sqlite3.sqlite_version_info, (3, 0, 0))
        with sqlite3.connect(":memory:") as connection:
            self.assertEqual(connection.execute("select 1").fetchone(), (1,))
            self.assertEqual(
                connection.execute("select sqlite_version()").fetchone()[0],
                sqlite3.sqlite_version)

    def test_model_round_trip_in_memory(self):
        class Record(minidb.Model):
            name = str
            count = int

        with minidb.Store() as db:
            db.register(Record)
            record = Record(name="HarmonyOS", count=2)
            record.save(db)
            self.assertIsNotNone(record.id)
            self.assertIs(Record.get(db, id=record.id), record)
            record.count = 3
            record.save()
            self.assertEqual(Record.get(db, id=record.id).count, 3)

    def test_file_database_persists_after_reopen(self):
        class Note(minidb.Model):
            text = str
            created = datetime.datetime

        with tempfile.TemporaryDirectory() as directory:
            path = os.path.join(directory, "minidb.sqlite")
            with minidb.Store(path) as db:
                db.register(Note)
                note = Note(text="persisted", created=datetime.datetime(2026, 10, 2))
                note.save(db)
                row_id = note.id
            with minidb.Store(path) as db:
                db.register(Note)
                loaded = Note.get(db, id=row_id)
                self.assertEqual(loaded.text, "persisted")
                self.assertEqual(loaded.created, datetime.datetime(2026, 10, 2))
                self.assertEqual(len(list(Note.load(db))), 1)


if __name__ == "__main__":
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(MiniDBConsumerTests)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    raise SystemExit(0 if result.wasSuccessful() else 1)
