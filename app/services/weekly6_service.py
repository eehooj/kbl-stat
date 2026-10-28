from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Weekly6Round


def get_round(session: Session, week_label: str | None) -> Weekly6Round | None:
    statement = select(Weekly6Round).order_by(Weekly6Round.closes_at.desc())
    if week_label:
        statement = statement.where(Weekly6Round.week_label == week_label)
    return session.scalars(statement).first()


def render_weekly6(round_: Weekly6Round | None) -> str:
    if round_ is None:
        return "KBL WEEKLY 6 PREDICTION\n\n확인된 Weekly 6 문제 데이터가 없습니다. 가상 예측을 만들지 않습니다."
    fixtures = sorted(round_.fixtures, key=lambda item: item.ordinal)
    lines = ["KBL WEEKLY 6 PREDICTION", "", f"주차: {round_.week_label}"]
    lines.append(f"공식 선택 수: {round_.selection_count if round_.selection_count is not None else '미확인'}")
    lines.append("")
    for fixture in fixtures:
        when = fixture.starts_at.isoformat() if fixture.starts_at else "일시 미확인"
        lines.extend([f"경기 {fixture.ordinal}: {fixture.home_team_name} vs {fixture.away_team_name}", f"일시: {when}", "추천: 데이터 수집 및 확률 보정 전", ""])
    lines.append("전체 적중 확률: 확률 보정과 공식 채점 규칙 검증 전에는 표시하지 않습니다.")
    return "\n".join(lines)
