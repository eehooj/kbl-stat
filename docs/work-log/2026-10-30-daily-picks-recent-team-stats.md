# Daily Picks 최근 팀 기록 기준선

- 완료일: 2026-10-30 (Asia/Seoul)
- 목표: Daily Picks 팀 기록 질문을 공개 완료 경기의 최근 팀 박스스코어로 비교하고, 데이터 부족 시 추천을 보류한다.

## 변경

- `predict-daily-picks` CLI를 추가했다.
- 질문 문구의 `2점슛 성공`을 지표로 분류한다.
- 스틸, 2점슛 성공, 턴오버, 블록슛, 개인 파울을 선수 박스스코어에서 팀 경기 단위로 합산한다.
- 대상 경기 시작 시각보다 이전의 기록만 사용하고, 팀별 최대 최근 5경기를 사용한다.
- 양 팀 모두 최소 3경기가 있어야 추천한다. 그렇지 않거나 평균이 같으면 추천 보류한다.

## 실행

```powershell
python -m app.cli collect-schedule
python -m app.cli collect-game-player-stats --limit 20
python -m app.cli collect-daily-picks
python -m app.cli predict-daily-picks
```

## 실제 검증

- Alembic `0014` migration 적용 확인
- 현재 DB의 박스스코어 수집량이 부족한 상태에서 다섯 Daily Picks 항목이 모두 `추천 보류`로 출력됨
- 단위 테스트 26건 통과, Ruff 검사 통과

## 제한

- 결장·출전 정보는 아직 Daily Picks의 수치 조정에 반영하지 않는다. 향후 주요 결장이 확인되면 신뢰도 하향 또는 추천 보류 근거로 추가한다.
- 최근 팀 기록이 수집되기 전에는 가상 추천을 만들지 않는다.
