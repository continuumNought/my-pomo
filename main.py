
import asyncio
from textual.app import App, ComposeResult
from textual.widgets import Static

class PomoApp(App):
    """A basic Pomodoro timer app."""

    CSS = """
    Screen {
        align: center middle;
    }
    #timer {
        border: thick $primary;
        padding: 1 2;
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

    def compose(self) -> ComposeResult:
        """Create child widgets."""
        yield Static(id="timer")

    def on_mount(self) -> None:
        """Event handler called when the app is mounted."""
        self.update_timer_display()
        self._timer = self.set_interval(1, self.tick)

    def tick(self) -> None:
        """Called every second to update the timer."""
        self.remaining_time -= 1
        if self.remaining_time < 0:
            self.sequence_index += 1
            if self.sequence_index < len(self.POMODORO_SEQUENCE):
                self.remaining_time = self.POMODORO_SEQUENCE[self.sequence_index][1]
            else:
                self._timer.stop()
                self.exit()
                return
        self.update_timer_display()

    def update_timer_display(self) -> None:
        """Update the timer display."""
        if self.sequence_index < len(self.POMODORO_SEQUENCE):
            name, _ = self.POMODORO_SEQUENCE[self.sequence_index]
            minutes, seconds = divmod(self.remaining_time, 60)
            timer_str = f"{name}: {minutes:02d}:{seconds:02d}"
            self.query_one("#timer", Static).update(timer_str)

if __name__ == "__main__":
    app = PomoApp()
    app.run()
