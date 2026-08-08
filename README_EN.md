# Task Tracker — Desktop Task Progress Widget for Claude Code

[中文](README.md) | **English**

An always-on-top desktop widget that shows your task list and progress in real time. Claude Code writes the task list to a JSON file during long conversations, and this widget keeps the full picture on your screen — so you never lose track of what's left to do, even after going deep on one step.

## Download

[⬇ Download TaskTracker.exe (v0.1.0)](https://github.com/ajin2002-boop/Task-Tracker-Claude-Code-/releases/download/v0.1.0/TaskTracker.exe)

Windows: download the exe and double-click to run. **No Python installation required.**

## The Problem It Solves

When working with Claude Code on multi-step tasks, the task list scrolls out of view as the conversation grows. Once you spend a long time on a single step, it's easy to lose the overall task trajectory, forcing you to ask the agent "where are we again?" — wasting tokens.

This tool keeps the task list **permanently on your desktop**:
- Full task list + progress bar + subtasks at a glance
- The agent checks off each step automatically
- Subtasks that emerge mid-conversation are added to the list automatically

## How It Works

```
You ask Claude to do a multi-step task
        ↓
Claude writes the task list to ~/.claude-tasks/tasks.json (per CLAUDE.md)
        ↓
The desktop widget refreshes within 1 second, showing the list + progress
        ↓
Claude completes a step → updates done → the widget checks it off automatically
```

- **Frontend**: Python + tkinter (light theme, always-on-top, resizable, auto-refresh via 1s polling)
- **Data source**: `~/.claude-tasks/tasks.json` (plain JSON, human-readable and editable)
- **Integration**: Auto-configured on first run — no manual steps needed

## Quick Start

### 1. Download and run

[⬇ Download TaskTracker.exe](https://github.com/ajin2002-boop/Task-Tracker-Claude-Code-/releases/download/v0.1.0/TaskTracker.exe) and double-click it. **No Python installation or manual configuration required.**

To run from source (development):

```bash
python task_tracker.py
```

On Windows you can also double-click `启动悬浮窗.bat` (runs in the background with `pythonw`).

### 2. Automatic Claude Code integration

**On first launch, the app automatically (invisible to you):**
- Creates the `~/.claude-tasks/` directory and `tasks.json`
- Checks `~/.claude/CLAUDE.md` and writes/appends the task-maintenance instructions

From then on, Claude writes the task list before starting a multi-step task and keeps it updated as it works — **you don't have to do anything**.

### 3. Example

`sample_tasks.json` is a sample of the task file format. Copy it to `~/.claude-tasks/tasks.json` to try it out.

## Task File Format

```json
{
  "project": "Current task name",
  "updated_at": "2026-08-07T12:40:00+08:00",
  "tasks": [
    {
      "id": "1",
      "title": "Main task title",
      "done": false,
      "subtasks": [
        { "id": "1-1", "title": "Subtask title", "done": false }
      ]
    }
  ]
}
```

- `done`: boolean. Use the main task's `done` when it has no subtasks; mark each subtask individually when it does.
- `updated_at`: update to the current time (ISO 8601) on every write.
- The widget auto-refreshes within 1 second of a file change.

## Customization

Window size, color theme, etc. are defined in the config section at the top of `task_tracker.py` — just change the constants.

- `COLOR_BG` / `COLOR_HEADER` / `COLOR_ACCENT` etc.: colors
- `POLL_INTERVAL_MS`: file-watching interval (default 1000ms)

## License

MIT
