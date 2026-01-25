# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

My-Pomo is a free and open-source Pomodoro timer with a TUI (Text User Interface) built using Python and the Textual framework.

## Commands

```bash
# Setup & sync dependencies
uv sync

# Run the app
uv run my-pomo
# or
uv run python -m my_pomo
```

## Project Structure

```
my-pomo/
├── src/
│   └── my_pomo/
│       ├── __init__.py      # Package init with version
│       ├── __main__.py      # Entry point for python -m my_pomo
│       ├── app.py           # Main Textual app and screen classes
│       ├── database.py      # SQLite database layer
│       └── assets/
│           └── meow.mp3     # Audio notification sound
├── tests/                   # Test directory
├── pyproject.toml           # Package configuration
├── uv.lock                  # uv lock file
└── README.md
```

## Architecture

- **src/my_pomo/app.py**: Main application using Textual TUI framework
  - `PomoApp`: Main app class managing timer state, sequence generation, and UI
  - `TimerFormScreen`: Screen for creating new timers
  - `EditTimerScreen`: Screen for editing/deleting existing timers
  - `SessionLogScreen`: Screen displaying session history via DataTable

- **src/my_pomo/database.py**: SQLite database layer (stores in `~/.my_pomo/timers.db`)
  - `timers` table: Stores timer configurations (name, durations, session counts)
  - `sessions` table: Logs completed pomodoro sessions with timestamps

## Key Concepts

- **Pomodoro Sequence**: Generated dynamically from timer config via `_generate_pomodoro_sequence()`. Alternates between work sessions and breaks (short breaks between sessions, long breaks after configurable intervals).
- **Timer State**: Managed through `sequence_index`, `remaining_time`, and `is_paused` on `PomoApp`
- **Session Tracking**: Sessions are created when timer starts and updated on pause/skip/completion

## Dependencies

- `textual`: TUI framework
- `pyfiglet`: ASCII art for timer display
- `playsound3`: Audio notification (plays `meow.mp3` on session end)
