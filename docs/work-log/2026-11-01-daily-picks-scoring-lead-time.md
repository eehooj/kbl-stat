# Daily Picks 득점 우위시간

## 목표와 완료 시각

- 목표: 공식 문자중계 화면의 득점 흐름으로 팀별 득점 우위시간을 계산하고 마지막 미지원 Daily Picks 문항을 추천 가능하게 만든다.
- 완료: 2026-11-01 (Asia/Seoul)

## 계산 기준

- 공식 `문자중계` 표에 표시된 3점슛·2점슛·덩크슛·자유투 성공 이벤트를 시간순으로 재생한다.
- 각 득점 시각 사이의 시간을 그 구간에 앞서 있던 팀에 배정한다.
- 동점 구간은 어느 팀에도 배정하지 않는다.
- 정규 쿼터는 10분, 연장 쿼터는 5분으로 처리한다.
- 문자중계로 재구성한 양 팀 최종 득점이 경기요약의 공식 합계와 정확히 일치할 때만 저장한다.

## 변경 내용

- `migrations/versions/0021_visible_game_scoring_lead.py`, `app/models.py`
  - 팀 경기 특수 기록에 초 단위 `scoring_lead_seconds`를 추가했다.
- `app/services/play_by_play_collection.py`
  - 쿼터와 연장전의 득점 이벤트를 재생해 우위시간을 계산한다.
  - 문자중계 득점 합계와 공식 최종 점수의 일치 검증을 추가했다.
  - 계산 버전을 `visible-play-by-play-v4`로 갱신했다.
- `app/services/daily_picks_schedule_linking.py`, `app/services/daily_picks_recommendation.py`
  - `득점 우위시간`을 일반 득점보다 먼저 분류하고 최근 최대 5경기 평균을 비교한다.
- `README.md`, 테스트
  - 계산·검증 기준을 문서화하고 동점·선두 구간 및 문항 분류를 검증한다.

## 실행·검증

```bash
python -m alembic upgrade head
# 0021_scoring_lead (head)
python -m app.cli backfill-game-special-scoring
# 저장된 공식 경기 URL 43건 / 팀 특수 기록 86건 / 일정 미연결 0건
python -m pytest -q
# 41 passed
python -m ruff check app tests migrations
# All checks passed!
python -m app.cli backtest-daily-picks
# 공식 정답 20건 / 평가 가능 20건 / 적중 11건 / 적중률 55.0%
```

- 43경기 모두 문자중계 재구성 득점과 공식 최종 점수가 일치했다.
- 86개 팀 행 모두 우위시간이 채워졌으며 범위는 0~2387초였다.
- 2026-10-28 문제: 최근 5경기 평균 1151.8초 대 1231.2초로 원주 DB를 추천했고 공식 정답과 일치했다.
- 이전 19건 평가·10건 적중·52.6%에서 20건 평가·11건 적중·55.0%로 바뀌었다.
- 수집된 공식 정답 20건에서 미지원 지표와 최근 기록 부족으로 제외되는 문항은 더 이상 없다.

## 외부 데이터와 제한 사항

- 공식 KBL 경기기록의 브라우저 렌더링 화면과 화면의 `문자중계` 표만 사용했다.
- 내부 API는 직접 호출하지 않았다.
- 공식 화면의 명시적 성공 이벤트만 사용하며 슛 결과나 시간을 추정해 보완하지 않는다.
- 현재 백테스트 표본은 공식 정답 20건으로 작으므로 55.0%를 장기 성능으로 해석하지 않는다.

## 다음 작업 후보

- Daily Picks 공식 정답 표본을 날짜별로 계속 누적해 지표별 적중률과 표본 수를 함께 보고한다.
- 현재 평균 비교 기준을 유지한 채 충분한 표본이 쌓이면 지표별 최근 경기 수와 가중치를 검증한다.
