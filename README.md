# To-Do for Linux

A simple, native-looking to-do app for Ubuntu / GNOME, written in Python with GTK4 and libadwaita.

## Features

- Add, edit, check off and delete tasks
- Filter by All / Active / Done
- Clear all completed tasks at once
- Undo for deletes and clears
- Follows the system light/dark theme
- Tasks saved automatically to `~/.local/share/todo-linux/tasks.json`

## Requirements

Ubuntu 24.04 or newer already ships everything needed. If something is missing:

```bash
sudo apt install python3-gi gir1.2-gtk-4.0 gir1.2-adw-1
```

## Run

```bash
python3 -m todo
```

## Add to the app launcher

```bash
./install.sh             # adds "To-Do" to your app menu and a `todo-linux` command
./install.sh --uninstall # removes them (your tasks are kept)
```

The launcher points at this folder, so don't move it after installing (or re-run `install.sh` if you do).

## Keyboard shortcuts

| Shortcut           | Action                 |
| ------------------ | ---------------------- |
| Enter              | Add the typed task     |
| Ctrl+N / Ctrl+L    | Jump to the task entry |
| Ctrl+Q             | Quit                   |

## Tests

```bash
python3 -m unittest
```
