# 완료 경기 쿼터 점수 수집

- 완료일: 2026-10-29 (Asia/Seoul)
- 목표: 공개 경기 상세의 팀별 쿼터 점수를 수집해 Daily Picks 쿼터 기록 예측의 기반을 만든다.

## 변경

- `visible_game_quarter_scores` 테이블과 Alembic `0011` migration을 추가했다.
- `collect-game-quarters` CLI를 추가했다.
- 현재 일정 화면의 완료 경기 `기록` 버튼을 브라우저에서 순차적으로 열어, 경기요약의 1~4쿼터·연장전·합계 점수를 저장한다.
- 상세 기록의 전체 팀명과 일정 카드의 짧은 팀명은 같은 날짜 안에서만 공백 제거·포함 비교로 연결한다. 후보가 정확히 하나일 때만 저장한다.
- 기본 수집량은 `--limit 5`로 제한해 과도한 요청을 피한다.

## 실행

```powershell
python -m app.cli collect-schedule
python -m app.cli collect-game-quarters
```

필요한 경우에만 수집량을 명시적으로 늘린다.

```powershell
python -m app.cli collect-game-quarters --limit 20
```

## 실제 검증

별도 SQLite DB에서 공식 일정 화면과 완료 경기 상세 2건을 다시 렌더링했다.

- 완료 경기 상세 2건 확인
- 팀별 쿼터 점수 2건 저장
- 일정 미연결 0건
- 단위 테스트 24건 통과, Ruff 검사 통과

## 다음 단계

- 저장된 쿼터 점수로 Daily Picks의 쿼터 득점 질문에 대한 팀별 최근 추세를 계산한다.
- 같은 공개 경기 상세의 `경기기록` 탭에서 선수 박스스코어를 수집해 StatsKing 최근 5경기 추천에 반영한다.
