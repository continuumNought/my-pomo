
import asyncio
from textual.app import App, ComposeResult
from textual.screen import Screen
from textual.widgets import Static, Button, Select, Input, Header, Footer
from textual.validation import Integer
from pyfiglet import Figlet
from database import create_table, add_timer, get_all_timers

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
    }
    #timer.pomodoro {
        color: yellow;
    }
    #timer.break {
        color: green;
    }
    #play-pause-button {
        width: 100%;
        text-align: center;
        color: white;
    }
    #timer-selector {
        width: 100%;
        margin-bottom: 1;
    }
    """

    POMODORO_SEQUENCE = [
        ("Pomodoro", 25 * 60),
        ("Short Break", 5 * 60),
        ("Pomodoro", 25 * 60),
        ("Long Break", 10 * 60),
        ("Pomodoro", 25 * 60),
        ("Short Break", 5 * 60),
        ("Pomodoro", 25 * 60),
    ]

    def __init__(self):
        super().__init__()
        create_table()
        if not get_all_timers():
            add_timer("Pomodoro", 25, 5, 10, 4, 8)
        self.timers = get_all_timers()
        self.sequence_index = 0
        self.remaining_time = self.POMODORO_SEQUENCE[0][1]
        self._timer = None
        self.figlet = Figlet(font='big', justify='center')
        self.is_paused = True

    def compose(self) -> ComposeResult:
        """Create child widgets."""
        timers = [(timer['name'], timer['id']) for timer in self.timers]
        timers.append(("Add new timer...", "add_new_timer"))
        yield Select(timers, id="timer-selector")
        yield Static(id="timer")
        yield Button("▶", id="play-pause-button")

    def on_mount(self) -> None:
        """Event handler called when the app is mounted."""
        self.update_timer_class()
        self.update_timer_display()
        self._timer = self.set_interval(1, self.tick)
        self._timer.pause()

    def on_select_changed(self, event: Select.Changed) -> None:
        if event.value == "add_new_timer":
            self.push_screen(TimerFormScreen())

    def add_new_timer(self, name, session_length, short_break, long_break, short_per_long, total_sessions):
        add_timer(name, int(session_length), int(short_break), int(long_break), int(short_per_long), int(total_sessions))
        self.timers = get_all_timers()
        select = self.query_one(Select)
        timers = [(timer['name'], timer['id']) for timer in self.timers]
        timers.append(("Add new timer...", "add_new_timer"))
        select.set_options(timers)
        self.pop_screen()


    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Event handler called when the button is pressed."""
        if event.button.id == "play-pause-button":
            if self.is_paused:
                self._timer.resume()
                event.button.label = "❚❚"
            else:
                self._timer.pause()
                event.button.label = "▶"
            self.is_paused = not self.is_paused

    def tick(self) -> None:
        """Called every second to update the timer."""
        self.remaining_time -= 1
        if self.remaining_time < 0:
            self.sequence_index += 1
            if self.sequence_index < len(self.POMODORO_SEQUENCE):
                self.remaining_time = self.POMODORO_SEQUENCE[self.sequence_index][1]
                self.update_timer_class()
            else:
                self._timer.stop()
                self.exit()
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
