import datetime
from importlib.resources import files
from typing import Optional

from textual.app import App, ComposeResult
from textual.screen import Screen
from textual.containers import Horizontal
from textual.widgets import Static, Button, Select, Input, Header, Footer, DataTable
from textual.validation import Integer
from pyfiglet import Figlet
from playsound3 import playsound  # type: ignore

from my_pomo.core import (
    TimerConfig,
    PomodoroTimer,
    TimerRepository,
    SessionRepository,
)

# Get path to assets directory
ASSETS_DIR = files("my_pomo").joinpath("assets")


class SessionLogScreen(Screen):
    def __init__(self, session_repo: SessionRepository) -> None:
        super().__init__()
        self._session_repo = session_repo

    def compose(self) -> ComposeResult:
        yield Header("Session Log")
        yield DataTable()
        yield Button("Back", id="back")
        yield Footer()

    def on_mount(self) -> None:
        table = self.query_one(DataTable)
        table.add_columns("ID", "Timer ID", "Start", "Stop", "Sessions", "Short Breaks", "Long Breaks")
        sessions = self._session_repo.get_all()
        for session in sessions:
            table.add_row(
                session["id"],
                session["timer_id"],
                session["start_timestamp"],
                session["stop_timestamp"],
                session["sessions_completed"],
                session["short_breaks_completed"],
                session["long_breaks_completed"],
            )

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "back":
            self.app.pop_screen()


class TimerFormScreen(Screen):
    def __init__(self, timer_repo: TimerRepository) -> None:
        super().__init__()
        self._timer_repo = timer_repo

    def compose(self) -> ComposeResult:
        yield Header("Add New Timer")
        yield Input(placeholder="Timer Name", id="name")
        yield Input(placeholder="Session Length (minutes)", id="session_length", validators=[Integer()])
        yield Input(placeholder="Short Break (minutes)", id="short_break", validators=[Integer()])
        yield Input(placeholder="Long Break (minutes)", id="long_break", validators=[Integer()])
        yield Input(placeholder="Short breaks per long break", id="short_per_long", validators=[Integer()])
        yield Input(placeholder="Total sessions", id="total_sessions", validators=[Integer()])
        yield Button("Save", id="save_timer")
        yield Footer()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "save_timer":
            name = self.query_one("#name", Input).value
            session_length = int(self.query_one("#session_length", Input).value)
            short_break = int(self.query_one("#short_break", Input).value)
            long_break = int(self.query_one("#long_break", Input).value)
            short_per_long = int(self.query_one("#short_per_long", Input).value)
            total_sessions = int(self.query_one("#total_sessions", Input).value)
            self._timer_repo.create(name, session_length, short_break, long_break, short_per_long, total_sessions)
            self.app.refresh_timers()
            self.app.pop_screen()


class EditTimerScreen(Screen):
    def __init__(self, timer_config: TimerConfig, timer_repo: TimerRepository) -> None:
        super().__init__()
        self._timer_config = timer_config
        self._timer_repo = timer_repo

    def compose(self) -> ComposeResult:
        yield Header(f"Edit Timer: {self._timer_config.name}")
        yield Input(value=self._timer_config.name, id="name")
        yield Input(value=str(self._timer_config.session_length), id="session_length", validators=[Integer()])
        yield Input(value=str(self._timer_config.short_break), id="short_break", validators=[Integer()])
        yield Input(value=str(self._timer_config.long_break), id="long_break", validators=[Integer()])
        yield Input(value=str(self._timer_config.short_per_long), id="short_per_long", validators=[Integer()])
        yield Input(value=str(self._timer_config.total_sessions), id="total_sessions", validators=[Integer()])
        with Horizontal(id="buttons-container"):
            yield Button("Save", id="save_timer")
            yield Button("Delete", id="delete_timer", variant="error")
            yield Button("Back", id="back")
        yield Footer()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "save_timer":
            updated_config = TimerConfig(
                id=self._timer_config.id,
                name=self.query_one("#name", Input).value,
                session_length=int(self.query_one("#session_length", Input).value),
                short_break=int(self.query_one("#short_break", Input).value),
                long_break=int(self.query_one("#long_break", Input).value),
                short_per_long=int(self.query_one("#short_per_long", Input).value),
                total_sessions=int(self.query_one("#total_sessions", Input).value),
            )
            self._timer_repo.update(updated_config)
            self.app.refresh_timers(self._timer_config.id)
            self.app.pop_screen()
        elif event.button.id == "delete_timer":
            self._timer_repo.delete(self._timer_config.id)
            self.app.refresh_timers(new_current_timer_id=None)
            self.app.pop_screen()
        elif event.button.id == "back":
            self.app.pop_screen()


class PomoApp(App):
    """A basic Pomodoro timer app."""

    CSS = """
    Screen {
        align: center middle;
    }
    #timer {
        padding: 0;
        margin-top: 8;
    }
    #timer.pomodoro {
        color: yellow;
    }
    #timer.break {
        color: cyan;
    }
    #play-pause-button {
        color: white;
    }
    #buttons-container {
        width: 100%;
        align: center middle;
        margin-top: 1;
    }
    """

    def __init__(self):
        super().__init__()
        self._timer_repo = TimerRepository()
        self._session_repo = SessionRepository()
        self._timer_repo.ensure_default_exists()

        self._timer_configs = self._timer_repo.get_all()
        self._current_timer_id: Optional[int] = self._timer_configs[0].id if self._timer_configs else None
        self._current_session_id: Optional[int] = None

        # Initialize the pomodoro timer
        if self._current_timer_id:
            config = self._timer_repo.get_by_id(self._current_timer_id)
            self._pomo_timer = PomodoroTimer(config)
        else:
            self._pomo_timer = None

        self._ui_timer = None
        self.figlet = Figlet(font="big", justify="center")

    def compose(self) -> ComposeResult:
        """Create child widgets."""
        timers = [(t.name, t.id) for t in self._timer_configs]
        timers.append(("Add new timer...", "add_new_timer"))
        yield Select(timers, id="timer-selector", value=self._current_timer_id)
        yield Static(id="timer")
        with Horizontal(id="buttons-container"):
            yield Button("\u25b6\ufe0f", id="play-pause-button")
            yield Button("\u23e9", id="fast-forward-button")
            yield Button("\U0001f504", id="restart-button")
            yield Button("\u2699\ufe0f", id="settings-button")
            yield Button("\u270f\ufe0f", id="edit-timer-button")

    def on_mount(self) -> None:
        """Event handler called when the app is mounted."""
        self._update_timer_class()
        self._update_timer_display()
        self._ui_timer = self.set_interval(1, self._tick)
        self._ui_timer.pause()

    def refresh_timers(self, new_current_timer_id: Optional[int] = None) -> None:
        """Refresh the timers in the select."""
        self._timer_configs = self._timer_repo.get_all()
        select = self.query_one(Select)
        timers = [(t.name, t.id) for t in self._timer_configs]
        timers.append(("Add new timer...", "add_new_timer"))
        select.set_options(timers)

        if new_current_timer_id is None:
            self._current_timer_id = self._timer_configs[0].id if self._timer_configs else None
        else:
            self._current_timer_id = new_current_timer_id

        select.value = self._current_timer_id
        self._current_session_id = None

        if self._current_timer_id:
            config = self._timer_repo.get_by_id(self._current_timer_id)
            self._pomo_timer = PomodoroTimer(config)
        else:
            self._pomo_timer = None

        self._ui_timer.pause()
        self.query_one("#play-pause-button", Button).label = "\u25b6\ufe0f"
        self._update_timer_class()
        self._update_timer_display()

    def on_select_changed(self, event: Select.Changed) -> None:
        if event.value == Select.BLANK:
            return
        if event.value == "add_new_timer":
            self.push_screen(TimerFormScreen(self._timer_repo))
        else:
            self._current_timer_id = event.value
            self._current_session_id = None
            config = self._timer_repo.get_by_id(self._current_timer_id)
            self._pomo_timer = PomodoroTimer(config)
            self._ui_timer.pause()
            self.query_one("#play-pause-button", Button).label = "\u25b6\ufe0f"
            self._update_timer_class()
            self._update_timer_display()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Event handler called when the button is pressed."""
        if event.button.id == "play-pause-button":
            self._handle_play_pause(event.button)
        elif event.button.id == "fast-forward-button":
            self._skip_session()
        elif event.button.id == "restart-button":
            self._restart_current_timer()
        elif event.button.id == "settings-button":
            self.push_screen(SessionLogScreen(self._session_repo))
        elif event.button.id == "edit-timer-button":
            if self._current_timer_id:
                config = self._timer_repo.get_by_id(self._current_timer_id)
                self.push_screen(EditTimerScreen(config, self._timer_repo))

    def _handle_play_pause(self, button: Button) -> None:
        """Handle play/pause button press."""
        if not self._pomo_timer:
            return

        if not self._pomo_timer.is_running:
            self._pomo_timer.start()
            self._ui_timer.resume()
            button.label = "\u23f8\ufe0f"
            if self._current_session_id is None:
                self._current_session_id = self._session_repo.create(self._current_timer_id)
            else:
                sessions, short_breaks, long_breaks = self._pomo_timer.get_completed_counts()
                self._session_repo.update(self._current_session_id, None, sessions, short_breaks, long_breaks)
        else:
            self._pomo_timer.pause()
            self._ui_timer.pause()
            button.label = "\u25b6\ufe0f"
            sessions, short_breaks, long_breaks = self._pomo_timer.get_completed_counts()
            stop_time = datetime.datetime.now().isoformat()
            self._session_repo.update(self._current_session_id, stop_time, sessions, short_breaks, long_breaks)

    def _restart_current_timer(self) -> None:
        """Resets the current timer to its starting state."""
        if not self._pomo_timer:
            return

        self._pomo_timer.restart()
        self._ui_timer.pause()
        self.query_one("#play-pause-button", Button).label = "\u25b6\ufe0f"
        self._current_session_id = None
        self._update_timer_class()
        self._update_timer_display()

    def _skip_session(self, play_sound: bool = False) -> None:
        """Skips the current session."""
        if not self._pomo_timer:
            return

        if play_sound:
            sound_file = ASSETS_DIR / "meow.mp3"
            playsound(str(sound_file))

        has_more = self._pomo_timer.skip()

        if has_more:
            self._update_timer_class()
            if self._current_session_id is not None:
                sessions, short_breaks, long_breaks = self._pomo_timer.get_completed_counts()
                self._session_repo.update(self._current_session_id, None, sessions, short_breaks, long_breaks)
            self._update_timer_display()
        else:
            # Sequence complete
            self._ui_timer.pause()
            if self._current_session_id is not None:
                sessions, short_breaks, long_breaks = self._pomo_timer.get_completed_counts()
                stop_time = datetime.datetime.now().isoformat()
                self._session_repo.update(self._current_session_id, stop_time, sessions, short_breaks, long_breaks)

            self.query_one("#play-pause-button", Button).label = "\u25b6\ufe0f"
            self._current_session_id = None
            self._update_timer_class()
            self._update_timer_display()

    def _tick(self) -> None:
        """Called every second to update the timer."""
        if not self._pomo_timer:
            return

        phase_changed = self._pomo_timer.tick()
        if phase_changed:
            # Play sound on phase change
            sound_file = ASSETS_DIR / "meow.mp3"
            playsound(str(sound_file))

            # Update session stats
            if self._current_session_id is not None:
                sessions, short_breaks, long_breaks = self._pomo_timer.get_completed_counts()
                self._session_repo.update(self._current_session_id, None, sessions, short_breaks, long_breaks)

            # Check if sequence complete
            if self._pomo_timer.is_complete or not self._pomo_timer.is_running:
                self._ui_timer.pause()
                if self._current_session_id is not None:
                    sessions, short_breaks, long_breaks = self._pomo_timer.get_completed_counts()
                    stop_time = datetime.datetime.now().isoformat()
                    self._session_repo.update(self._current_session_id, stop_time, sessions, short_breaks, long_breaks)
                self.query_one("#play-pause-button", Button).label = "\u25b6\ufe0f"
                self._current_session_id = None

            self._update_timer_class()
        self._update_timer_display()

    def _update_timer_class(self) -> None:
        """Update the timer's CSS class based on the current session."""
        if not self._pomo_timer:
            return

        timer_widget = self.query_one("#timer")
        if self._pomo_timer.is_break:
            timer_widget.remove_class("pomodoro")
            timer_widget.add_class("break")
        else:
            timer_widget.remove_class("break")
            timer_widget.add_class("pomodoro")

    def _update_timer_display(self) -> None:
        """Update the timer display."""
        if not self._pomo_timer:
            return

        minutes, seconds = divmod(self._pomo_timer.remaining_seconds, 60)
        timer_str = f"{minutes:02d}:{seconds:02d}"
        self.figlet.width = self.console.width
        self.query_one("#timer", Static).update(self.figlet.renderText(timer_str))
