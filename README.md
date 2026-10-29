# KBL Predictor

KBL 공식 경기 기록을 누적하고, StatsKing·Daily Picks·Weekly 6 문제에 대해 **검증 가능한 데이터만** 바탕으로 추천하기 위한 Python 프로젝트입니다. 자동 제출과 알림 발송은 범위에 포함하지 않습니다.

## 현재 구현 범위 (Phase 1 기반 + Weekly 6 확장)

- PostgreSQL/SQLAlchemy/Alembic용 기본 스키마: 시즌, 팀, 선수, 경기, 팀·선수 경기기록, 챌린지 및 수집 이력
- 세 게임 유형(`stats_king`, `daily_picks`, `weekly6`)을 하나의 챌린지 스키마에서 지원
- Weekly 6의 주차와 후보 경기를 별도 `weekly6_rounds`, `weekly6_fixtures`로 모델링
- 공식 페이지를 요청 간격을 두고 취득하고 응답 해시·수집 이력을 남기는 보수적 수집기
- 데이터가 불충분하거나 확률 보정이 끝나지 않으면 추천·확률을 숨기는 Weekly 6 기준선
- `predict-weekly6`, `predict-all` CLI 골격 및 단위 테스트

## 공식 페이지 확인 기록 — 2026-10-28 (Asia/Seoul)

브라우저에서 `https://www.kbl.or.kr/game/challenge/weekly6`를 확인했다.

- 화면에는 주차 범위, 마감 카운트다운, 후보 경기의 날짜·시간·장소·두 팀이 보인다.
- 확인 시점의 화면은 후보가 11개이고 “응모를 위한 6 경기 중 0 경기 선택”이라고 표시했다. 즉, 이 게임은 ‘6경기 전체의 승패’가 아니라 **후보 경기 중 6경기를 선택**하는 구조로 보인다.
- “정답자에게는 10만 포인트…복수 정답자는 균등 분배” 안내는 확인했지만, 전체 정답 조건·과거 결과 공개 구조·문제 고유 ID·선택지 전달 형식은 아직 공식 응답으로 검증하지 못했다.
- 따라서 현재 코드에는 미확인 내부 API나 선택지/채점 규칙을 하드코딩하지 않았다.

## 실행

```powershell
Copy-Item .env.example .env
docker compose up -d
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e ".[dev]"
alembic upgrade head
python -m app.cli status
python -m app.cli collect-weekly6
python -m app.cli predict-weekly6
python -m app.cli predict-weekly6 --week 2026-W44
python -m app.cli predict-all
pytest
```

`collect-weekly6`는 공식 HTML 원문과 수집 로그에 출처·시간·해시를 남긴다. 아직 안정적인 필드 추출 계약이 검증되지 않았으므로, 응답에서 문제·결과를 추측해 저장하지 않는다.

## 월요일 실행 설계

월요일 Asia/Seoul 시간대에 `collect-weekly6`를 먼저 한 번 실행한다. 문제 미등록일 때는 30~60분 이상의 간격으로 제한 재시도를 권장한다. 등록 확인 뒤에는 마감 전 한 번 더 실행해 기록·출전 정보 변경을 반영한다. 스케줄러(Cron, Windows 작업 스케줄러)는 운영 환경에서 실행 주체에 맞춰 설정하며, 이번 범위에서는 알림이나 게임 제출을 수행하지 않는다.

## 화면 기반 기록 수집

내부 API를 직접 호출하지 않는다. 브라우저가 공식 기록 페이지를 렌더링한 뒤, 화면상 표시되는 텍스트만 읽는다. 현재는 시즌 리더 화면의 선수 순위·지표와 일정·결과 화면의 경기 카드를 수집한다.

```powershell
python -m app.cli collect-season-leaders
python -m app.cli collect-schedule
python -m app.cli collect-season-schedule --season 2026-2027
python -m app.cli collect-team-rankings
python -m app.cli compute-team-form --season 2026-2027 --as-of 2026-10-29T19:00+09:00
python -m app.cli collect-daily-picks
```

이 기능은 로컬 Chrome과 Playwright 패키지가 필요하다. 로그인·CAPTCHA·제출 동작은 수행하지 않으며, 표시되지 않은 정보는 추측해 저장하지 않는다.

`collect-schedule`은 [일정 및 결과](https://www.kbl.or.kr/match/schedule) 화면의 월별 경기 카드에서 날짜·시각·장소·두 팀의 표시 순서·점수·완료 여부만 수집한다. 화면에 홈/원정 라벨이 없으므로 팀 표시 순서를 홈/원정으로 추정하지 않는다. 미래 경기에 표시되는 `0-0`은 점수가 아니라 미확정 일정으로 저장한다.

`collect-season-schedule --season 2026-2027`은 같은 화면의 월 이동 버튼으로 10월부터 다음 해 5월까지를 차례로 렌더링한다. 경기 카드가 없는 월도 화면 원문과 수집 이력은 남기며, 표시되지 않은 과거·미래 경기를 만들지 않는다.

`collect-team-rankings`은 [팀 순위](https://www.kbl.or.kr/match/team-ranking) 화면에 표시되는 시즌 승·패·승률, 최근 5경기, 연속, 홈·원정 성적, 다음 상대와 상대전적을 수집한다. 이 값은 화면 관측 시점의 스냅샷이며, 득실점·리바운드·턴오버·공격/수비 효율처럼 현재 표에 없는 값은 저장하지 않는다.

`collect-weekly6`은 Weekly 6 본문에 표시된 Pick 번호, 날짜·시각, 장소, 두 팀의 표기 순서와 공식 선택 수를 저장한다. 홈/원정 라벨이 화면에 없으므로 팀 순서를 홈/원정으로 해석하지 않는다. 본문이 보이지 않을 때는 문제 미등록으로 단정하지 않고 원문·수집 이력에 `본문 미표시`로 남기며, 문제·예측·가상 결과를 저장하지 않는다.

`compute-team-form`은 수집된 완료 경기만 사용해 시즌 승패, 최근 5/10경기 승패, 평균 득점·실점, 휴식일을 계산한다. `--as-of`와 같거나 이후에 시작한 경기는 계산에서 제외하므로 미래 결과가 섞이지 않는다. 일정 카드에 홈/원정 라벨이 없어 홈/원정 파생 지표는 계산하지 않는다.

`collect-daily-picks`은 [Daily Picks](https://www.kbl.or.kr/game/challenge/daily-picks) 화면의 날짜·시각·장소·질문·선택지를 저장한다. 화면에 절대 마감 시각이나 공식 문제 ID가 표시되지 않으면 저장하지 않는다.

## 확률과 백테스트 원칙

승률·최근 폼·홈/원정·효율·휴식·상대전적은 모두 예측 시각 이전의 공식 경기 기록으로 계산해야 한다. 현재 기준선은 확률 보정 전의 순위 모델이므로 승리 확률과 6개 선택의 전체 적중 확률을 표시하지 않는다. 향후 과거 Weekly 6 문제와 공식 정답을 확보하면, 시점 고정 백테스트 및 확률 보정 후에만 이를 노출한다. 경기 간 독립성 곱셈은 근사치일 뿐이며, 공통 부상·일정·순위 경쟁 영향을 반영하지 못한다.
