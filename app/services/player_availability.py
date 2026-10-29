"""Persist only date-specific player availability facts supplied with a source note."""
from datetime import UTC, date, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import PlayerAvailability


def record_unavailable_player(
    session: Session, *, player_name: str, team_name: str | None, availability_date: date, source_note: str,
) -> None:
    if not player_name.strip() or not source_note.strip():
        raise ValueError("선수 이름과 확인 근거를 입력해야 합니다")
    record = session.scalar(select(PlayerAvailability).where(
        PlayerAvailability.player_name == player_name,
        PlayerAvailability.team_name == team_name,
        PlayerAvailability.availability_date == availability_date,
    ))
    fields = {"status": "out", "source_note": source_note, "verified_at": datetime.now(UTC)}
    if record is None:
        session.add(PlayerAvailability(
            player_name=player_name, team_name=team_name, availability_date=availability_date, **fields,
        ))
    else:
        for name, value in fields.items():
            setattr(record, name, value)
    session.commit()
