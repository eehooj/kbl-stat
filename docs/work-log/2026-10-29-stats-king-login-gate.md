# StatsKing 로그인 선택 화면 처리

- 완료일: 2026-10-29 (Asia/Seoul)
- 목표: StatsKing의 선수 선택 화면이 로그인 뒤에만 보이는 사실을 확인하고, 로그인 정보를 저장하지 않는 수집 경로를 마련한다.

## 확인 결과

비로그인 브라우저에서 공식 StatsKing 카드의 실제 `게임참여` UI를 열었다.

- 화면은 `로그인 후 이용해주세요.` 안내를 표시했다.
- 선수 목록과 득점·리바운드·어시스트 선택 UI는 표시되지 않았다.
- 따라서 비로그인 화면의 부재는 문제 미공개가 아니라 로그인 접근 제한이다.

사용자가 설명한 게임 구조(양 팀 전체 선수 중 득점·리바운드·어시스트 부문 선택)는 로그인된 참여 화면에서 확인·파싱해야 한다.

## 변경

- `collect-stats-king`이 실제 경기 카드의 `게임참여` UI를 읽기 전용으로 연다.
- 비로그인 상태에서는 로그인 필요 여부, 경기 카드, 화면 원문·수집 이력만 저장하고 문제·선택지·예측을 만들지 않는다.
- `KBL_BROWSER_USER_DATA_DIR` 환경 변수를 추가했다. 이 값은 전용 Chrome 프로필 폴더 경로이며 `.env`에만 둔다.
- `open-stats-king-login` CLI를 추가했다. 사용자가 열린 전용 Chrome에서 직접 로그인한 뒤 Enter를 누르면 세션 쿠키는 해당 로컬 프로필에만 보존된다.
- 기본 Chrome 프로필이나 계정 정보는 코드·Git·DB에 저장하지 않는다.

## 사용자 실행 절차

`.env`에 비어 있는 전용 폴더를 지정한다. 기본 Chrome 프로필 폴더는 지정하지 않는다.

```dotenv
KBL_BROWSER_USER_DATA_DIR=C:\\kbl-predictor-browser-profile
```

그 다음 아래를 실행한다.

```powershell
python -m app.cli open-stats-king-login
```

열린 Chrome에서 KBL에 로그인만 하고, 선수 선택·응모·제출은 하지 않는다. 터미널에서 Enter를 누른 다음에는 다음 명령으로 로그인된 참여 화면 원문을 수집한다.

```powershell
python -m app.cli collect-stats-king
```

## 실제 검증

별도 SQLite DB에서 비로그인 참여 화면을 다시 렌더링했다.

- StatsKing 경기 카드 1건 저장
- 로그인 안내가 포함된 원문 스냅샷 1건 저장
- `stats_king` 챌린지 문제 0건 저장
- 단위 테스트 22건 통과, Ruff 검사 통과

## 다음 단계

로그인된 프로필로 수집한 참여 화면에서 실제 선수 목록과 득점·리바운드·어시스트 선택 UI의 렌더링 순서를 확인한다. 그 확인 결과에 맞춰서만 `challenge_questions`와 `challenge_options` 파서를 추가한다.
