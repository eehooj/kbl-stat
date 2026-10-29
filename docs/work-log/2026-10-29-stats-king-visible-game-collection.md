# StatsKing 화면 경기 카드 수집

- 완료일: 2026-10-29 (Asia/Seoul)
- 목표: 공식 StatsKing 화면에서 실제로 보이는 경기 정보만 저장하고, 보이지 않는 선수 선택지나 기록 항목은 추측하지 않는다.

## 확인한 화면

공식 [StatsKing](https://www.kbl.or.kr/game/challenge/stats) 화면을 브라우저로 렌더링해 다음을 확인했다.

- 당일 날짜
- 현재 경기의 시각과 장소
- 화면상 두 팀 표기
- 참여 상태(`미참여`)
- 상대적인 게임 마감 카운트다운 문구

같은 화면에는 선수 선택지, 기록별 문제 문구, 공식 문제 ID, 절대 마감 시각, 정답·채점 규칙이 표시되지 않았다.

## 변경

- `stats_king_visible_games` 테이블과 Alembic `0009` migration을 추가했다.
- `collect-stats-king` CLI를 추가했다.
- 화면에 경기 카드의 필수 값이 모두 보일 때만 시각·장소·두 팀의 표시 순서·참여 상태·상대 마감 문구를 저장한다.
- 팀 표기 순서는 홈/원정으로 해석하지 않는다.
- 화면 원문과 수집 이력은 카드 미표시 상태에서도 남긴다.
- 선수 선택지와 기록 항목이 화면에 보이지 않으므로 `challenge_questions`, `challenge_options`, 예측 결과는 만들지 않는다.

## 실행

```powershell
alembic upgrade head
python -m app.cli collect-stats-king
```

## 실제 검증

별도 SQLite DB에서 공식 StatsKing 화면을 다시 렌더링했다.

- StatsKing 경기 카드 1건 저장
- `stats_king` 유형 챌린지 문제 0건 저장
- 단위 테스트 20건 통과, Ruff 검사 통과

## 다음 단계

- 공식 화면에 선수 목록과 기록별 선택지가 실제로 표시되는 시점에만 해당 구조를 확인한 뒤 `challenge_questions`·`challenge_options` 파서를 추가한다.
- 공식 정답 공개 화면과 채점 규칙이 확인되면 결과 수집 및 시점 고정 백테스트를 추가한다.
