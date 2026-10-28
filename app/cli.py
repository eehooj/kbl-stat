import typer
from sqlalchemy import create_engine, select

from app.collectors.official_pages import KBL_BASE_URL, KBLRenderedPageClient
from app.config import get_settings
from app.database import Base, make_session_factory
from app.models import Weekly6Round
from app.services.visible_record_collection import collect_season_leaders
from app.services.visible_schedule_collection import collect_visible_schedule
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
    """공식 Weekly 6 화면에 렌더링된 텍스트만 보존한다."""
    page = KBLRenderedPageClient().render(f"{KBL_BASE_URL}/game/challenge/weekly6")
    with _session() as session:
        from app.services.visible_record_collection import collect_rendered_page
        collect_rendered_page(session, page, "Weekly 6 화면 원문; 규칙 추출 전")
    typer.echo(f"공식 Weekly 6 화면을 확인했습니다: {page.url}\n표시되지 않은 문제 데이터는 저장하지 않았습니다.")


@app.command("collect-season-leaders")
def collect_season_leaders_command() -> None:
    """공식 기록 페이지에 화면상 표시되는 시즌 리더를 수집한다."""
    page = KBLRenderedPageClient().render_season_leaders()
    with _session() as session:
        count = collect_season_leaders(session, page)
    typer.echo(f"공식 기록 화면에 표시된 시즌 리더 {count}건을 수집·갱신했습니다.")


@app.command("collect-schedule")
def collect_schedule() -> None:
    """공식 일정 화면에 표시된 경기 카드만 수집한다."""
    page = KBLRenderedPageClient().render_match_schedule()
    with _session() as session:
        count = collect_visible_schedule(session, page)
    typer.echo(f"공식 일정 화면에 표시된 경기 {count}건을 수집·갱신했습니다.")


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
