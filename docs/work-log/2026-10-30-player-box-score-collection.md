# 공개 선수 박스스코어 수집

- 완료일: 2026-10-30 (Asia/Seoul)
- 목표: 공개 완료 경기기록에서 선수별 박스스코어를 저장해 StatsKing 최근 폼과 Daily Picks 팀 지표의 근거를 만든다.

## 변경

- `visible_player_game_stats` 테이블과 Alembic `0013` migration을 추가했다.
- `collect-game-player-stats` CLI를 추가했다.
- 현재 일정 화면의 완료 경기 `기록` 버튼을 제한된 양만 열고, 공개 `경기기록` 탭의 홈·원정 선수 행을 저장한다.
- 저장 지표: 출전 시간, 득점, 리바운드, 어시스트, 스틸, 블록, 턴오버, 파울.
- 일정 카드의 짧은 팀명과 상세 기록의 전체 팀명은 같은 날짜의 단일 경기일 때만 연결한다.
- 기본 조회는 5경기로 제한하며 `--limit`으로 명시적으로 늘릴 수 있다.

## 실행

```powershell
python -m app.cli collect-schedule
python -m app.cli collect-game-player-stats
```

## 실제 검증

별도 SQLite DB에서 공식 일정과 완료 경기기록 2건을 렌더링했다.

- 선수 박스스코어 43행 저장
- 일정 미연결 0건
- 단위 테스트 26건 통과, Ruff 검사 통과

## 다음 단계

- 선수별 최근 5경기 평균과 출전 경기 수를 계산해 StatsKing 시즌 평균 추천을 보정한다.
- 팀별 최근 경기 스틸·블록·턴오버·파울·2점슛 성공을 집계해 Daily Picks 질문별 추천 근거를 만든다.
