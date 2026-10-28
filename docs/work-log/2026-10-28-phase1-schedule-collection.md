# Phase 1 — 공식 경기 일정·기록 수집 구현

- 완료일: 2026-10-28 (Asia/Seoul)
- 목표: 확인된 KBL 공식 인터페이스로 일정, 팀 기록, 선수 기록을 누적 저장한다.

## 조사 결과

KBL 공식 웹 번들 및 실제 API 응답으로 다음 경로를 확인했다.

- 일정: `GET https://api.kbl.or.kr/match/list`
- 경기 상세: `GET /match/{gmkey}`
- 팀 기록: `GET /match/{gmkey}/team-record`
- 선수 기록: `GET /match/{gmkey}/player-stat`

필수 공개 요청 헤더와 일정의 실제 입력·출력 필드는 [KBL 공식 데이터 수집 계약](../kbl-official-api.md)에 기록했다.

## 구현 내용

- `KBLApiClient`에 확인된 API와 웹앱 헤더만 구현
- `collect-games --from-date YYYYMMDD --to-date YYYYMMDD` CLI 추가
- `collect-stats [--limit N]` CLI 추가
- `gmkey`와 시즌을 기준으로 경기 중복을 방지하고, 재수집 시 점수·상태·통계를 갱신
- 팀 코드·선수 코드의 안정적 ID 저장
- 응답 원문·해시·수집 로그 저장
- 로컬 검증 DB 파일 전체를 Git에서 제외하도록 `.gitignore` 보완

## 실제 수집 검증

분리 SQLite DB(`phase1_check.db`)에서 다음을 수행했다.

```powershell
$env:DATABASE_URL='sqlite:///./phase1_check.db'
python -m app.cli init-db
python -m app.cli collect-games --from-date 20261001 --to-date 20261031
python -m app.cli collect-stats --limit 1
```

결과:

- 일정 49건
- 팀 12건
- 종료 경기 1건의 팀 기록 2건
- 같은 경기의 선수 기록 24건
- 공식 원문 4건

## 자동 검증

- `python -m pytest -p no:cacheprovider -q`: 3개 테스트 통과
- `python -m ruff check app tests migrations`: 통과

## 남은 작업

- 전체 과거 시즌 범위를 선택하는 공식 방식 조사 및 수집 편의 명령 추가
- 실패한 개별 경기 수집을 격리하고 재시도하는 배치 실행 정책 추가
- 쿼터별 점수용 정규화 테이블 필요성 검토
- StatsKing·Daily Picks 실제 문제 수집으로 Phase 2 진행
