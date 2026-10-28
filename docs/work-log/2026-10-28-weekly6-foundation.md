# Weekly 6 기반 및 Phase 1 프로젝트 초기화

- 완료일: 2026-10-28 (Asia/Seoul)
- 범위: KBL 예측 프로젝트 초기 구조와 Weekly 6 지원 추가

## 완료 내용

- Python 3.12 프로젝트, PostgreSQL Docker Compose, SQLAlchemy, Alembic, Typer CLI 구성
- 시즌·팀·선수·경기·팀/선수 경기 기록과 챌린지 공통 테이블 구성
- `stats_king`, `daily_picks`, `weekly6` 챌린지 유형 추가
- Weekly 6 주차와 후보 경기 관계를 위한 `weekly6_rounds`, `weekly6_fixtures` 테이블 추가
- 공식 HTML 원문, SHA-256 해시, 수집 시각을 보존하는 수집 이력 추가
- `collect-weekly6`, `predict-weekly6`, `predict-all`, `status` CLI 추가
- 데이터 부족 또는 확률 보정 전에는 가상 추천·승리 확률·전체 적중 확률을 출력하지 않는 기준선 추가
- 이후 작업의 완료 기록을 남길 `docs/work-log/` 규칙과 작성 안내 추가

## 공식 화면 확인 결과

2026-10-28에 KBL Weekly 6 공식 페이지를 브라우저로 확인했다.

- 주차 범위, 마감 카운트다운, 후보 경기의 일시·장소·팀 대진이 표시됐다.
- 확인 시점 화면에는 11개 후보 경기가 있고 “응모를 위한 6 경기 중 0 경기 선택”이라고 표시됐다.
- 따라서 현재 확인된 규칙은 후보 경기에서 6개를 선택하는 방식이다. ‘정확히 6경기의 승패 전체를 맞히는 게임’으로 가정하지 않는다.
- 문제 고유 ID, 내부 API, 전체 채점 규칙, 과거 문제/정답 구조는 아직 검증되지 않아 코드에 추측으로 넣지 않았다.

## 검증

```powershell
python -m pytest -p no:cacheprovider -q
python -m ruff check app tests migrations
$env:KBL_DATABASE_URL='sqlite:///./migration_check.db'; alembic upgrade head
python -m app.cli collect-weekly6
```

결과:

- 단위 테스트 2개 통과
- Ruff 검사 통과
- Alembic 초기 마이그레이션 통과
- `collect-weekly6`로 KBL 공식 페이지의 원문 1건 수집 성공

## 다른 컴퓨터에서 시작하기

```powershell
git clone https://github.com/eehooj/kbl-stat.git
cd kbl-stat
Copy-Item .env.example .env
docker compose up -d
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e ".[dev]"
alembic upgrade head
python -m app.cli status
```

`.env`에는 개인 비밀값을 넣을 수 있으나 Git에 추가하지 않는다.

## 남은 작업

- 공식 일정·경기 상세 기록 응답 구조를 실제로 검증한 뒤 Phase 1 수집 파서 구현
- StatsKing 및 Daily Picks의 실제 문제·선택지·정답 구조 확인
- Weekly 6의 고유 ID·마감 시각·정답·채점 규칙 파서 구현
- 시점 고정 백테스트와 승리 확률 보정 구현
