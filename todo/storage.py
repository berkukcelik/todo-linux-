"""Task model and JSON persistence."""

from __future__ import annotations

import json
import os
import uuid
from dataclasses import asdict, dataclass, field, fields
from datetime import datetime
from pathlib import Path


def default_path() -> Path:
    """Tasks live in $XDG_DATA_HOME/todo-linux/tasks.json (~/.local/share by default)."""
    base = os.environ.get("XDG_DATA_HOME") or Path.home() / ".local" / "share"
    return Path(base) / "todo-linux" / "tasks.json"


@dataclass
class Task:
    title: str
    done: bool = False
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    created: str = field(
        default_factory=lambda: datetime.now().isoformat(timespec="seconds")
    )


_TASK_FIELDS = {f.name for f in fields(Task)}


class TaskStore:
    """An ordered list of tasks, saved to disk after every change."""

    def __init__(self, path: str | Path | None = None):
        self.path = Path(path) if path else default_path()
        self.tasks: list[Task] = []
        self.load()

    def load(self) -> None:
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
        except FileNotFoundError:
            self.tasks = []
            return
        except (json.JSONDecodeError, UnicodeDecodeError):
            # Keep the unreadable file around instead of silently overwriting it.
            self.path.replace(self.path.with_suffix(".corrupt.json"))
            self.tasks = []
            return
        self.tasks = [
            Task(**{k: v for k, v in item.items() if k in _TASK_FIELDS})
            for item in data
            if isinstance(item, dict) and "title" in item
        ]

    def save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.path.with_suffix(".tmp")
        tmp.write_text(
            json.dumps([asdict(t) for t in self.tasks], indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        os.replace(tmp, self.path)  # atomic, so a crash never leaves a half-written file

    def get(self, task_id: str) -> Task | None:
        return next((t for t in self.tasks if t.id == task_id), None)

    def add(self, title: str) -> Task | None:
        title = title.strip()
        if not title:
            return None
        task = Task(title=title)
        self.tasks.append(task)
        self.save()
        return task

    def toggle(self, task_id: str) -> None:
        if task := self.get(task_id):
            task.done = not task.done
            self.save()

    def rename(self, task_id: str, title: str) -> None:
        title = title.strip()
        task = self.get(task_id)
        if task and title:
            task.title = title
            self.save()

    def remove(self, task_id: str) -> tuple[int, Task] | None:
        """Remove a task and return (index, task) so it can be restored with insert()."""
        for i, task in enumerate(self.tasks):
            if task.id == task_id:
                del self.tasks[i]
                self.save()
                return i, task
        return None

    def insert(self, index: int, task: Task) -> None:
        self.tasks.insert(min(index, len(self.tasks)), task)
        self.save()

    def clear_completed(self) -> list[tuple[int, Task]]:
        """Remove finished tasks; returns (index, task) pairs in ascending order for undo."""
        removed = [(i, t) for i, t in enumerate(self.tasks) if t.done]
        if removed:
            self.tasks = [t for t in self.tasks if not t.done]
            self.save()
        return removed

    @property
    def remaining(self) -> int:
        return sum(not t.done for t in self.tasks)
