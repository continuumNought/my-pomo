"""End-to-end tests for the Pomodoro timer TUI application."""

from unittest.mock import patch

import pytest

from my_pomo.app import PomoApp, TimerFormScreen, EditTimerScreen, SessionLogScreen
import my_pomo.database


@pytest.fixture
def temp_db(tmp_path, monkeypatch):
    """Use a temporary database for testing."""
    test_db = tmp_path / "test_timers.db"
    monkeypatch.setattr(my_pomo.database, "DB_PATH", test_db)
    return test_db


@pytest.fixture
def mock_playsound():
    """Mock playsound to avoid audio during tests."""
    with patch("my_pomo.app.playsound") as mock:
        yield mock


class TestAppStartup:
    """Tests for app initialization and startup."""

    async def test_app_mounts_successfully(self, temp_db, mock_playsound):
        """Test that the app mounts without errors."""
        app = PomoApp()
        async with app.run_test() as pilot:
            # App should have mounted
            assert app.is_running is False or app._pomo_timer is not None

    async def test_default_timer_created(self, temp_db, mock_playsound):
        """Test that a default timer is created on first run."""
        app = PomoApp()
        async with app.run_test() as pilot:
            # Should have at least one timer
            assert len(app._timer_configs) >= 1
            assert app._timer_configs[0].name == "Pomodoro"

    async def test_timer_display_shows_initial_time(self, temp_db, mock_playsound):
        """Test that the timer display shows the initial time."""
        app = PomoApp()
        async with app.run_test() as pilot:
            # Default timer is 25 minutes
            assert app.remaining_seconds == 25 * 60

    async def test_header_and_footer_present(self, temp_db, mock_playsound):
        """Test that header and footer widgets are present."""
        app = PomoApp()
        async with app.run_test() as pilot:
            from textual.widgets import Header, Footer
            header = app.query_one(Header)
            footer = app.query_one(Footer)
            assert header is not None
            assert footer is not None


class TestTimerControls:
    """Tests for timer play/pause/skip/rewind/restart controls."""

    async def test_play_starts_timer(self, temp_db, mock_playsound):
        """Test that pressing 'p' starts the timer."""
        app = PomoApp()
        async with app.run_test() as pilot:
            assert app._pomo_timer.is_running is False
            await pilot.press("p")
            assert app._pomo_timer.is_running is True

    async def test_pause_stops_timer(self, temp_db, mock_playsound):
        """Test that pressing 'p' again pauses the timer."""
        app = PomoApp()
        async with app.run_test() as pilot:
            await pilot.press("p")  # Start
            assert app._pomo_timer.is_running is True
            await pilot.press("p")  # Pause
            assert app._pomo_timer.is_running is False

    async def test_skip_advances_phase(self, temp_db, mock_playsound):
        """Test that pressing 's' skips to the next phase."""
        app = PomoApp()
        async with app.run_test() as pilot:
            initial_phase = app._pomo_timer.current_phase_name
            assert initial_phase == "Pomodoro"

            await pilot.press("s")

            # Should now be on a break
            assert app._pomo_timer.is_break is True

    async def test_rewind_resets_current_phase(self, temp_db, mock_playsound):
        """Test that pressing 'w' rewinds the timer."""
        app = PomoApp()
        async with app.run_test() as pilot:
            # Start and let it tick
            await pilot.press("p")
            await pilot.pause()  # Let the app process

            # Rewind
            await pilot.press("w")

            # Timer should be paused and reset
            assert app._pomo_timer.is_running is False
            assert app.remaining_seconds == 25 * 60

    async def test_restart_resets_sequence(self, temp_db, mock_playsound):
        """Test that pressing 'r' restarts the entire sequence."""
        app = PomoApp()
        async with app.run_test() as pilot:
            # Skip to break
            await pilot.press("s")
            assert app._pomo_timer.is_break is True

            # Restart
            await pilot.press("r")

            # Should be back at the beginning
            assert app._pomo_timer.current_phase_name == "Pomodoro"
            assert app.remaining_seconds == 25 * 60

    async def test_multiple_skips(self, temp_db, mock_playsound):
        """Test multiple skip operations."""
        app = PomoApp()
        async with app.run_test() as pilot:
            # Skip through several phases
            await pilot.press("s")  # Pomodoro -> Short Break
            assert app._pomo_timer.is_break is True

            await pilot.press("s")  # Short Break -> Pomodoro
            assert app._pomo_timer.is_break is False

            await pilot.press("s")  # Pomodoro -> Short Break
            assert app._pomo_timer.is_break is True


class TestScreenNavigation:
    """Tests for navigating between screens."""

    async def test_new_timer_screen_opens(self, temp_db, mock_playsound):
        """Test that pressing 'n' opens the new timer screen."""
        app = PomoApp()
        async with app.run_test() as pilot:
            await pilot.press("n")
            await pilot.pause()

            # Should be on TimerFormScreen
            assert isinstance(app.screen, TimerFormScreen)

    async def test_edit_timer_screen_opens(self, temp_db, mock_playsound):
        """Test that pressing 'e' opens the edit timer screen."""
        app = PomoApp()
        async with app.run_test() as pilot:
            await pilot.press("e")
            await pilot.pause()

            # Should be on EditTimerScreen
            assert isinstance(app.screen, EditTimerScreen)

    async def test_session_log_screen_opens(self, temp_db, mock_playsound):
        """Test that pressing 'l' opens the session log screen."""
        app = PomoApp()
        async with app.run_test() as pilot:
            await pilot.press("l")
            await pilot.pause()

            # Should be on SessionLogScreen
            assert isinstance(app.screen, SessionLogScreen)

    async def test_back_from_session_log(self, temp_db, mock_playsound):
        """Test navigating back from session log screen."""
        app = PomoApp()
        async with app.run_test() as pilot:
            await pilot.press("l")
            await pilot.pause()
            assert isinstance(app.screen, SessionLogScreen)

            # Click back button
            await pilot.click("#back")
            await pilot.pause()

            # Should be back on main screen
            assert not isinstance(app.screen, SessionLogScreen)

    async def test_back_from_edit_screen(self, temp_db, mock_playsound):
        """Test navigating back from edit timer screen."""
        app = PomoApp()
        async with app.run_test() as pilot:
            await pilot.press("e")
            await pilot.pause()
            assert isinstance(app.screen, EditTimerScreen)

            # Click back button
            await pilot.click("#back")
            await pilot.pause()

            # Should be back on main screen
            assert not isinstance(app.screen, EditTimerScreen)


class TestTimerFormScreen:
    """Tests for the new timer form screen."""

    async def test_form_has_all_fields(self, temp_db, mock_playsound):
        """Test that the form has all required input fields."""
        app = PomoApp()
        async with app.run_test() as pilot:
            await pilot.press("n")
            await pilot.pause()

            from textual.widgets import Input
            inputs = app.screen.query(Input)

            # Should have 6 input fields
            input_ids = [inp.id for inp in inputs]
            assert "name" in input_ids
            assert "session_length" in input_ids
            assert "short_break" in input_ids
            assert "long_break" in input_ids
            assert "short_per_long" in input_ids
            assert "total_sessions" in input_ids

    async def test_create_new_timer(self, temp_db, mock_playsound):
        """Test creating a new timer through the form."""
        app = PomoApp()
        async with app.run_test() as pilot:
            initial_count = len(app._timer_configs)

            await pilot.press("n")
            await pilot.pause()

            # Fill in the form
            from textual.widgets import Input

            name_input = app.screen.query_one("#name", Input)
            name_input.value = "Test Timer"

            app.screen.query_one("#session_length", Input).value = "30"
            app.screen.query_one("#short_break", Input).value = "5"
            app.screen.query_one("#long_break", Input).value = "15"
            app.screen.query_one("#short_per_long", Input).value = "3"
            app.screen.query_one("#total_sessions", Input).value = "4"

            # Click save
            await pilot.click("#save_timer")
            await pilot.pause()

            # Should be back on main screen with new timer
            assert not isinstance(app.screen, TimerFormScreen)
            assert len(app._timer_configs) == initial_count + 1

    async def test_form_validation_empty_name(self, temp_db, mock_playsound):
        """Test that form validates empty timer name."""
        app = PomoApp()
        async with app.run_test() as pilot:
            await pilot.press("n")
            await pilot.pause()

            # Try to save with empty name
            await pilot.click("#save_timer")
            await pilot.pause()

            # Should still be on form screen (validation failed)
            assert isinstance(app.screen, TimerFormScreen)


class TestEditTimerScreen:
    """Tests for the edit timer screen."""

    async def test_form_populated_with_current_values(self, temp_db, mock_playsound):
        """Test that edit form is populated with current timer values."""
        app = PomoApp()
        async with app.run_test() as pilot:
            await pilot.press("e")
            await pilot.pause()

            from textual.widgets import Input

            # Default timer values should be populated
            name_input = app.screen.query_one("#name", Input)
            assert name_input.value == "Pomodoro"

            session_input = app.screen.query_one("#session_length", Input)
            assert session_input.value == "25"

    async def test_update_timer(self, temp_db, mock_playsound):
        """Test updating a timer through the edit form."""
        app = PomoApp()
        async with app.run_test() as pilot:
            await pilot.press("e")
            await pilot.pause()

            from textual.widgets import Input

            # Change the session length
            session_input = app.screen.query_one("#session_length", Input)
            session_input.value = "50"

            await pilot.click("#save_timer")
            await pilot.pause()

            # Timer should be updated
            assert not isinstance(app.screen, EditTimerScreen)
            # The remaining seconds should reflect new duration
            assert app.remaining_seconds == 50 * 60

    async def test_delete_timer(self, temp_db, mock_playsound):
        """Test deleting a timer."""
        app = PomoApp()
        async with app.run_test() as pilot:
            # First create a second timer so we can delete one
            await pilot.press("n")
            await pilot.pause()

            from textual.widgets import Input
            app.screen.query_one("#name", Input).value = "To Delete"
            app.screen.query_one("#session_length", Input).value = "10"
            app.screen.query_one("#short_break", Input).value = "5"
            app.screen.query_one("#long_break", Input).value = "15"
            app.screen.query_one("#short_per_long", Input).value = "3"
            app.screen.query_one("#total_sessions", Input).value = "4"

            await pilot.click("#save_timer")
            await pilot.pause()

            count_before = len(app._timer_configs)

            # Now edit and delete
            await pilot.press("e")
            await pilot.pause()

            await pilot.click("#delete_timer")
            await pilot.pause()

            # Timer count should decrease
            assert len(app._timer_configs) == count_before - 1


class TestSessionLog:
    """Tests for the session log screen."""

    async def test_session_log_has_table(self, temp_db, mock_playsound):
        """Test that session log screen has a data table."""
        app = PomoApp()
        async with app.run_test() as pilot:
            await pilot.press("l")
            await pilot.pause()

            from textual.widgets import DataTable
            table = app.screen.query_one(DataTable)
            assert table is not None

    async def test_session_log_columns(self, temp_db, mock_playsound):
        """Test that session log table has correct columns."""
        app = PomoApp()
        async with app.run_test() as pilot:
            await pilot.press("l")
            await pilot.pause()

            from textual.widgets import DataTable
            table = app.screen.query_one(DataTable)

            column_labels = [col.label.plain for col in table.columns.values()]
            assert "ID" in column_labels
            assert "Timer ID" in column_labels
            assert "Start" in column_labels
            assert "Stop" in column_labels
            assert "Sessions" in column_labels

    async def test_session_created_on_play(self, temp_db, mock_playsound):
        """Test that a session is created when timer is started."""
        app = PomoApp()
        async with app.run_test() as pilot:
            # Start timer to create a session
            await pilot.press("p")
            await pilot.pause()

            assert app._current_session_id is not None

            # Stop timer
            await pilot.press("p")
            await pilot.pause()

            # Check session log
            await pilot.press("l")
            await pilot.pause()

            from textual.widgets import DataTable
            table = app.screen.query_one(DataTable)

            # Should have at least one row
            assert table.row_count >= 1


class TestTimerSelection:
    """Tests for timer selection dropdown."""

    async def test_timer_selector_present(self, temp_db, mock_playsound):
        """Test that timer selector is present."""
        app = PomoApp()
        async with app.run_test() as pilot:
            from textual.widgets import Select
            select = app.query_one("#timer-selector", Select)
            assert select is not None

    async def test_timer_selector_has_default(self, temp_db, mock_playsound):
        """Test that timer selector has default timer selected."""
        app = PomoApp()
        async with app.run_test() as pilot:
            from textual.widgets import Select
            select = app.query_one("#timer-selector", Select)

            # Should have a value selected
            assert select.value is not None


class TestQuitBehavior:
    """Tests for app quit behavior."""

    async def test_quit_action(self, temp_db, mock_playsound):
        """Test that pressing 'q' quits the app."""
        app = PomoApp()
        async with app.run_test() as pilot:
            # Press quit - the test will end when app exits
            await pilot.press("q")
            # If we get here without error, quit worked
