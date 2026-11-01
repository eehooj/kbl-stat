# Daily Picks 벤치·세컨드 찬스 득점

## 목표와 완료 시각

- 목표: 공식 KBL 문자중계 화면만으로 벤치 득점과 세컨드 찬스 득점을 검증·구현한다.
- 완료: 2026-11-01 (Asia/Seoul)

## 변경 기능과 주요 파일

- `app/collectors/official_pages.py`: 공개 경기기록의 문자중계와 Q1~Q4 화면에서 좌·우 팀 이벤트를 읽는다.
- `app/services/play_by_play_collection.py`: 1쿼터 10:00의 팀별 `교체(IN)` 5명을 선발로 확정한다. 비선발 득점을 벤치 득점으로, 공격리바운드부터 점유권 종료 전까지의 득점을 세컨드 찬스 득점으로 계산한다.
- `app/models.py`, `migrations/versions/0017_visible_game_special_stats.py`: 경기·팀별 두 지표, 계산 버전, 출처를 저장한다.
- `app/services/daily_picks_recommendation.py`: 두 지표의 최근 5경기 평균을 Daily Picks 추천에 연결한다.
- `app/cli.py`: `collect-game-special-scoring`과 공개 경기 URL 검증 옵션을 추가했다.
- `tests/test_play_by_play_collection.py`: 선발 판정, 자유투·필드골, 점유권 종료를 검증한다.

## 실행·검증

```bash
python -m pytest -q
# 28 passed
python -m ruff check app tests
# All checks passed!
python -m alembic upgrade head
# 0017_special_scoring
python -m app.cli collect-game-special-scoring \
  --record-url https://www.kbl.or.kr/match/record/S49G01N43/20261029
# 1경기, 팀 특수 득점 2건 저장, 일정 미연결 0건
```

실제 공식 화면 검증 결과:

- 울산 현대모비스: 벤치 40점, 세컨드 찬스 8점
- 부산 KCC: 벤치 21점, 세컨드 찬스 11점
- 벤치 득점은 같은 공식 경기기록 화면의 선수 득점에서 선발 5명을 제외한 합계와 양 팀 모두 일치했다(40=40, 21=21).

## 외부 데이터와 제한 사항

- 공식 KBL 페이지의 브라우저 렌더링 화면만 사용했고 내부 API는 직접 호출하지 않았다.
- 2026-11-01 현재 일정 화면에는 수집 대상 완료 경기 카드가 없어 `--limit 1` 결과가 0건이었다. DB에 연결된 직전 완료 경기의 공개 URL로 실제 검증했다.
- 선발 5명이 화면에 완전하게 표시되지 않으면 잘못 추정하지 않고 실패시킨다.
- 세컨드 찬스 공식 합계가 별도 화면에 표시되지 않아 독립 합계 대조는 할 수 없었다. 공격리바운드 뒤 득점, 상대 리바운드·스틸, 공격 팀 턴오버, 쿼터 종료를 보수적인 점유권 경계로 사용한다.

## 재현 방법

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
alembic upgrade head
python -m app.cli collect-game-special-scoring --limit 5
python -m app.cli predict-daily-picks
```

Chrome이 필요하며 `.env`가 없으면 프로젝트 루트 SQLite DB를 사용한다.

## 남은 작업과 주의점

- 여러 시즌과 연장전 경기로 세컨드 찬스 점유권 규칙을 추가 검증한다.
- 완료 경기 카드가 생기면 `--limit` 경로를 실제 경기로 재검증한다.
- 문자중계가 정정되면 같은 URL을 다시 수집해 계산값을 갱신한다.
