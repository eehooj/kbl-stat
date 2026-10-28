import typer
from sqlalchemy import create_engine, select

from app.collectors.official_pages import KBLApiClient, KBLOfficialPageClient
from app.config import get_settings
from app.database import Base, make_session_factory
from app.models import CollectionLog, RawSourceDocument, Weekly6Round
from app.services.game_collection import collect_completed_game_stats, collect_schedule
from app.services.weekly6_service import get_round, render_weekly6

app = typer.Typer(no_args_is_help=True)


def _session():
    return make_session_factory()()


@app.command("init-db")
def init_db() -> None:
    engine = create_engine(get_settings().database_url)
    Base.metadata.create_all(engine)
    typer.echo("데이터베이스 스키마를 생성했습니다. 운영 환경에서는 Alembic migration을 사용하세요.")


@app.command("collect-weekly6")
def collect_weekly6() -> None:
    """Fetch and preserve the official page. Extraction is enabled only after schema verification."""
    page = KBLOfficialPageClient().fetch_challenge("weekly6")
    with _session() as session:
        session.add(CollectionLog(source_url=page.url, status="fetched_unparsed", fetched_at=page.fetched_at,
                                  response_sha256=page.content_hash,
                                  detail="Official Weekly 6 HTML retained for parser verification; no unverified fields extracted."))
        existing = session.scalar(select(RawSourceDocument).where(RawSourceDocument.content_hash == page.content_hash))
        if existing is None:
            session.add(RawSourceDocument(source_url=page.url, fetched_at=page.fetched_at,
                                          content_hash=page.content_hash, body=page.body))
        session.commit()
    typer.echo(f"공식 Weekly 6 페이지를 확인했습니다: {page.url}\n추출 규칙 미검증 상태이므로 문제 데이터를 임의 저장하지 않았습니다.")


@app.command("collect-games")
def collect_games(
    from_date: str = typer.Option(..., "--from-date", help="시작일 YYYYMMDD"),
    to_date: str = typer.Option(..., "--to-date", help="종료일 YYYYMMDD"),
) -> None:
    """명시된 날짜 범위의 공식 경기 일정을 수집·갱신한다."""
    with _session() as session:
        count = collect_schedule(session, KBLApiClient(), from_date, to_date)
    typer.echo(f"공식 경기 일정 {count}건을 수집·갱신했습니다.")


@app.command("collect-stats")
def collect_stats(limit: int | None = typer.Option(None, "--limit", min=1, help="수집할 종료 경기 수 상한")) -> None:
    """수집된 종료 경기의 공식 팀·선수 기록을 수집·갱신한다."""
    with _session() as session:
        count = collect_completed_game_stats(session, KBLApiClient(), limit)
    typer.echo(f"종료 경기 {count}건의 팀·선수 기록을 수집·갱신했습니다.")


@app.command("predict-weekly6")
def predict_weekly6(week: str | None = typer.Option(None, "--week")) -> None:
    with _session() as session:
        typer.echo(render_weekly6(get_round(session, week)))


@app.command("predict-all")
def predict_all() -> None:
    typer.echo("[StatsKing] 확인된 문제 데이터가 없습니다.")
    typer.echo("[Daily Picks] 확인된 문제 데이터가 없습니다.")
    predict_weekly6()


@app.command("status")
def status() -> None:
    with _session() as session:
        count = len(session.scalars(select(Weekly6Round)).all())
    typer.echo(f"Weekly 6 저장 주차: {count}")


if __name__ == "__main__":
    app()
