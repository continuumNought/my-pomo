
import asyncio
import datetime
from textual.app import App, ComposeResult
from textual.screen import Screen
from textual.containers import Horizontal
from textual.widgets import Static, Button, Select, Input, Header, Footer, DataTable
from textual.validation import Integer
from pyfiglet import Figlet
from database import create_tables, add_timer, get_all_timers, get_timer_by_id, create_session, update_session, get_all_sessions
from playsound3 import playsound # type: ignore

class SessionLogScreen(Screen):
    def compose(self) -> ComposeResult:
        yield Header("Session Log")
        yield DataTable()
        yield Button("Back", id="back")
        yield Footer()

    def on_mount(self) -> None:
        table = self.query_one(DataTable)
        table.add_columns("ID", "Timer ID", "Start", "Stop", "Sessions", "Short Breaks", "Long Breaks")
        sessions = get_all_sessions()
        for session in sessions:
            table.add_row(session['id'], session['timer_id'], session['start_timestamp'], session['stop_timestamp'], session['sessions_completed'], session['short_breaks_completed'], session['long_breaks_completed'])

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "back":
            self.app.pop_screen()

class TimerFormScreen(Screen):
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
            session_length = self.query_one("#session_length", Input).value
            short_break = self.query_one("#short_break", Input).value
            long_break = self.query_one("#long_break", Input).value
            short_per_long = self.query_one("#short_per_long", Input).value
            total_sessions = self.query_one("#total_sessions", Input).value
            self.app.add_new_timer(name, session_length, short_break, long_break, short_per_long, total_sessions)


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
        create_tables()
        if not get_all_timers():
            add_timer("Pomodoro", 25, 5, 10, 4, 8)
        self.timers = get_all_timers()
        self.current_timer_id = self.timers[0]['id'] if self.timers else None
        self.current_session_id = None
        self.POMODORO_SEQUENCE = self._generate_pomodoro_sequence(get_timer_by_id(self.current_timer_id)) if self.current_timer_id else []
        self.sequence_index = 0
        self.remaining_time = self.POMODORO_SEQUENCE[0][1] if self.POMODORO_SEQUENCE else 0
        self._timer = None
        self.figlet = Figlet(font='big', justify='center')
        self.is_paused = True

    def _generate_pomodoro_sequence(self, timer_data):
        if not timer_data:
            return []
        session_len = timer_data['session_length'] * 60
        short_break_len = timer_data['short_break'] * 60
        long_break_len = timer_data['long_break'] * 60
        short_per_long = timer_data['short_per_long'] + 1
        total_sessions = timer_data['total_sessions']

        sequence = []
        sessions_done = 0
        while sessions_done < total_sessions:
            sequence.append(("Pomodoro", session_len))
            sessions_done += 1
            if sessions_done % short_per_long == 0 and sessions_done < total_sessions:
                sequence.append(("Long Break", long_break_len))
            elif sessions_done < total_sessions:
                sequence.append(("Short Break", short_break_len))
        return sequence

    def compose(self) -> ComposeResult:
        """Create child widgets."""
        timers = [(timer['name'], timer['id']) for timer in self.timers]
        timers.append(("Add new timer...", "add_new_timer"))
        yield Select(timers, id="timer-selector", value=self.current_timer_id)
        yield Static(id="timer")
        with Horizontal(id="buttons-container"):
            yield Button("▶️", id="play-pause-button")
            yield Button("⏩", id="fast-forward-button")
            yield Button("🔄", id="restart-button")
            yield Button("⚙️", id="settings-button")

    def on_mount(self) -> None:
        """Event handler called when the app is mounted."""
        self.update_timer_class()
        self.update_timer_display()
        self._timer = self.set_interval(1, self.tick)
        self._timer.pause()

    def on_select_changed(self, event: Select.Changed) -> None:
        if event.value == Select.BLANK:
            return
        if event.value == "add_new_timer":
            self.push_screen(TimerFormScreen())
        else:
            self.current_timer_id = event.value
            self.current_session_id = None # Reset session on timer change
            selected_timer_data = get_timer_by_id(self.current_timer_id)
            self.POMODORO_SEQUENCE = self._generate_pomodoro_sequence(selected_timer_data)
            self.sequence_index = 0
            self.remaining_time = self.POMODORO_SEQUENCE[0][1] if self.POMODORO_SEQUENCE else 0
            self._timer.pause()
            self.query_one("#play-pause-button", Button).label = "▶️"
            self.is_paused = True
            self.update_timer_class()
            self.update_timer_display()

    def add_new_timer(self, name, session_length, short_break, long_break, short_per_long, total_sessions):
        add_timer(name, int(session_length), int(short_break), int(long_break), int(short_per_long), int(total_sessions))
        self.timers = get_all_timers()
        select = self.query_one(Select)
        timers = [(timer['name'], timer['id']) for timer in self.timers]
        timers.append(("Add new timer...", "add_new_timer"))
        select.set_options(timers)
        self.pop_screen()

    def _get_completed_counts(self):
        sessions = 0
        short_breaks = 0
        long_breaks = 0
        for i in range(self.sequence_index):
            event_name, _ = self.POMODORO_SEQUENCE[i]
            if event_name == "Pomodoro":
                sessions += 1
            elif event_name == "Short Break":
                short_breaks += 1
            elif event_name == "Long Break":
                long_breaks += 1
        return sessions, short_breaks, long_breaks

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Event handler called when the button is pressed."""
        if event.button.id == "play-pause-button":
            if self.is_paused:
                self._timer.resume()
                event.button.label = "⏸️"
                if self.current_session_id is None:
                    self.current_session_id = create_session(self.current_timer_id)
                else:
                    sessions, short_breaks, long_breaks = self._get_completed_counts()
                    update_session(self.current_session_id, None, sessions, short_breaks, long_breaks)
            else:
                self._timer.pause()
                event.button.label = "▶️"
                sessions, short_breaks, long_breaks = self._get_completed_counts()
                stop_time = datetime.datetime.now().isoformat()
                update_session(self.current_session_id, stop_time, sessions, short_breaks, long_breaks)
            self.is_paused = not self.is_paused
        elif event.button.id == "fast-forward-button":
            self.skip_session()
        elif event.button.id == "restart-button":
            self.restart_current_timer()
        elif event.button.id == "settings-button":
            self.push_screen(SessionLogScreen())


    def restart_current_timer(self):
        """Resets the current timer to its starting state."""
        self._timer.pause()
        self.is_paused = True
        self.query_one("#play-pause-button", Button).label = "▶️"
        self.remaining_time = self.POMODORO_SEQUENCE[self.sequence_index][1]
        self.update_timer_display()


    def skip_session(self, play_sound: bool = False):
        """Skips the current session."""
        if play_sound:
            # User needs to provide a 'session_end.wav' file in the project root for sound to play.
            playsound('./meow.mp3')
        self.sequence_index += 1
        if self.sequence_index < len(self.POMODORO_SEQUENCE):
            self.remaining_time = self.POMODORO_SEQUENCE[self.sequence_index][1]
            self.update_timer_class()
            if self.current_session_id is not None:
                sessions, short_breaks, long_breaks = self._get_completed_counts()
                update_session(self.current_session_id, None, sessions, short_breaks, long_breaks)
            self.update_timer_display()
        else:
            self._timer.pause()
            if self.current_session_id is not None:
                sessions, short_breaks, long_breaks = self._get_completed_counts()
                stop_time = datetime.datetime.now().isoformat()
                update_session(self.current_session_id, stop_time, sessions, short_breaks, long_breaks)

            self.sequence_index = 0
            self.remaining_time = self.POMODORO_SEQUENCE[0][1] if self.POMODORO_SEQUENCE else 0
            self.is_paused = True
            self.query_one("#play-pause-button", Button).label = "▶️"
            self.current_session_id = None
            self.update_timer_class()
            self.update_timer_display()


    def tick(self) -> None:
        """Called every second to update the timer."""
        self.remaining_time -= 1
        if self.remaining_time < 0:
            self.skip_session(play_sound=True)
            return
        self.update_timer_display()

    def update_timer_class(self) -> None:
        """Update the timer's CSS class based on the current session."""
        name, _ = self.POMODORO_SEQUENCE[self.sequence_index]
        timer = self.query_one("#timer")
        if "Break" in name:
            timer.remove_class("pomodoro")
            timer.add_class("break")
        else:
            timer.remove_class("break")
            timer.add_class("pomodoro")

    def update_timer_display(self) -> None:
        """Update the timer display."""
        if self.sequence_index < len(self.POMODORO_SEQUENCE):
            name, _ = self.POMODORO_SEQUENCE[self.sequence_index]
            minutes, seconds = divmod(self.remaining_time, 60)
            timer_str = f"{minutes:02d}:{seconds:02d}"
            self.figlet.width = self.console.width
            self.query_one("#timer", Static).update(self.figlet.renderText(timer_str))

if __name__ == "__main__":
    app = PomoApp()
    app.run()
