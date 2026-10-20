import json
import tempfile
import unittest
from pathlib import Path

from todo.storage import TaskStore


class TaskStoreTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = Path(self.tmp.name) / "sub" / "tasks.json"
        self.store = TaskStore(self.path)
        self.path.parent.mkdir()

    def tearDown(self):
        self.tmp.cleanup()

    def test_add_persists_and_reloads(self):
        self.store.add("  buy milk  ")
        reloaded = TaskStore(self.path)
        self.assertEqual([t.title for t in reloaded.tasks], ["buy milk"])

    def test_blank_title_is_ignored(self):
        self.assertIsNone(self.store.add("   "))
        self.assertEqual(self.store.tasks, [])

    def test_toggle_and_remaining(self):
        a = self.store.add("a")
        self.store.add("b")
        self.store.toggle(a.id)
        self.assertTrue(TaskStore(self.path).get(a.id).done)
        self.assertEqual(self.store.remaining, 1)

    def test_rename_ignores_blank(self):
        t = self.store.add("old")
        self.store.rename(t.id, "")
        self.assertEqual(self.store.get(t.id).title, "old")
        self.store.rename(t.id, "new")
        self.assertEqual(TaskStore(self.path).get(t.id).title, "new")

    def test_remove_then_insert_restores_order(self):
        ids = [self.store.add(x).id for x in "abc"]
        index, task = self.store.remove(ids[1])
        self.store.insert(index, task)
        self.assertEqual([t.id for t in self.store.tasks], ids)

    def test_clear_completed_undo_restores_order(self):
        tasks = [self.store.add(x) for x in "abcd"]
        self.store.toggle(tasks[0].id)
        self.store.toggle(tasks[2].id)
        removed = self.store.clear_completed()
        self.assertEqual([t.title for t in self.store.tasks], ["b", "d"])
        for index, task in removed:
            self.store.insert(index, task)
        self.assertEqual([t.title for t in self.store.tasks], list("abcd"))

    def test_corrupt_file_is_backed_up(self):
        self.path.write_text("{not json")
        store = TaskStore(self.path)
        self.assertEqual(store.tasks, [])
        self.assertTrue(self.path.with_suffix(".corrupt.json").exists())

    def test_unknown_fields_are_ignored(self):
        self.path.write_text(json.dumps([{"title": "x", "extra": 1}]))
        self.assertEqual(TaskStore(self.path).tasks[0].title, "x")


if __name__ == "__main__":
    unittest.main()
