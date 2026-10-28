import typer
from sqlalchemy import create_engine, select

from app.collectors.official_pages import KBL_BASE_URL, KBLRenderedPageClient
from app.config import get_settings
from app.database import Base, make_session_factory
from app.models import Weekly6Round
from app.services.team_form_features import compute_and_store_team_forms, parse_as_of
from app.services.visible_record_collection import collect_season_leaders
from app.services.visible_schedule_collection import (
    collect_visible_schedule,
    collect_visible_schedule_pages,
)
from app.services.visible_team_ranking_collection import collect_visible_team_rankings
from app.services.weekly6_collection import Weekly6Visibility, collect_weekly6_page
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
        visibility, count = collect_weekly6_page(session, page)
    if visibility is Weekly6Visibility.BODY_NOT_VISIBLE:
        typer.echo("공식 Weekly 6 화면 본문이 표시되지 않았습니다. 문제 미등록과 렌더링 실패를 구분할 수 없어 예측을 만들지 않았습니다.")
        return
    typer.echo(f"공식 Weekly 6 화면에서 후보 경기 {count}건을 수집·갱신했습니다: {page.url}")


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


@app.command("collect-season-schedule")
def collect_season_schedule(season: str = typer.Option(..., "--season", help="예: 2026-2027")) -> None:
    """선택 시즌의 10월~5월 일정 화면을 월별로 렌더링해 수집한다."""
    pages = KBLRenderedPageClient().render_schedule_season(season)
    with _session() as session:
        games, empty_pages = collect_visible_schedule_pages(session, pages)
    typer.echo(
        f"{season} 시즌 일정 화면 {len(pages)}개월을 확인했습니다. "
        f"표시된 경기 {games}건을 수집·갱신했고, 경기 카드가 없는 화면은 {empty_pages}개월입니다."
    )


@app.command("collect-team-rankings")
def collect_team_rankings() -> None:
    """공식 팀 순위 화면에 표시된 값만 수집한다."""
    page = KBLRenderedPageClient().render_team_rankings()
    with _session() as session:
        count = collect_visible_team_rankings(session, page)
    typer.echo(f"공식 팀 순위 화면에 표시된 팀 성적 {count}건을 수집·갱신했습니다.")


@app.command("compute-team-form")
def compute_team_form(
    season: str = typer.Option(..., "--season", help="예: 2026-2027"),
    as_of: str | None = typer.Option(None, "--as-of", help="예: 2026-10-29T19:00+09:00"),
) -> None:
    """기준 시각 이전에 완료된 경기만 사용해 팀 폼을 계산한다."""
    cutoff = parse_as_of(as_of)
    with _session() as session:
        forms = compute_and_store_team_forms(session, season, cutoff)
    typer.echo(f"{season} 시즌 팀 폼 {len(forms)}건을 {cutoff.isoformat()} 기준으로 계산·저장했습니다.")


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
