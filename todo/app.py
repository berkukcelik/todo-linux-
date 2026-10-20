"""GTK4 / libadwaita user interface."""

from __future__ import annotations

import sys

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, Gio, GLib, Gtk  # noqa: E402

from .storage import TaskStore  # noqa: E402

APP_ID = "io.github.berkukcelik.TodoLinux"

FILTERS = {
    "all": ("All", lambda t: True, "No tasks yet", "Add one above to get started"),
    "active": ("Active", lambda t: not t.done, "All done!", "Nothing left to do"),
    "done": ("Done", lambda t: t.done, "Nothing finished yet", "Completed tasks show up here"),
}


class TodoWindow(Adw.ApplicationWindow):
    def __init__(self, app: Adw.Application, store: TaskStore):
        super().__init__(application=app, title="To-Do")
        self.store = store
        self.filter = "all"
        self.set_default_size(480, 640)

        # Header: filter toggles in the middle, "clear completed" on the right.
        header = Adw.HeaderBar()
        filter_box = Gtk.Box(css_classes=["linked"])
        first = None
        for key, (label, *_rest) in FILTERS.items():
            button = Gtk.ToggleButton(label=label)
            if first is None:
                first = button
                button.set_active(True)
            else:
                button.set_group(first)
            button.connect("toggled", self.on_filter_toggled, key)
            filter_box.append(button)
        header.set_title_widget(filter_box)

        clear_button = Gtk.Button(
            icon_name="edit-clear-all-symbolic", tooltip_text="Clear completed"
        )
        clear_button.connect("clicked", self.on_clear_completed)
        header.pack_end(clear_button)

        # New-task entry.
        self.entry = Gtk.Entry(placeholder_text="What needs to be done?", hexpand=True)
        self.entry.connect("activate", self.on_add)
        add_button = Gtk.Button(
            icon_name="list-add-symbolic",
            tooltip_text="Add task",
            css_classes=["suggested-action"],
        )
        add_button.connect("clicked", self.on_add)
        entry_box = Gtk.Box(spacing=6)
        entry_box.append(self.entry)
        entry_box.append(add_button)

        # Task list, or an empty-state page when there is nothing to show.
        self.listbox = Gtk.ListBox(
            selection_mode=Gtk.SelectionMode.NONE,
            css_classes=["boxed-list"],
            valign=Gtk.Align.START,
        )
        scrolled = Gtk.ScrolledWindow(
            child=self.listbox, vexpand=True, hscrollbar_policy=Gtk.PolicyType.NEVER
        )
        self.empty_page = Adw.StatusPage(icon_name="checkbox-checked-symbolic")
        self.stack = Gtk.Stack(vexpand=True)
        self.stack.add_named(scrolled, "list")
        self.stack.add_named(self.empty_page, "empty")

        self.counter = Gtk.Label(xalign=0, css_classes=["dim-label"])

        content = Gtk.Box(
            orientation=Gtk.Orientation.VERTICAL,
            spacing=12,
            margin_top=12,
            margin_bottom=12,
            margin_start=12,
            margin_end=12,
        )
        content.append(entry_box)
        content.append(self.stack)
        content.append(self.counter)

        self.toasts = Adw.ToastOverlay(child=Adw.Clamp(maximum_size=640, child=content))
        toolbar = Adw.ToolbarView(content=self.toasts)
        toolbar.add_top_bar(header)
        self.set_content(toolbar)

        focus_action = Gio.SimpleAction(name="focus-entry")
        focus_action.connect("activate", lambda *_: self.entry.grab_focus())
        self.add_action(focus_action)

        self.refresh()
        self.entry.grab_focus()

    # ---- rendering -------------------------------------------------------

    def refresh(self) -> bool:
        self.listbox.remove_all()
        _label, keep, empty_title, empty_desc = FILTERS[self.filter]
        visible = [t for t in self.store.tasks if keep(t)]
        for task in visible:
            self.listbox.append(self._make_row(task))

        self.empty_page.set_title(empty_title)
        self.empty_page.set_description(empty_desc)
        self.stack.set_visible_child_name("list" if visible else "empty")

        left = self.store.remaining
        self.counter.set_label(f"{left} task{'' if left == 1 else 's'} left")
        return GLib.SOURCE_REMOVE  # so it can be used with GLib.idle_add

    def _make_row(self, task) -> Adw.ActionRow:
        title = GLib.markup_escape_text(task.title)
        row = Adw.ActionRow(title=f"<s>{title}</s>" if task.done else title)
        if task.done:
            row.add_css_class("dim-label")

        check = Gtk.CheckButton(active=task.done, valign=Gtk.Align.CENTER)
        check.connect("toggled", lambda *_: self.on_toggle(task.id))
        row.add_prefix(check)
        row.set_activatable_widget(check)

        edit = Gtk.Button(
            icon_name="document-edit-symbolic",
            tooltip_text="Edit",
            valign=Gtk.Align.CENTER,
            css_classes=["flat"],
        )
        edit.connect("clicked", lambda *_: self.on_edit(task.id))
        row.add_suffix(edit)

        delete = Gtk.Button(
            icon_name="user-trash-symbolic",
            tooltip_text="Delete",
            valign=Gtk.Align.CENTER,
            css_classes=["flat"],
        )
        delete.connect("clicked", lambda *_: self.on_delete(task.id))
        row.add_suffix(delete)
        return row

    def _toast(self, title: str, undo=None) -> None:
        toast = Adw.Toast(title=GLib.markup_escape_text(title), timeout=5)
        if undo:
            toast.set_button_label("Undo")
            toast.connect("button-clicked", lambda *_: (undo(), self.refresh()))
        self.toasts.add_toast(toast)

    # ---- handlers --------------------------------------------------------

    def on_add(self, *_):
        if self.store.add(self.entry.get_text()):
            self.entry.set_text("")
            self.refresh()
        self.entry.grab_focus()

    def on_toggle(self, task_id: str):
        self.store.toggle(task_id)
        # Rebuild after the signal finishes, since it destroys the emitting widget.
        GLib.idle_add(self.refresh)

    def on_delete(self, task_id: str):
        removed = self.store.remove(task_id)
        if removed:
            index, task = removed
            self.refresh()
            self._toast(f"Deleted “{task.title}”", lambda: self.store.insert(index, task))

    def on_clear_completed(self, *_):
        removed = self.store.clear_completed()
        if not removed:
            return

        def undo():
            for index, task in removed:
                self.store.insert(index, task)

        self.refresh()
        n = len(removed)
        self._toast(f"Cleared {n} completed task{'' if n == 1 else 's'}", undo)

    def on_edit(self, task_id: str):
        task = self.store.get(task_id)
        if not task:
            return
        entry = Gtk.Entry(text=task.title, activates_default=True)
        dialog = Adw.AlertDialog(heading="Edit task", extra_child=entry)
        dialog.add_response("cancel", "Cancel")
        dialog.add_response("save", "Save")
        dialog.set_response_appearance("save", Adw.ResponseAppearance.SUGGESTED)
        dialog.set_default_response("save")
        dialog.set_close_response("cancel")

        def on_response(_dialog, response):
            if response == "save":
                self.store.rename(task_id, entry.get_text())
                self.refresh()

        dialog.connect("response", on_response)
        dialog.present(self)

    def on_filter_toggled(self, button: Gtk.ToggleButton, key: str):
        if button.get_active():
            self.filter = key
            self.refresh()


class TodoApp(Adw.Application):
    def __init__(self):
        super().__init__(application_id=APP_ID, flags=Gio.ApplicationFlags.DEFAULT_FLAGS)

    def do_startup(self):
        Adw.Application.do_startup(self)
        quit_action = Gio.SimpleAction(name="quit")
        quit_action.connect("activate", lambda *_: self.quit())
        self.add_action(quit_action)
        self.set_accels_for_action("app.quit", ["<Control>q"])
        self.set_accels_for_action("win.focus-entry", ["<Control>n", "<Control>l"])

    def do_activate(self):
        window = self.props.active_window or TodoWindow(self, TaskStore())
        window.present()


def main() -> int:
    return TodoApp().run(sys.argv)
