"""SQLAlchemy database layer for the Pomodoro timer."""

import datetime
from pathlib import Path
from typing import Optional

from sqlalchemy import create_engine, String, Integer, ForeignKey
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker, Session


# Store database in user's data directory
DB_PATH = Path.home() / ".my_pomo" / "timers.db"


class Base(DeclarativeBase):
    pass


class Timer(Base):
    """SQLAlchemy model for timer configurations."""

    __tablename__ = "timers"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    session_length: Mapped[int] = mapped_column(Integer, nullable=False)
    short_break: Mapped[int] = mapped_column(Integer, nullable=False)
    long_break: Mapped[int] = mapped_column(Integer, nullable=False)
    short_per_long: Mapped[int] = mapped_column(Integer, nullable=False)
    total_sessions: Mapped[int] = mapped_column(Integer, nullable=False)


class PomodoroSession(Base):
    """SQLAlchemy model for completed pomodoro sessions."""

    __tablename__ = "sessions"

    id: Mapped[int] = mapped_column(primary_key=True)
    timer_id: Mapped[int] = mapped_column(ForeignKey("timers.id"), nullable=False)
    start_timestamp: Mapped[str] = mapped_column(String, nullable=False)
    stop_timestamp: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    sessions_completed: Mapped[int] = mapped_column(Integer, default=0)
    short_breaks_completed: Mapped[int] = mapped_column(Integer, default=0)
    long_breaks_completed: Mapped[int] = mapped_column(Integer, default=0)


def _ensure_db_dir() -> None:
    """Ensure the database directory exists."""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)


def get_engine():
    """Get the SQLAlchemy engine."""
    _ensure_db_dir()
    return create_engine(f"sqlite:///{DB_PATH}")


def get_session_factory() -> sessionmaker[Session]:
    """Get a session factory for creating database sessions."""
    engine = get_engine()
    return sessionmaker(bind=engine)


def create_tables() -> None:
    """Create all database tables."""
    engine = get_engine()
    Base.metadata.create_all(engine)


def add_timer(
    name: str,
    session_length: int,
    short_break: int,
    long_break: int,
    short_per_long: int,
    total_sessions: int,
) -> None:
    """Add a new timer configuration."""
    SessionFactory = get_session_factory()
    with SessionFactory() as session:
        # Check if timer with this name already exists
        existing = session.query(Timer).filter_by(name=name).first()
        if existing:
            return
        timer = Timer(
            name=name,
            session_length=session_length,
            short_break=short_break,
            long_break=long_break,
            short_per_long=short_per_long,
            total_sessions=total_sessions,
        )
        session.add(timer)
        session.commit()


def get_all_timers() -> list[Timer]:
    """Get all timer configurations."""
    SessionFactory = get_session_factory()
    with SessionFactory() as session:
        timers = session.query(Timer).all()
        # Detach from session so they can be used outside
        session.expunge_all()
        return timers


def get_timer_by_id(timer_id: int) -> Optional[Timer]:
    """Get a timer by ID."""
    SessionFactory = get_session_factory()
    with SessionFactory() as session:
        timer = session.query(Timer).filter_by(id=timer_id).first()
        if timer:
            session.expunge(timer)
        return timer


def update_timer(
    timer_id: int,
    name: str,
    session_length: int,
    short_break: int,
    long_break: int,
    short_per_long: int,
    total_sessions: int,
) -> None:
    """Update an existing timer configuration."""
    SessionFactory = get_session_factory()
    with SessionFactory() as session:
        timer = session.query(Timer).filter_by(id=timer_id).first()
        if timer:
            timer.name = name
            timer.session_length = session_length
            timer.short_break = short_break
            timer.long_break = long_break
            timer.short_per_long = short_per_long
            timer.total_sessions = total_sessions
            session.commit()


def delete_timer(timer_id: int) -> None:
    """Delete a timer and its associated sessions."""
    SessionFactory = get_session_factory()
    with SessionFactory() as session:
        session.query(PomodoroSession).filter_by(timer_id=timer_id).delete()
        session.query(Timer).filter_by(id=timer_id).delete()
        session.commit()


def create_session(timer_id: int) -> int:
    """Create a new pomodoro session and return its ID."""
    SessionFactory = get_session_factory()
    with SessionFactory() as session:
        start_time = datetime.datetime.now().isoformat()
        pomo_session = PomodoroSession(
            timer_id=timer_id,
            start_timestamp=start_time,
        )
        session.add(pomo_session)
        session.commit()
        return pomo_session.id


def update_session(
    session_id: int,
    stop_timestamp: Optional[str],
    sessions_completed: int,
    short_breaks_completed: int,
    long_breaks_completed: int,
) -> None:
    """Update a pomodoro session's stats."""
    SessionFactory = get_session_factory()
    with SessionFactory() as session:
        pomo_session = session.query(PomodoroSession).filter_by(id=session_id).first()
        if pomo_session:
            pomo_session.stop_timestamp = stop_timestamp
            pomo_session.sessions_completed = sessions_completed
            pomo_session.short_breaks_completed = short_breaks_completed
            pomo_session.long_breaks_completed = long_breaks_completed
            session.commit()


def get_all_sessions() -> list[PomodoroSession]:
    """Get all pomodoro sessions."""
    SessionFactory = get_session_factory()
    with SessionFactory() as session:
        sessions = session.query(PomodoroSession).all()
        session.expunge_all()
        return sessions
