"""Core business logic for the Pomodoro timer, independent of UI framework."""

from dataclasses import dataclass
from typing import Optional

from my_pomo.database import (
    create_tables,
    add_timer,
    get_all_timers,
    get_timer_by_id,
    create_session,
    update_session,
    get_all_sessions,
    update_timer,
    delete_timer,
    Timer,
    PomodoroSession,
)


@dataclass
class TimerConfig:
    """Represents a timer configuration."""

    id: int
    name: str
    session_length: int  # minutes
    short_break: int  # minutes
    long_break: int  # minutes
    short_per_long: int
    total_sessions: int

    @classmethod
    def from_db_model(cls, timer: Optional[Timer]) -> Optional["TimerConfig"]:
        """Create a TimerConfig from a SQLAlchemy Timer model."""
        if timer is None:
            return None
        return cls(
            id=timer.id,
            name=timer.name,
            session_length=timer.session_length,
            short_break=timer.short_break,
            long_break=timer.long_break,
            short_per_long=timer.short_per_long,
            total_sessions=timer.total_sessions,
        )


class PomodoroSequence:
    """Generates and manages the sequence of work/break periods."""

    def __init__(self, config: TimerConfig):
        self._config = config
        self._sequence: list[tuple[str, int]] = []
        self._index = 0
        self._generate_sequence()

    def _generate_sequence(self) -> None:
        """Generate the pomodoro sequence from timer config."""
        session_len = self._config.session_length * 60
        short_break_len = self._config.short_break * 60
        long_break_len = self._config.long_break * 60
        short_per_long = self._config.short_per_long + 1
        total_sessions = self._config.total_sessions

        self._sequence = []
        sessions_done = 0
        while sessions_done < total_sessions:
            self._sequence.append(("Pomodoro", session_len))
            sessions_done += 1
            if sessions_done % short_per_long == 0 and sessions_done < total_sessions:
                self._sequence.append(("Long Break", long_break_len))
            elif sessions_done < total_sessions:
                self._sequence.append(("Short Break", short_break_len))

    def current_phase(self) -> tuple[str, int]:
        """Return the current phase name and duration in seconds."""
        if self._index < len(self._sequence):
            return self._sequence[self._index]
        return ("", 0)

    def advance(self) -> bool:
        """Advance to the next phase. Returns False if sequence complete."""
        self._index += 1
        return self._index < len(self._sequence)

    def reset(self) -> None:
        """Reset to the beginning of the sequence."""
        self._index = 0

    def is_break(self) -> bool:
        """Check if the current phase is a break."""
        name, _ = self.current_phase()
        return "Break" in name

    def is_complete(self) -> bool:
        """Check if the sequence is complete."""
        return self._index >= len(self._sequence)

    @property
    def index(self) -> int:
        """Current index in the sequence."""
        return self._index

    def get_completed_counts(self) -> tuple[int, int, int]:
        """Return counts of completed sessions, short breaks, and long breaks."""
        sessions = 0
        short_breaks = 0
        long_breaks = 0
        for i in range(self._index):
            event_name, _ = self._sequence[i]
            if event_name == "Pomodoro":
                sessions += 1
            elif event_name == "Short Break":
                short_breaks += 1
            elif event_name == "Long Break":
                long_breaks += 1
        return sessions, short_breaks, long_breaks


class PomodoroTimer:
    """Core timer state machine, independent of UI."""

    def __init__(self, config: TimerConfig):
        self._config = config
        self._sequence = PomodoroSequence(config)
        self._remaining_seconds = self._sequence.current_phase()[1]
        self._is_running = False

    @property
    def remaining_seconds(self) -> int:
        """Get remaining seconds in current phase."""
        return self._remaining_seconds

    @property
    def is_running(self) -> bool:
        """Check if timer is running."""
        return self._is_running

    @property
    def current_phase_name(self) -> str:
        """Get the name of the current phase."""
        return self._sequence.current_phase()[0]

    @property
    def is_break(self) -> bool:
        """Check if currently on a break."""
        return self._sequence.is_break()

    @property
    def is_complete(self) -> bool:
        """Check if the entire sequence is complete."""
        return self._sequence.is_complete()

    @property
    def config(self) -> TimerConfig:
        """Get the timer configuration."""
        return self._config

    def start(self) -> None:
        """Start the timer."""
        self._is_running = True

    def pause(self) -> None:
        """Pause the timer."""
        self._is_running = False

    def tick(self) -> bool:
        """
        Decrement timer by one second.
        Returns True if phase changed (time ran out).
        """
        if not self._is_running:
            return False

        self._remaining_seconds -= 1
        if self._remaining_seconds < 0:
            return self._advance_phase()
        return False

    def _advance_phase(self) -> bool:
        """
        Advance to the next phase.
        Returns True if phase changed, False if sequence complete.
        """
        if self._sequence.advance():
            self._remaining_seconds = self._sequence.current_phase()[1]
            return True
        else:
            # Sequence complete, reset
            self._sequence.reset()
            self._remaining_seconds = self._sequence.current_phase()[1]
            self._is_running = False
            return True

    def skip(self) -> bool:
        """
        Skip to the next phase.
        Returns True if there are more phases, False if sequence restarted.
        """
        if self._sequence.advance():
            self._remaining_seconds = self._sequence.current_phase()[1]
            return True
        else:
            # Sequence complete, reset
            self._sequence.reset()
            self._remaining_seconds = self._sequence.current_phase()[1]
            self._is_running = False
            return False

    def restart(self) -> None:
        """Restart the timer from the beginning."""
        self._sequence.reset()
        self._remaining_seconds = self._sequence.current_phase()[1]
        self._is_running = False

    def get_completed_counts(self) -> tuple[int, int, int]:
        """Get counts of completed sessions, short breaks, and long breaks."""
        return self._sequence.get_completed_counts()


class TimerRepository:
    """Wraps database calls for timer CRUD operations."""

    def __init__(self):
        create_tables()

    def get_all(self) -> list[TimerConfig]:
        """Get all timer configurations."""
        timers = get_all_timers()
        return [TimerConfig.from_db_model(t) for t in timers]

    def get_by_id(self, timer_id: int) -> Optional[TimerConfig]:
        """Get a timer by ID."""
        timer = get_timer_by_id(timer_id)
        return TimerConfig.from_db_model(timer)

    def create(
        self,
        name: str,
        session_length: int,
        short_break: int,
        long_break: int,
        short_per_long: int,
        total_sessions: int,
    ) -> None:
        """Create a new timer configuration."""
        add_timer(name, session_length, short_break, long_break, short_per_long, total_sessions)

    def update(self, config: TimerConfig) -> None:
        """Update an existing timer configuration."""
        update_timer(
            config.id,
            config.name,
            config.session_length,
            config.short_break,
            config.long_break,
            config.short_per_long,
            config.total_sessions,
        )

    def delete(self, timer_id: int) -> None:
        """Delete a timer by ID."""
        delete_timer(timer_id)

    def ensure_default_exists(self) -> None:
        """Ensure at least one default timer exists."""
        if not get_all_timers():
            add_timer("Pomodoro", 25, 5, 10, 4, 8)


class SessionRepository:
    """Wraps database calls for session logging."""

    def create(self, timer_id: int) -> int:
        """Create a new session and return its ID."""
        return create_session(timer_id)

    def update(
        self,
        session_id: int,
        stop_timestamp: Optional[str],
        sessions_completed: int,
        short_breaks_completed: int,
        long_breaks_completed: int,
    ) -> None:
        """Update a session's stats."""
        update_session(
            session_id,
            stop_timestamp,
            sessions_completed,
            short_breaks_completed,
            long_breaks_completed,
        )

    def get_all(self) -> list[dict]:
        """Get all sessions as dictionaries."""
        sessions = get_all_sessions()
        return [
            {
                "id": s.id,
                "timer_id": s.timer_id,
                "start_timestamp": s.start_timestamp,
                "stop_timestamp": s.stop_timestamp,
                "sessions_completed": s.sessions_completed,
                "short_breaks_completed": s.short_breaks_completed,
                "long_breaks_completed": s.long_breaks_completed,
            }
            for s in sessions
        ]
