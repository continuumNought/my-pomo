"""Unit tests for the core Pomodoro timer logic."""

import pytest

from my_pomo.core import TimerConfig, PomodoroSequence, PomodoroTimer


@pytest.fixture
def default_config() -> TimerConfig:
    """Create a default timer configuration for testing."""
    return TimerConfig(
        id=1,
        name="Test Timer",
        session_length=25,
        short_break=5,
        long_break=15,
        short_per_long=3,
        total_sessions=4,
    )


@pytest.fixture
def short_config() -> TimerConfig:
    """Create a short timer configuration for faster testing."""
    return TimerConfig(
        id=2,
        name="Short Timer",
        session_length=1,
        short_break=1,
        long_break=2,
        short_per_long=1,
        total_sessions=2,
    )


class TestTimerConfig:
    """Tests for TimerConfig dataclass."""

    def test_create_config(self):
        """Test creating a timer configuration."""
        config = TimerConfig(
            id=1,
            name="Work",
            session_length=25,
            short_break=5,
            long_break=15,
            short_per_long=3,
            total_sessions=4,
        )
        assert config.name == "Work"
        assert config.session_length == 25
        assert config.short_break == 5
        assert config.long_break == 15
        assert config.short_per_long == 3
        assert config.total_sessions == 4

    def test_from_db_model_none(self):
        """Test from_db_model with None returns None."""
        assert TimerConfig.from_db_model(None) is None


class TestPomodoroSequence:
    """Tests for PomodoroSequence class."""

    def test_sequence_generation(self, default_config: TimerConfig):
        """Test that sequence is generated correctly."""
        seq = PomodoroSequence(default_config)
        # 4 sessions with breaks between them
        # Pattern: P, SB, P, SB, P, SB, P (last session has no break after)
        # With short_per_long=3, long break after every 4th session
        # So: P, SB, P, SB, P, SB, P, LB would be if we had more sessions
        # But with 4 sessions: P, SB, P, SB, P, SB, P (7 phases)
        phase_name, duration = seq.current_phase()
        assert phase_name == "Pomodoro"
        assert duration == 25 * 60

    def test_sequence_advance(self, default_config: TimerConfig):
        """Test advancing through the sequence."""
        seq = PomodoroSequence(default_config)

        # First phase is Pomodoro
        assert seq.current_phase()[0] == "Pomodoro"
        assert not seq.is_break()

        # Advance to first break
        assert seq.advance() is True
        assert "Break" in seq.current_phase()[0]
        assert seq.is_break()

        # Advance to second Pomodoro
        assert seq.advance() is True
        assert seq.current_phase()[0] == "Pomodoro"

    def test_sequence_retreat(self, default_config: TimerConfig):
        """Test retreating through the sequence."""
        seq = PomodoroSequence(default_config)

        # Can't retreat from first phase
        assert seq.retreat() is False
        assert seq.index == 0

        # Advance then retreat
        seq.advance()
        assert seq.index == 1
        assert seq.retreat() is True
        assert seq.index == 0

    def test_sequence_reset(self, default_config: TimerConfig):
        """Test resetting the sequence."""
        seq = PomodoroSequence(default_config)

        # Advance a few times
        seq.advance()
        seq.advance()
        assert seq.index == 2

        # Reset
        seq.reset()
        assert seq.index == 0
        assert seq.current_phase()[0] == "Pomodoro"

    def test_sequence_completion(self, short_config: TimerConfig):
        """Test that sequence completes correctly."""
        seq = PomodoroSequence(short_config)

        # Advance through all phases
        while seq.advance():
            pass

        assert seq.is_complete()

    def test_completed_counts(self, default_config: TimerConfig):
        """Test counting completed phases."""
        seq = PomodoroSequence(default_config)

        # Initially nothing completed
        sessions, short_breaks, long_breaks = seq.get_completed_counts()
        assert sessions == 0
        assert short_breaks == 0
        assert long_breaks == 0

        # Complete first pomodoro
        seq.advance()
        sessions, short_breaks, long_breaks = seq.get_completed_counts()
        assert sessions == 1
        assert short_breaks == 0

        # Complete first short break
        seq.advance()
        sessions, short_breaks, long_breaks = seq.get_completed_counts()
        assert sessions == 1
        assert short_breaks == 1

    def test_long_break_insertion(self):
        """Test that long breaks are inserted at correct intervals."""
        config = TimerConfig(
            id=1,
            name="Long Break Test",
            session_length=1,
            short_break=1,
            long_break=2,
            short_per_long=1,  # Long break after every 2 sessions
            total_sessions=4,
        )
        seq = PomodoroSequence(config)

        phases = []
        phases.append(seq.current_phase()[0])
        while seq.advance():
            phases.append(seq.current_phase()[0])

        # Should have: P, LB, P, LB, P, LB, P (or similar pattern)
        assert "Long Break" in phases


class TestPomodoroTimer:
    """Tests for PomodoroTimer class."""

    def test_initial_state(self, default_config: TimerConfig):
        """Test timer initial state."""
        timer = PomodoroTimer(default_config)

        assert timer.remaining_seconds == 25 * 60
        assert timer.is_running is False
        assert timer.current_phase_name == "Pomodoro"
        assert timer.is_break is False
        assert timer.is_complete is False
        assert timer.config == default_config

    def test_start_pause(self, default_config: TimerConfig):
        """Test starting and pausing the timer."""
        timer = PomodoroTimer(default_config)

        assert timer.is_running is False
        timer.start()
        assert timer.is_running is True
        timer.pause()
        assert timer.is_running is False

    def test_tick_decrements(self, default_config: TimerConfig):
        """Test that tick decrements remaining time."""
        timer = PomodoroTimer(default_config)
        timer.start()

        initial = timer.remaining_seconds
        phase_changed = timer.tick()

        assert timer.remaining_seconds == initial - 1
        assert phase_changed is False

    def test_tick_when_paused(self, default_config: TimerConfig):
        """Test that tick does nothing when paused."""
        timer = PomodoroTimer(default_config)

        initial = timer.remaining_seconds
        phase_changed = timer.tick()

        assert timer.remaining_seconds == initial
        assert phase_changed is False

    def test_tick_phase_change(self):
        """Test that tick triggers phase change when time runs out."""
        config = TimerConfig(
            id=1,
            name="Quick",
            session_length=1,
            short_break=1,
            long_break=1,
            short_per_long=1,
            total_sessions=2,
        )
        timer = PomodoroTimer(config)
        timer.start()

        # Tick down to 0
        for _ in range(60):
            timer.tick()

        # One more tick should trigger phase change
        phase_changed = timer.tick()
        assert phase_changed is True
        assert timer.is_break is True

    def test_skip(self, default_config: TimerConfig):
        """Test skipping to next phase."""
        timer = PomodoroTimer(default_config)

        assert timer.current_phase_name == "Pomodoro"
        has_more = timer.skip()

        assert has_more is True
        assert timer.is_break is True

    def test_skip_to_completion(self):
        """Test skipping through entire sequence."""
        config = TimerConfig(
            id=1,
            name="Short",
            session_length=1,
            short_break=1,
            long_break=1,
            short_per_long=1,
            total_sessions=1,
        )
        timer = PomodoroTimer(config)

        # Only one session, no break after
        has_more = timer.skip()
        assert has_more is False
        assert timer.is_running is False

    def test_restart(self, default_config: TimerConfig):
        """Test restarting the timer."""
        timer = PomodoroTimer(default_config)
        timer.start()

        # Advance a bit
        for _ in range(10):
            timer.tick()
        timer.skip()

        # Restart
        timer.restart()

        assert timer.remaining_seconds == 25 * 60
        assert timer.is_running is False
        assert timer.current_phase_name == "Pomodoro"

    def test_rewind_resets_clock(self, default_config: TimerConfig):
        """Test rewind resets clock when running or partially elapsed."""
        timer = PomodoroTimer(default_config)
        timer.start()

        # Tick a few times
        for _ in range(10):
            timer.tick()

        assert timer.remaining_seconds < 25 * 60
        changed = timer.rewind()

        assert changed is True
        assert timer.remaining_seconds == 25 * 60
        assert timer.is_running is False

    def test_rewind_goes_back_phase(self, default_config: TimerConfig):
        """Test rewind goes to previous phase when at initial state."""
        timer = PomodoroTimer(default_config)

        # Skip to next phase
        timer.skip()
        assert timer.is_break is True

        # Rewind should go back to previous phase
        changed = timer.rewind()
        assert changed is True
        assert timer.is_break is False
        assert timer.current_phase_name == "Pomodoro"

    def test_rewind_at_start(self, default_config: TimerConfig):
        """Test rewind does nothing at start of first phase."""
        timer = PomodoroTimer(default_config)

        changed = timer.rewind()
        assert changed is False

    def test_get_completed_counts(self, default_config: TimerConfig):
        """Test getting completed phase counts."""
        timer = PomodoroTimer(default_config)

        sessions, short_breaks, long_breaks = timer.get_completed_counts()
        assert sessions == 0
        assert short_breaks == 0
        assert long_breaks == 0

        # Skip first pomodoro
        timer.skip()
        sessions, short_breaks, long_breaks = timer.get_completed_counts()
        assert sessions == 1


class TestBoundaryConditions:
    """Boundary condition tests for edge cases."""

    def test_single_session_no_breaks(self):
        """Test timer with only one session (no breaks needed)."""
        config = TimerConfig(
            id=1,
            name="Single",
            session_length=1,
            short_break=5,
            long_break=15,
            short_per_long=3,
            total_sessions=1,
        )
        seq = PomodoroSequence(config)

        # Should only have one phase
        assert seq.current_phase()[0] == "Pomodoro"
        assert seq.advance() is False
        assert seq.is_complete()

    def test_minimum_session_length(self):
        """Test timer with minimum 1-minute session length."""
        config = TimerConfig(
            id=1,
            name="Minimum",
            session_length=1,
            short_break=1,
            long_break=1,
            short_per_long=1,
            total_sessions=1,
        )
        timer = PomodoroTimer(config)

        assert timer.remaining_seconds == 60

    def test_zero_short_per_long(self):
        """Test timer with zero short breaks per long break (always long breaks)."""
        config = TimerConfig(
            id=1,
            name="Always Long",
            session_length=1,
            short_break=1,
            long_break=2,
            short_per_long=0,
            total_sessions=3,
        )
        seq = PomodoroSequence(config)

        phases = []
        phases.append(seq.current_phase()[0])
        while seq.advance():
            phases.append(seq.current_phase()[0])

        # With short_per_long=0, long break after every session
        long_break_count = sum(1 for p in phases if p == "Long Break")
        assert long_break_count >= 1

    def test_large_session_count(self):
        """Test timer with many sessions."""
        config = TimerConfig(
            id=1,
            name="Marathon",
            session_length=1,
            short_break=1,
            long_break=2,
            short_per_long=3,
            total_sessions=100,
        )
        seq = PomodoroSequence(config)

        # Count all phases
        phase_count = 1
        while seq.advance():
            phase_count += 1

        # Should have 100 pomodoros + breaks between them
        assert phase_count > 100
        assert seq.is_complete()

    def test_timer_at_exactly_zero(self):
        """Test timer behavior when remaining_seconds hits exactly zero."""
        config = TimerConfig(
            id=1,
            name="Zero Test",
            session_length=1,
            short_break=1,
            long_break=1,
            short_per_long=1,
            total_sessions=2,
        )
        timer = PomodoroTimer(config)
        timer.start()

        # Tick exactly 60 times to reach 0
        for _ in range(60):
            timer.tick()

        assert timer.remaining_seconds == 0

        # Next tick triggers phase change
        phase_changed = timer.tick()
        assert phase_changed is True

    def test_sequence_index_at_boundary(self):
        """Test sequence index behavior at start and end."""
        config = TimerConfig(
            id=1,
            name="Index Test",
            session_length=1,
            short_break=1,
            long_break=1,
            short_per_long=1,
            total_sessions=2,
        )
        seq = PomodoroSequence(config)

        # At start
        assert seq.index == 0

        # Advance to end
        while seq.advance():
            pass

        # Should be at the end index
        assert seq.is_complete()

        # Further advances should still return False
        assert seq.advance() is False

    def test_empty_phase_name_after_completion(self):
        """Test current_phase returns empty after sequence completes."""
        config = TimerConfig(
            id=1,
            name="Completion Test",
            session_length=1,
            short_break=1,
            long_break=1,
            short_per_long=1,
            total_sessions=1,
        )
        seq = PomodoroSequence(config)

        # Advance past the only session
        seq.advance()

        phase_name, duration = seq.current_phase()
        assert phase_name == ""
        assert duration == 0

    def test_very_long_durations(self):
        """Test timer with very long session durations."""
        config = TimerConfig(
            id=1,
            name="Long Duration",
            session_length=999,
            short_break=999,
            long_break=999,
            short_per_long=1,
            total_sessions=1,
        )
        timer = PomodoroTimer(config)

        assert timer.remaining_seconds == 999 * 60

    def test_retreat_multiple_times(self):
        """Test retreating multiple times through sequence."""
        config = TimerConfig(
            id=1,
            name="Retreat Test",
            session_length=1,
            short_break=1,
            long_break=1,
            short_per_long=1,
            total_sessions=5,
        )
        seq = PomodoroSequence(config)

        # Advance 4 times
        for _ in range(4):
            seq.advance()
        assert seq.index == 4

        # Retreat 4 times
        for i in range(4):
            assert seq.retreat() is True
        assert seq.index == 0

        # Can't retreat further
        assert seq.retreat() is False


class TestNegativeCases:
    """Negative tests for error conditions and invalid operations."""

    def test_multiple_starts(self):
        """Test calling start multiple times."""
        config = TimerConfig(
            id=1,
            name="Multi Start",
            session_length=25,
            short_break=5,
            long_break=15,
            short_per_long=3,
            total_sessions=4,
        )
        timer = PomodoroTimer(config)

        timer.start()
        assert timer.is_running is True

        # Starting again should still be running (idempotent)
        timer.start()
        assert timer.is_running is True

    def test_multiple_pauses(self):
        """Test calling pause multiple times."""
        config = TimerConfig(
            id=1,
            name="Multi Pause",
            session_length=25,
            short_break=5,
            long_break=15,
            short_per_long=3,
            total_sessions=4,
        )
        timer = PomodoroTimer(config)

        # Pause when not running
        timer.pause()
        assert timer.is_running is False

        timer.start()
        timer.pause()
        assert timer.is_running is False

        # Pause again
        timer.pause()
        assert timer.is_running is False

    def test_tick_after_sequence_complete(self):
        """Test ticking after sequence is complete."""
        config = TimerConfig(
            id=1,
            name="Complete Tick",
            session_length=1,
            short_break=1,
            long_break=1,
            short_per_long=1,
            total_sessions=1,
        )
        timer = PomodoroTimer(config)
        timer.start()

        # Complete the sequence
        for _ in range(61):
            timer.tick()

        # Timer should have stopped
        assert timer.is_running is False

        # Additional ticks should do nothing
        remaining_before = timer.remaining_seconds
        timer.tick()
        assert timer.remaining_seconds == remaining_before

    def test_skip_after_completion_resets(self):
        """Test skip after sequence completes resets the timer."""
        config = TimerConfig(
            id=1,
            name="Skip After Complete",
            session_length=1,
            short_break=1,
            long_break=1,
            short_per_long=1,
            total_sessions=1,
        )
        timer = PomodoroTimer(config)

        # Skip the only session
        has_more = timer.skip()
        assert has_more is False

        # Skip again should still return False (already reset)
        has_more = timer.skip()
        # After reset, skipping advances but sequence is short
        assert timer.current_phase_name == "Pomodoro"

    def test_rewind_while_running(self):
        """Test rewind while timer is running stops the timer."""
        config = TimerConfig(
            id=1,
            name="Rewind Running",
            session_length=25,
            short_break=5,
            long_break=15,
            short_per_long=3,
            total_sessions=4,
        )
        timer = PomodoroTimer(config)
        timer.start()

        assert timer.is_running is True
        timer.rewind()
        assert timer.is_running is False

    def test_restart_while_running(self):
        """Test restart while timer is running."""
        config = TimerConfig(
            id=1,
            name="Restart Running",
            session_length=25,
            short_break=5,
            long_break=15,
            short_per_long=3,
            total_sessions=4,
        )
        timer = PomodoroTimer(config)
        timer.start()

        for _ in range(100):
            timer.tick()

        timer.restart()
        assert timer.is_running is False
        assert timer.remaining_seconds == 25 * 60
        assert timer.current_phase_name == "Pomodoro"

    def test_advance_on_completed_sequence(self):
        """Test advancing an already completed sequence."""
        config = TimerConfig(
            id=1,
            name="Advance Complete",
            session_length=1,
            short_break=1,
            long_break=1,
            short_per_long=1,
            total_sessions=1,
        )
        seq = PomodoroSequence(config)

        # Complete the sequence
        seq.advance()
        assert seq.is_complete()

        # Further advances should return False
        assert seq.advance() is False
        assert seq.advance() is False

    def test_counts_stable_at_completion(self):
        """Test that completed counts are correct when sequence ends."""
        config = TimerConfig(
            id=1,
            name="Stable Counts",
            session_length=1,
            short_break=1,
            long_break=1,
            short_per_long=1,
            total_sessions=2,
        )
        seq = PomodoroSequence(config)

        # Complete entire sequence
        while seq.advance():
            pass

        sessions, short_breaks, long_breaks = seq.get_completed_counts()

        # Should have completed 2 sessions and 1 long break between them
        assert sessions == 2
        assert seq.is_complete()

    def test_advance_past_end_causes_index_error(self):
        """Test that advancing past end and calling get_completed_counts raises IndexError."""
        config = TimerConfig(
            id=1,
            name="Index Error Test",
            session_length=1,
            short_break=1,
            long_break=1,
            short_per_long=1,
            total_sessions=1,
        )
        seq = PomodoroSequence(config)

        # Complete the sequence
        seq.advance()
        assert seq.is_complete()

        # Advance past the end (returns False but still increments index)
        seq.advance()

        # get_completed_counts will raise IndexError due to index out of bounds
        with pytest.raises(IndexError):
            seq.get_completed_counts()

    def test_zero_remaining_stays_zero_when_paused(self):
        """Test that timer at zero doesn't go negative when paused."""
        config = TimerConfig(
            id=1,
            name="Zero Paused",
            session_length=1,
            short_break=1,
            long_break=1,
            short_per_long=1,
            total_sessions=2,
        )
        timer = PomodoroTimer(config)
        timer.start()

        # Tick to zero
        for _ in range(60):
            timer.tick()

        timer.pause()
        assert timer.remaining_seconds == 0

        # Tick while paused
        timer.tick()
        assert timer.remaining_seconds == 0

    def test_rapid_start_pause_cycles(self):
        """Test rapid start/pause cycles don't corrupt state."""
        config = TimerConfig(
            id=1,
            name="Rapid Cycles",
            session_length=25,
            short_break=5,
            long_break=15,
            short_per_long=3,
            total_sessions=4,
        )
        timer = PomodoroTimer(config)

        initial_seconds = timer.remaining_seconds

        for _ in range(100):
            timer.start()
            timer.pause()

        # State should be consistent
        assert timer.remaining_seconds == initial_seconds
        assert timer.is_running is False

    def test_rewind_skip_rewind_sequence(self):
        """Test complex rewind/skip/rewind sequences."""
        config = TimerConfig(
            id=1,
            name="Complex Nav",
            session_length=1,
            short_break=1,
            long_break=1,
            short_per_long=1,
            total_sessions=4,
        )
        timer = PomodoroTimer(config)

        # Skip forward twice
        timer.skip()
        timer.skip()
        phase_after_skips = timer.current_phase_name

        # Rewind once
        timer.rewind()

        # Skip again
        timer.skip()

        # Should be back to same phase
        assert timer.current_phase_name == phase_after_skips
