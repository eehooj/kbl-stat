# Daily Picks 화면 문제·선택지 수집

- 완료일: 2026-10-29 (Asia/Seoul)
- 목표: 공식 Daily Picks 화면에 표시된 당일 예측 문제와 선택지를 공용 챌린지 구조에 저장한다.

## 확인한 화면

공식 [Daily Picks](https://www.kbl.or.kr/game/challenge/daily-picks) 화면에서 다음 구조를 확인했다.

- 당일 날짜
- `Pick 1`부터 여러 Pick 번호
- 각 Pick의 경기 시각·장소·화면상 주제 라벨
- 질문 문구
- 세 개의 선택지
- 상대적인 마감 카운트다운

화면 안내에는 Daily Picks가 당일 경기의 팀 기록 관련 예측 게임이라고 표시됐다. 확인 시점 화면에는 문제 5개가 표시됐다.

## 변경

- `collect-daily-picks` CLI 추가
- 공용 `challenge_questions`, `challenge_options` 테이블에 `daily_picks` 유형으로 저장
- 질문의 날짜·시각·장소·주제 라벨은 원문 payload에 보관
- 선택지 순서를 보존
- 원문 스냅샷 및 수집 로그 저장

## 의도적으로 저장하지 않은 값

- 화면에 표시되지 않은 공식 문제 고유 ID
- 상대 카운트다운만으로 추정한 절대 마감 시각
- 공식 정답·채점 규칙
- 질문의 선택지 순서만으로 판단한 홈/원정 정보

## 실행

```powershell
alembic upgrade head
python -m app.cli collect-daily-picks
```

## 실제 검증

새 SQLite DB에서 현재 공식 Daily Picks 화면을 렌더링해 확인했다.

- Daily Picks 질문 5건 저장
- 선택지 15건 저장
- 단위 테스트 16건 통과
- Ruff 검사 통과

## 다음 단계

- Daily Picks 문제의 날짜·시각·장소를 수집된 일정 카드와 안전하게 연결
- 질문별 팀 기록 유형을 화면 문구 기준으로 분류
- 공식 정답 공개 방식이 화면에서 확인될 때 결과 수집과 백테스트 구조를 추가
