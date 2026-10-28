import enum
from datetime import datetime

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class ChallengeType(str, enum.Enum):
    STATS_KING = "stats_king"
    DAILY_PICKS = "daily_picks"
    WEEKLY6 = "weekly6"


class Season(Base):
    __tablename__ = "seasons"
    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(20), unique=True)
    name: Mapped[str | None] = mapped_column(String(100))


class Team(Base):
    __tablename__ = "teams"
    id: Mapped[int] = mapped_column(primary_key=True)
    official_id: Mapped[str | None] = mapped_column(String(80), unique=True)
    name: Mapped[str] = mapped_column(String(100), unique=True)


class Player(Base):
    __tablename__ = "players"
    id: Mapped[int] = mapped_column(primary_key=True)
    official_id: Mapped[str | None] = mapped_column(String(80), unique=True)
    name: Mapped[str] = mapped_column(String(100))
    team_id: Mapped[int | None] = mapped_column(ForeignKey("teams.id"))


class Game(Base):
    __tablename__ = "games"
    id: Mapped[int] = mapped_column(primary_key=True)
    official_id: Mapped[str | None] = mapped_column(String(80), unique=True)
    season_id: Mapped[int | None] = mapped_column(ForeignKey("seasons.id"))
    starts_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    home_team_id: Mapped[int] = mapped_column(ForeignKey("teams.id"))
    away_team_id: Mapped[int] = mapped_column(ForeignKey("teams.id"))
    home_score: Mapped[int | None] = mapped_column(Integer)
    away_score: Mapped[int | None] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(30), default="scheduled")
    source_url: Mapped[str | None] = mapped_column(String(500))
    fetched_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    __table_args__ = (UniqueConstraint("season_id", "official_id", name="uq_game_official_per_season"),)

    home_team: Mapped[Team] = relationship(foreign_keys=[home_team_id])
    away_team: Mapped[Team] = relationship(foreign_keys=[away_team_id])


class TeamGameStat(Base):
    __tablename__ = "team_game_stats"
    id: Mapped[int] = mapped_column(primary_key=True)
    game_id: Mapped[int] = mapped_column(ForeignKey("games.id"))
    team_id: Mapped[int] = mapped_column(ForeignKey("teams.id"))
    stats: Mapped[dict] = mapped_column(JSON, default=dict)
    source_updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    __table_args__ = (UniqueConstraint("game_id", "team_id", name="uq_team_game_stat"),)


class PlayerGameStat(Base):
    __tablename__ = "player_game_stats"
    id: Mapped[int] = mapped_column(primary_key=True)
    game_id: Mapped[int] = mapped_column(ForeignKey("games.id"))
    player_id: Mapped[int] = mapped_column(ForeignKey("players.id"))
    played: Mapped[bool] = mapped_column(Boolean, default=False)
    stats: Mapped[dict] = mapped_column(JSON, default=dict)
    __table_args__ = (UniqueConstraint("game_id", "player_id", name="uq_player_game_stat"),)


class SeasonPlayerStat(Base):
    """A value shown on the rendered season-leader page, not a game box score."""
    __tablename__ = "season_player_stats"
    id: Mapped[int] = mapped_column(primary_key=True)
    season_id: Mapped[int] = mapped_column(ForeignKey("seasons.id"))
    metric: Mapped[str] = mapped_column(String(50))
    rank: Mapped[int] = mapped_column(Integer)
    player_name: Mapped[str] = mapped_column(String(100))
    team_name: Mapped[str] = mapped_column(String(100))
    value: Mapped[float] = mapped_column(Float)
    source_url: Mapped[str] = mapped_column(String(500))
    observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    __table_args__ = (UniqueConstraint("season_id", "metric", "player_name", "team_name", name="uq_season_leader_player"),)


class VisibleScheduleGame(Base):
    """A game exactly as shown in the rendered schedule; no home/away inference."""
    __tablename__ = "visible_schedule_games"
    id: Mapped[int] = mapped_column(primary_key=True)
    observed_key: Mapped[str] = mapped_column(String(64), unique=True)
    season_id: Mapped[int] = mapped_column(ForeignKey("seasons.id"))
    starts_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    competition: Mapped[str] = mapped_column(String(50))
    venue: Mapped[str] = mapped_column(String(150))
    first_team_name: Mapped[str] = mapped_column(String(100))
    second_team_name: Mapped[str] = mapped_column(String(100))
    first_score: Mapped[int | None] = mapped_column(Integer)
    second_score: Mapped[int | None] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(30))
    source_url: Mapped[str] = mapped_column(String(500))
    observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class TeamSeasonStanding(Base):
    """A team standing row exactly as displayed on KBL's team-ranking page."""
    __tablename__ = "team_season_standings"
    id: Mapped[int] = mapped_column(primary_key=True)
    season_id: Mapped[int] = mapped_column(ForeignKey("seasons.id"))
    team_name: Mapped[str] = mapped_column(String(100))
    rank: Mapped[int] = mapped_column(Integer)
    wins: Mapped[int] = mapped_column(Integer)
    losses: Mapped[int] = mapped_column(Integer)
    win_rate: Mapped[float] = mapped_column(Float)
    games_back: Mapped[float] = mapped_column(Float)
    recent_five: Mapped[str] = mapped_column(String(20))
    streak: Mapped[str] = mapped_column(String(20))
    home_record: Mapped[str] = mapped_column(String(20))
    away_record: Mapped[str] = mapped_column(String(20))
    next_opponent_name: Mapped[str | None] = mapped_column(String(100))
    head_to_head: Mapped[str | None] = mapped_column(String(30))
    source_url: Mapped[str] = mapped_column(String(500))
    observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    __table_args__ = (UniqueConstraint("season_id", "team_name", name="uq_team_season_standing"),)


class TeamFormSnapshot(Base):
    """Leakage-safe features derived solely from completed visible schedule games."""
    __tablename__ = "team_form_snapshots"
    id: Mapped[int] = mapped_column(primary_key=True)
    season_id: Mapped[int] = mapped_column(ForeignKey("seasons.id"))
    team_name: Mapped[str] = mapped_column(String(100))
    as_of: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    games_played: Mapped[int] = mapped_column(Integer)
    wins: Mapped[int] = mapped_column(Integer)
    losses: Mapped[int] = mapped_column(Integer)
    recent_five_wins: Mapped[int] = mapped_column(Integer)
    recent_five_losses: Mapped[int] = mapped_column(Integer)
    recent_ten_wins: Mapped[int] = mapped_column(Integer)
    recent_ten_losses: Mapped[int] = mapped_column(Integer)
    average_points_for: Mapped[float] = mapped_column(Float)
    average_points_against: Mapped[float] = mapped_column(Float)
    rest_days: Mapped[int | None] = mapped_column(Integer)
    calculation_version: Mapped[str] = mapped_column(String(50))
    calculated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    __table_args__ = (UniqueConstraint("season_id", "team_name", "as_of", name="uq_team_form_snapshot"),)


class ChallengeQuestion(Base):
    __tablename__ = "challenge_questions"
    id: Mapped[int] = mapped_column(primary_key=True)
    challenge_type: Mapped[ChallengeType] = mapped_column(Enum(ChallengeType))
    official_id: Mapped[str | None] = mapped_column(String(100))
    question_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    text: Mapped[str | None] = mapped_column(Text)
    closes_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    source_url: Mapped[str] = mapped_column(String(500))
    raw_payload: Mapped[dict | None] = mapped_column(JSON)


class ChallengeOption(Base):
    __tablename__ = "challenge_options"
    id: Mapped[int] = mapped_column(primary_key=True)
    question_id: Mapped[int] = mapped_column(ForeignKey("challenge_questions.id"))
    official_id: Mapped[str | None] = mapped_column(String(100))
    label: Mapped[str] = mapped_column(String(250))
    payload: Mapped[dict | None] = mapped_column(JSON)


class ChallengePrediction(Base):
    __tablename__ = "challenge_predictions"
    id: Mapped[int] = mapped_column(primary_key=True)
    question_id: Mapped[int] = mapped_column(ForeignKey("challenge_questions.id"))
    option_id: Mapped[int | None] = mapped_column(ForeignKey("challenge_options.id"))
    predicted_probability: Mapped[float | None] = mapped_column(Float)
    confidence: Mapped[str] = mapped_column(String(30))
    rationale: Mapped[dict] = mapped_column(JSON, default=dict)
    model_version: Mapped[str] = mapped_column(String(100))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class ChallengeResult(Base):
    __tablename__ = "challenge_results"
    id: Mapped[int] = mapped_column(primary_key=True)
    question_id: Mapped[int] = mapped_column(ForeignKey("challenge_questions.id"), unique=True)
    official_answer: Mapped[dict | None] = mapped_column(JSON)
    scoring_rule: Mapped[dict | None] = mapped_column(JSON)
    verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class Weekly6Round(Base):
    __tablename__ = "weekly6_rounds"
    id: Mapped[int] = mapped_column(primary_key=True)
    official_id: Mapped[str | None] = mapped_column(String(100), unique=True)
    week_label: Mapped[str] = mapped_column(String(50), unique=True)
    opens_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    closes_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    selection_count: Mapped[int | None] = mapped_column(Integer)
    source_url: Mapped[str] = mapped_column(String(500))
    raw_payload: Mapped[dict | None] = mapped_column(JSON)
    fixtures: Mapped[list["Weekly6Fixture"]] = relationship(back_populates="round")


class Weekly6Fixture(Base):
    __tablename__ = "weekly6_fixtures"
    id: Mapped[int] = mapped_column(primary_key=True)
    round_id: Mapped[int] = mapped_column(ForeignKey("weekly6_rounds.id"))
    game_id: Mapped[int | None] = mapped_column(ForeignKey("games.id"))
    ordinal: Mapped[int] = mapped_column(Integer)
    starts_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    home_team_name: Mapped[str] = mapped_column(String(100))
    away_team_name: Mapped[str] = mapped_column(String(100))
    venue: Mapped[str | None] = mapped_column(String(150))
    official_result: Mapped[str | None] = mapped_column(String(100))
    round: Mapped[Weekly6Round] = relationship(back_populates="fixtures")
    __table_args__ = (UniqueConstraint("round_id", "ordinal", name="uq_weekly6_round_ordinal"),)


class CollectionLog(Base):
    __tablename__ = "collection_logs"
    id: Mapped[int] = mapped_column(primary_key=True)
    source_url: Mapped[str] = mapped_column(String(500))
    status: Mapped[str] = mapped_column(String(30))
    fetched_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    response_sha256: Mapped[str | None] = mapped_column(String(64))
    detail: Mapped[str | None] = mapped_column(Text)


class RawSourceDocument(Base):
    """Immutable acquisition evidence; parsers can always be re-run against it."""
    __tablename__ = "raw_source_documents"
    id: Mapped[int] = mapped_column(primary_key=True)
    source_url: Mapped[str] = mapped_column(String(500))
    fetched_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    content_hash: Mapped[str] = mapped_column(String(64), unique=True)
    content_type: Mapped[str] = mapped_column(String(100), default="text/html")
    body: Mapped[str] = mapped_column(Text)
