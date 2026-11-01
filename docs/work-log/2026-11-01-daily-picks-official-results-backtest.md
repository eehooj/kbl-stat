# Daily Picks 공식 정답·백테스트

## 목표와 완료 시각

- 목표: 공식 과거 Daily Picks 화면의 정답을 문제와 연결하고, 대상 경기 이전 기록만 사용해 현재 추천 규칙을 백테스트한다.
- 완료: 2026-11-01 (Asia/Seoul)

## 변경 기능과 주요 파일

- `app/collectors/official_pages.py`
  - 공식 화면의 이전 날짜 버튼으로 과거 Daily Picks를 탐색한다.
  - 종료된 문제에서 비활성 선택지 중 정답 상태(`true`)로 표시된 라벨을 Pick 순서대로 읽는다.
  - 정답자 이름과 마스킹 전화번호 목록은 보존하는 문제 증거에서 제외한다.
- `app/services/daily_picks_result_collection.py`
  - 화면상 문제·선택지와 정답 개수가 정확히 일치할 때만 `challenge_results`에 연결한다.
  - 정답 라벨이 저장된 선택지에 없으면 실패시킨다.
- `app/services/daily_picks_recommendation.py`
  - 개별 과거 문제도 같은 추천 규칙으로 평가하도록 분리했다.
  - 공식 정답이 있는 문제의 평가 가능 건수, 적중 건수, 적중률과 제외 사유를 계산한다.
- `app/cli.py`
  - `collect-daily-picks-results --days N`, `backtest-daily-picks` 명령을 추가했다.
- `tests/test_daily_picks_result_collection.py`
  - 정답 저장, 문제·정답 수 불일치 거부, 정답자 목록 제외를 검증한다.

## 실행·검증

```bash
python -m app.cli collect-daily-picks-results --days 4
# 공식 과거 화면 4일, 문제 20건, 정답 20건
python -m app.cli backtest-daily-picks
# 공식 정답 20건 / 평가 가능 11건 / 적중 5건 / 적중률 45.5%
# 평가 제외: 질문 지표 미확인 5건, 최근 기록 부족 4건
python -m pytest -q
# 40 passed
python -m ruff check app tests
# All checks passed!
```

정답 연결 범위는 2026-10-28부터 2026-10-31까지이며 날짜별 5문제, 총 20문제다. 모든 문제는 공식 일정과 연결됐다.

## 외부 데이터와 제한 사항

- 공식 KBL Daily Picks 브라우저 렌더링 화면만 사용했고 내부 API는 직접 호출하지 않았다.
- 과거 화면에서 정답 선택지는 비활성화되고 정답 상태 스타일로 한 개가 표시된다. 이 상태와 화면 라벨을 함께 확인했다.
- 정답자 목록은 문제·정답 수집에 필요하지 않아 새 수집 증거에서 제외한다.
- 백테스트는 저장된 추천이 아니라 현재 모델을 과거 시점 데이터에 다시 적용한 회고형 결과다.
- 미지원 지표 또는 양 팀 각각 최소 3경기 기록이 없는 문제는 적중률 분모에 넣지 않는다.
- 표본 11건의 45.5%는 모델 성능을 확정할 만큼 충분하지 않다.

## 다른 컴퓨터에서 재현

```bash
source .venv/bin/activate
alembic upgrade head
python -m app.cli collect-season-schedule --season 2026-2027
python -m app.cli collect-game-player-stats --limit 43
python -m app.cli collect-daily-picks-results --days 4
python -m app.cli backtest-daily-picks
```

## 남은 작업과 주의점

- 미지원 지표인 득점 우위시간, 자유투 성공, 굿디펜스, 3점슛 성공률, 속공 득점의 화면 기록 수집 가능성을 검증한다.
- 더 많은 과거 날짜의 공식 정답을 수집해 지표별 적중률과 신뢰구간을 계산한다.
- StatsKing 과거 공식 정답 화면도 별도로 조사해 같은 방식의 백테스트를 추가한다.
