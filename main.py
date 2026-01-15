
import asyncio
from textual.app import App, ComposeResult
from textual.widgets import Static, Button
from pyfiglet import Figlet

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
        self.sequence_index = 0
        self.remaining_time = self.POMODORO_SEQUENCE[0][1]
        self._timer = None
        self.figlet = Figlet(font='big', justify='center')
        self.is_paused = True

    def compose(self) -> ComposeResult:
        """Create child widgets."""
        yield Static(id="timer")
        yield Button("▶", id="play-pause-button")

    def on_mount(self) -> None:
        """Event handler called when the app is mounted."""
        self.update_timer_class()
        self.update_timer_display()
        self._timer = self.set_interval(1, self.tick)
        self._timer.pause()

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
