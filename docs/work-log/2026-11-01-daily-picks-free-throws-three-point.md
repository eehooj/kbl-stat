# Daily Picks 자유투·3점슛 성공률

## 목표와 완료 시각

- 목표: 공식 선수 박스스코어의 자유투 성공과 3점슛 성공·시도를 수집해 Daily Picks 추천과 백테스트에 연결한다.
- 완료: 2026-11-01 (Asia/Seoul)

## 변경 기능과 주요 파일

- `app/models.py`, `migrations/versions/0019_player_game_shooting.py`
  - 선수 경기 기록에 `three_point_made`, `three_point_attempted`, `free_throw_made`를 추가했다.
- `app/services/player_game_stat_collection.py`
  - 공식 선수기록 표의 3PM·3PA·FTM 화면 열을 파싱한다.
  - 보존된 43경기 화면을 다시 읽는 슈팅 백필을 추가했다.
  - 양 팀에 동명이인이 출전한 경우 경기요약의 팀 표시 순서 또는 선수 섹션의 팀 다수결로 `URL+팀+선수명`을 연결한다.
  - 같은 문제가 있던 기존 덩크 백필도 팀까지 포함해 갱신하도록 수정했다.
- `app/services/daily_picks_schedule_linking.py`
  - `3점슛 성공률`을 `three_point_pct`로 분류한다.
  - 공식 문제 화면의 `자유튜` 오타와 정상 `자유투`를 모두 `free_throw_made`로 분류한다.
- `app/services/daily_picks_recommendation.py`
  - 최근 최대 5경기의 팀 3PM/3PA 합계로 3점슛 성공률을 계산한다.
  - 최근 최대 5경기의 팀 자유투 성공 합계로 경기당 평균을 계산한다.
- `app/cli.py`
  - `backfill-game-shooting` 명령을 추가했다.

## 실행·검증

```bash
python -m alembic upgrade head
# 0019_game_shooting
python -m app.cli backfill-game-shooting
# 889행 갱신
python -m app.cli backfill-game-dunks
# 889행 갱신
```

로컬 DB의 선수 경기 기록 889행 모두에 3점슛 성공·시도, 자유투 성공, 덩크 성공 값이 채워졌다.

동명이인 예외:

- `S49G01N2/20261003`: 양 팀의 최승욱
- `S49G01N4/20261004`: 양 팀의 이정현

두 경기 모두 팀까지 포함해 각 선수 행을 별도로 갱신했다.

백테스트 변화:

- 이전: 공식 정답 20건, 평가 가능 11건, 적중 5건, 45.5%
- 이후: 공식 정답 20건, 평가 가능 13건, 적중 6건, 46.2%
- 2026-10-31 3점슛 성공률: 안양 정관장 추천, 공식 정답 안양 정관장, 적중
- 2026-10-28 자유투 성공: 원주 DB 추천, 공식 정답 대구 한국가스공사, 실패
- 평가 제외: 미지원 지표 3건, 최근 기록 부족 4건

```bash
python -m pytest -q
# 40 passed
python -m ruff check app tests
# All checks passed!
```

## 외부 데이터와 제한 사항

- 공식 KBL 선수 경기기록의 브라우저 렌더링 화면과 이미 보존된 동일 화면만 사용했다. 내부 API는 직접 호출하지 않았다.
- 3점슛 성공률은 최근 경기별 성공률의 단순 평균이 아니라 최근 경기 전체 성공 수/전체 시도 수로 계산한다.
- 자유투 문제는 공식 화면 문구의 `자유튜` 오타를 그대로 인식한다.
- 표본이 각각 한 문제뿐이므로 지표별 성능을 판단할 수 없다.

## 다른 컴퓨터에서 재현

```bash
source .venv/bin/activate
alembic upgrade head
python -m app.cli backfill-game-shooting
python -m app.cli collect-daily-picks-results --days 4
python -m app.cli backtest-daily-picks
```

## 남은 작업과 주의점

- 속공 득점과 굿디펜스를 공식 문자중계 이벤트로 정확히 집계할 수 있는지 검증한다.
- 득점 우위시간은 전체 득점 흐름과 동점 구간을 재생하는 별도 계산이 필요하다.
- 자유투와 3점슛 성공률 문제 표본을 더 모아 지표별 적중률을 평가한다.
