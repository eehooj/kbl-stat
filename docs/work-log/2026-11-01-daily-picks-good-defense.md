# Daily Picks 굿디펜스

## 목표와 완료 시각

- 목표: 공식 문자중계 화면에서 굿디펜스를 정확히 집계할 수 있는지 검증하고 Daily Picks 추천에 연결한다.
- 완료: 2026-11-01 (Asia/Seoul)

## 화면 검증

최근 공식 완료 경기 5건의 `문자중계` 쿼터 탭에서 `선수명 굿디펜스` 이벤트가 실제 표 행으로 표시되는 것을 확인했다. 예시는 다음과 같다.

- `S49G01N43/20261029`: `윤기찬 굿디펜스`
- `S49G01N42/20261028`: `정효근 굿디펜스`
- `S49G01N41/20261027`: `김형빈 굿디펜스`, `윤기찬 굿디펜스`

선수 이름에 `굿`이 포함된 `아치 굿윈`을 잘못 세지 않도록, 이벤트 문구가 공백 뒤 `굿디펜스`로 끝나는 경우만 집계한다.

## 변경 내용

- `migrations/versions/0020_visible_game_good_defense.py`, `app/models.py`
  - 팀 경기 특수 기록에 `good_defense`를 추가했다.
- `app/services/play_by_play_collection.py`
  - 공식 문자중계의 팀별 굿디펜스 이벤트 수를 집계한다.
  - 계산 버전을 `visible-play-by-play-v3`로 갱신했다.
- `app/services/daily_picks_schedule_linking.py`, `app/services/daily_picks_recommendation.py`
  - 굿디펜스 문항을 분류하고 대상 경기 이전 최근 최대 5경기의 팀별 평균을 비교한다.
- `app/cli.py`, `README.md`
  - 저장된 공식 경기 URL을 화면에서 다시 여는 `backfill-game-special-scoring` 명령을 추가했다.
- 테스트
  - 굿디펜스 집계·문항 분류 및 `굿윈` 이름 오인 방지를 검증한다.

## 실행·검증

```bash
python -m alembic upgrade head
# 0020_good_defense (head)
python -m app.cli backfill-game-special-scoring
# 저장된 공식 경기 URL 43건 / 팀 특수 기록 86건 / 일정 미연결 0건
python -m pytest -q
# 40 passed
python -m ruff check app tests migrations
# All checks passed!
python -m app.cli backtest-daily-picks
# 공식 정답 20건 / 평가 가능 19건 / 적중 10건 / 적중률 52.6%
# 평가 제외: 질문 지표 미확인 1건
```

- 86개 팀 행 모두 `good_defense`가 채워졌다.
- 전체 굿디펜스 이벤트는 112건이며 팀 한 경기 최댓값은 6건이다.
- 2026-10-31 문제: 최근 5경기 평균 2.6 대 0.2로 안양 정관장을 추천했고 공식 정답과 일치했다.
- 43경기 전체를 다시 수집하면서 벤치·세컨드 찬스 표본도 함께 완성되어, 이전 14건 평가·7건 적중·50.0%에서 19건 평가·10건 적중·52.6%로 바뀌었다.

## 외부 데이터와 제한 사항

- 공식 KBL 경기기록의 브라우저 렌더링 화면과 화면의 `문자중계` 표만 사용했다.
- 내부 API는 직접 호출하지 않았다.
- 굿디펜스의 의미를 추론하지 않고, 공식 화면이 명시적으로 `굿디펜스`라고 표시한 이벤트만 센다.

## 남은 작업

- 마지막 미지원 문항인 득점 우위시간을 공식 문자중계의 득점 흐름으로 계산한다.
