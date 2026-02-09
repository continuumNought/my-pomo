import datetime
from importlib.resources import files
from typing import Optional

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.reactive import reactive
from textual.screen import Screen
from textual.containers import Horizontal
from textual.widgets import Static, Button, Select, Input, Header, Footer, DataTable
from textual.validation import Integer
from textual import on
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
    """Screen displaying a table of completed pomodoro sessions."""

    def __init__(self, session_repo: SessionRepository) -> None:
        """Initialize the session log screen.

        Args:
            session_repo: Repository for fetching session data.
        """
        super().__init__()
        self._session_repo = session_repo

    def compose(self) -> ComposeResult:
        """Create child widgets for the session log screen."""
        yield Header("Session Log")
        yield DataTable()
        yield Button("Back", id="back")
        yield Footer()

    def on_mount(self) -> None:
        """Populate the data table with session history when the screen is mounted."""
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

    @on(Button.Pressed, "#back")
    def handle_back(self, event: Button.Pressed) -> None:
        """Dismiss the screen when the back button is pressed."""
        self.dismiss()


class TimerFormScreen(Screen):
    """Screen for creating a new timer configuration."""

    def __init__(self, timer_repo: TimerRepository) -> None:
        """Initialize the timer form screen.

        Args:
            timer_repo: Repository for persisting timer configurations.
        """
        super().__init__()
        self._timer_repo = timer_repo

    def compose(self) -> ComposeResult:
        """Create the form widgets for timer configuration."""
        yield Header("Add New Timer")
        yield Input(placeholder="Timer Name", id="name")
        yield Input(placeholder="Session Length (minutes)", id="session_length", validators=[Integer()])
        yield Input(placeholder="Short Break (minutes)", id="short_break", validators=[Integer()])
        yield Input(placeholder="Long Break (minutes)", id="long_break", validators=[Integer()])
        yield Input(placeholder="Short breaks per long break", id="short_per_long", validators=[Integer()])
        yield Input(placeholder="Total sessions", id="total_sessions", validators=[Integer()])
        yield Button("Save", id="save_timer")
        yield Footer()

    @on(Button.Pressed, "#save_timer")
    def handle_save(self, event: Button.Pressed) -> None:
        """Validate form inputs and save the new timer configuration."""
        name = self.query_one("#name", Input).value.strip()
        if not name:
            self.notify("Timer name is required", severity="error")
            self.query_one("#name", Input).focus()
            return

        numeric_fields = ["session_length", "short_break", "long_break", "short_per_long", "total_sessions"]
        for field_id in numeric_fields:
            inp = self.query_one(f"#{field_id}", Input)
            try:
                int(inp.value)
            except (ValueError, TypeError):
                self.notify(f"{inp.placeholder} must be a valid integer", severity="error")
                inp.focus()
                return

        self._timer_repo.create(
            name,
            int(self.query_one("#session_length", Input).value),
            int(self.query_one("#short_break", Input).value),
            int(self.query_one("#long_break", Input).value),
            int(self.query_one("#short_per_long", Input).value),
            int(self.query_one("#total_sessions", Input).value),
        )
        self.notify(f"Timer '{name}' created")
        self.dismiss(True)


class EditTimerScreen(Screen):
    """Screen for editing or deleting an existing timer configuration."""

    def __init__(self, timer_config: TimerConfig, timer_repo: TimerRepository) -> None:
        """Initialize the edit timer screen.

        Args:
            timer_config: The timer configuration to edit.
            timer_repo: Repository for persisting timer configurations.
        """
        super().__init__()
        self._timer_config = timer_config
        self._timer_repo = timer_repo

    def compose(self) -> ComposeResult:
        """Create the form widgets pre-populated with the timer's current values."""
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

    @on(Button.Pressed, "#save_timer")
    def handle_save(self, event: Button.Pressed) -> None:
        """Validate form inputs and update the timer configuration."""
        name = self.query_one("#name", Input).value.strip()
        if not name:
            self.notify("Timer name is required", severity="error")
            self.query_one("#name", Input).focus()
            return

        numeric_fields = ["session_length", "short_break", "long_break", "short_per_long", "total_sessions"]
        for field_id in numeric_fields:
            inp = self.query_one(f"#{field_id}", Input)
            try:
                int(inp.value)
            except (ValueError, TypeError):
                self.notify(f"{inp.placeholder} must be a valid integer", severity="error")
                inp.focus()
                return

        updated_config = TimerConfig(
            id=self._timer_config.id,
            name=name,
            session_length=int(self.query_one("#session_length", Input).value),
            short_break=int(self.query_one("#short_break", Input).value),
            long_break=int(self.query_one("#long_break", Input).value),
            short_per_long=int(self.query_one("#short_per_long", Input).value),
            total_sessions=int(self.query_one("#total_sessions", Input).value),
        )
        self._timer_repo.update(updated_config)
        self.notify(f"Timer '{name}' updated")
        self.dismiss(("saved", self._timer_config.id))

    @on(Button.Pressed, "#delete_timer")
    def handle_delete(self, event: Button.Pressed) -> None:
        """Delete the timer and dismiss the screen."""
        self._timer_repo.delete(self._timer_config.id)
        self.notify(f"Timer '{self._timer_config.name}' deleted")
        self.dismiss(("deleted", None))

    @on(Button.Pressed, "#back")
    def handle_back(self, event: Button.Pressed) -> None:
        """Dismiss the screen without saving changes."""
        self.dismiss(None)


class PomoApp(App):
    """A basic Pomodoro timer app."""

    CSS_PATH = "app.tcss"
    TITLE = "My Pomo"
    BINDINGS = [
        Binding("p", "play", "Play"),
        Binding("p", "pause", "Pause"),
        ("s", "skip", "Skip"),
        ("w", "rewind", "Rewind"),
        ("r", "restart", "Restart"),
        ("n", "new_timer", "New"),
        ("e", "edit", "Edit"),
        ("l", "session_log", "Log"),
        ("q", "quit", "Quit"),
    ]

    is_break: reactive[bool] = reactive(False)
    remaining_seconds: reactive[int] = reactive(0)

    def __init__(self):
        """Initialize the Pomodoro app with repositories and figlet renderer."""
        super().__init__()
        self.figlet = Figlet(font="big", justify="center")
        self._timer_repo = TimerRepository()
        self._session_repo = SessionRepository()
        self._pomo_timer = None

    def compose(self) -> ComposeResult:
        """Create child widgets."""
        yield Header()
        yield Select([], id="timer-selector", prompt="Timer")
        yield Static(id="timer")
        yield Footer()

    def on_mount(self) -> None:
        """Event handler called when the app is mounted."""
        self._timer_repo.ensure_default_exists()

        self._timer_configs = self._timer_repo.get_all()
        self._current_timer_id: Optional[int] = self._timer_configs[0].id if self._timer_configs else None
        self._current_session_id: Optional[int] = None

        # Populate the select widget
        select = self.query_one(Select)
        timers = [(t.name, t.id) for t in self._timer_configs]
        select.set_options(timers)
        select.value = self._current_timer_id

        # Initialize the pomodoro timer
        if self._current_timer_id:
            config = self._timer_repo.get_by_id(self._current_timer_id)
            self._pomo_timer = PomodoroTimer(config)
        else:
            self._pomo_timer = None

        self._sync_reactive_from_timer()

        self._ui_timer = self.set_interval(1, self._tick)
        self._ui_timer.pause()

    def watch_is_break(self, on_break: bool) -> None:
        """Toggle CSS classes on the timer widget when break state changes."""
        try:
            timer_widget = self.query_one("#timer")
        except Exception:
            return
        timer_widget.set_class(on_break, "break")
        timer_widget.set_class(not on_break, "pomodoro")

    def watch_remaining_seconds(self, seconds: int) -> None:
        """Render the figlet text when remaining seconds changes."""
        try:
            timer_widget = self.query_one("#timer", Static)
        except Exception:
            return
        minutes, secs = divmod(seconds, 60)
        timer_str = f"{minutes:02d}:{secs:02d}"
        self.figlet.width = self.console.width
        timer_widget.update(self.figlet.renderText(timer_str))

    def _sync_reactive_from_timer(self) -> None:
        """Sync all reactive attributes from the current PomodoroTimer state."""
        if self._pomo_timer:
            self.is_break = self._pomo_timer.is_break
            self.remaining_seconds = self._pomo_timer.remaining_seconds
            self.sub_title = self._pomo_timer.config.name
        else:
            self.is_break = False
            self.remaining_seconds = 0
            self.sub_title = ""
        self.refresh_bindings()

    def refresh_timers(self, new_current_timer_id: Optional[int] = None) -> None:
        """Refresh the timers in the select."""
        self._timer_configs = self._timer_repo.get_all()
        select = self.query_one(Select)
        timers = [(t.name, t.id) for t in self._timer_configs]
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
        self._sync_reactive_from_timer()

    def _on_timer_form_closed(self, result: object) -> None:
        """Callback when TimerFormScreen is dismissed."""
        if result:
            self.refresh_timers()

    def _on_edit_timer_closed(self, result: object) -> None:
        """Callback when EditTimerScreen is dismissed."""
        if result is None:
            return
        action, timer_id = result
        if action == "saved":
            self.refresh_timers(timer_id)
        elif action == "deleted":
            self.refresh_timers(new_current_timer_id=None)

    def _on_session_log_closed(self, result: object) -> None:
        """Callback when SessionLogScreen is dismissed."""
        pass

    def on_select_changed(self, event: Select.Changed) -> None:
        """Handle timer selection changes from the dropdown."""
        if event.value == Select.BLANK:
            return
        self._current_timer_id = event.value
        self._current_session_id = None
        config = self._timer_repo.get_by_id(self._current_timer_id)
        self._pomo_timer = PomodoroTimer(config)
        self._ui_timer.pause()
        self._sync_reactive_from_timer()

    def check_action(self, action: str, parameters: tuple) -> bool | None:
        """Control which actions are enabled based on timer state."""
        if action == "play":
            return not self._pomo_timer or not self._pomo_timer.is_running
        if action == "pause":
            return self._pomo_timer is not None and self._pomo_timer.is_running
        return True

    def action_play(self) -> None:
        """Start the timer."""
        self._handle_play_pause()

    def action_pause(self) -> None:
        """Pause the timer."""
        self._handle_play_pause()

    def action_skip(self) -> None:
        """Skip to the next session or break."""
        self._skip_session()

    def action_rewind(self) -> None:
        """Rewind to the previous session or reset the current one."""
        if self._pomo_timer and self._pomo_timer.rewind():
            self._ui_timer.pause()
            self._sync_reactive_from_timer()

    def action_restart(self) -> None:
        """Restart the entire pomodoro sequence from the beginning."""
        self._restart_current_timer()

    def action_new_timer(self) -> None:
        """Open the new timer form screen."""
        self.push_screen(TimerFormScreen(self._timer_repo), callback=self._on_timer_form_closed)

    def action_edit(self) -> None:
        """Open the edit timer screen for the current timer."""
        if self._current_timer_id:
            config = self._timer_repo.get_by_id(self._current_timer_id)
            self.push_screen(EditTimerScreen(config, self._timer_repo), callback=self._on_edit_timer_closed)

    def action_session_log(self) -> None:
        """Open the session log screen."""
        self.push_screen(SessionLogScreen(self._session_repo), callback=self._on_session_log_closed)

    def _handle_play_pause(self) -> None:
        """Handle play/pause toggle."""
        if not self._pomo_timer:
            return

        if not self._pomo_timer.is_running:
            self._pomo_timer.start()
            self._ui_timer.resume()
            if self._current_session_id is None:
                self._current_session_id = self._session_repo.create(self._current_timer_id)
            else:
                sessions, short_breaks, long_breaks = self._pomo_timer.get_completed_counts()
                self._session_repo.update(self._current_session_id, None, sessions, short_breaks, long_breaks)
        else:
            self._pomo_timer.pause()
            self._ui_timer.pause()
            sessions, short_breaks, long_breaks = self._pomo_timer.get_completed_counts()
            stop_time = datetime.datetime.now().isoformat()
            self._session_repo.update(self._current_session_id, stop_time, sessions, short_breaks, long_breaks)
        self.refresh_bindings()

    def _restart_current_timer(self) -> None:
        """Resets the current timer to its starting state."""
        if not self._pomo_timer:
            return

        self._pomo_timer.restart()
        self._ui_timer.pause()
        self._current_session_id = None
        self._sync_reactive_from_timer()

    def _skip_session(self, play_sound: bool = False) -> None:
        """Skips the current session."""
        if not self._pomo_timer:
            return

        if play_sound:
            sound_file = ASSETS_DIR / "meow.mp3"
            self.run_worker(lambda: playsound(str(sound_file)), exclusive=False, thread=True)

        has_more = self._pomo_timer.skip()

        if has_more:
            if self._current_session_id is not None:
                sessions, short_breaks, long_breaks = self._pomo_timer.get_completed_counts()
                self._session_repo.update(self._current_session_id, None, sessions, short_breaks, long_breaks)
            self._sync_reactive_from_timer()
        else:
            # Sequence complete
            self._ui_timer.pause()
            if self._current_session_id is not None:
                sessions, short_breaks, long_breaks = self._pomo_timer.get_completed_counts()
                stop_time = datetime.datetime.now().isoformat()
                self._session_repo.update(self._current_session_id, stop_time, sessions, short_breaks, long_breaks)

            self._current_session_id = None
            self._sync_reactive_from_timer()

    def _tick(self) -> None:
        """Called every second to update the timer."""
        if not self._pomo_timer:
            return

        phase_changed = self._pomo_timer.tick()
        if phase_changed:
            # Play sound on phase change (in background worker to avoid blocking)
            sound_file = ASSETS_DIR / "meow.mp3"
            self.run_worker(lambda: playsound(str(sound_file)), exclusive=False, thread=True)

            if not self._pomo_timer.is_running:
                # Sequence complete — finalize session, then reset like stop button
                if self._current_session_id is not None:
                    sessions, short_breaks, long_breaks = self._pomo_timer.get_completed_counts()
                    stop_time = datetime.datetime.now().isoformat()
                    self._session_repo.update(self._current_session_id, stop_time, sessions, short_breaks, long_breaks)
                self._current_session_id = None
                self.notify("Pomodoro sequence complete!")
                self._restart_current_timer()
                return

            # Normal phase change — update session stats
            if self._current_session_id is not None:
                sessions, short_breaks, long_breaks = self._pomo_timer.get_completed_counts()
                self._session_repo.update(self._current_session_id, None, sessions, short_breaks, long_breaks)

            self.is_break = self._pomo_timer.is_break
        self.remaining_seconds = self._pomo_timer.remaining_seconds
