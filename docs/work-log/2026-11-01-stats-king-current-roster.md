# StatsKing 현재 로스터 검증

## 목표와 완료 시각

- 목표: StatsKing 후보가 공식 선수기록 화면의 최신 소속만 사용하고, 과거 팀 또는 동명이인의 최근 기록이 섞이지 않도록 한다.
- 완료: 2026-11-01 (Asia/Seoul)

## 변경 기능과 주요 파일

- `app/models.py`, `migrations/versions/0018_player_roster_snapshot.py`
  - 선수 시즌 기록에 전체 공식 선수기록 수집 시점을 나타내는 `roster_snapshot_at`을 추가했다.
- `app/services/player_record_collection.py`
  - 7페이지 전체를 성공적으로 렌더링한 한 번의 수집에 공통 스냅샷 시각을 부여한다.
  - 과거 팀 행은 삭제하지 않고 이전 스냅샷으로 보존한다.
- `app/services/stats_king_recommendation.py`
  - 가장 최근의 완전한 로스터 스냅샷에 포함된 선수만 현재 StatsKing 후보로 사용한다.
  - 완전한 스냅샷이 없으면 오래된 행으로 추천하지 않는다.
  - 최근 폼은 기존과 같이 선수명과 현재 팀명이 모두 일치하는 경기만 사용한다.
- `tests/test_stats_king_recommendation.py`
  - 이전 스냅샷 제외, 동명이인 유지, 스냅샷 미수집 시 추천 보류, 동명이인의 팀별 최근 폼 분리를 검증한다.

## 실행·검증

```bash
python -m alembic upgrade head
# 0018_roster_snapshot
python -m app.cli collect-player-records
# 공식 선수 기록 7페이지, 137건
python -m app.cli collect-stats-king
# 고양소노 vs 수원KT
python -m app.cli predict-stats-king
```

실제 추천 결과:

- 득점: 패리스 배스(수원 KT)
- 리바운드: 트레이 포터(수원 KT)
- 어시스트: 이정현(고양 소노)

최신 공식 스냅샷에는 `이정현`이 고양 소노와 원주 DB에 각각 한 명, `최승욱`이 고양 소노와 대구 한국가스공사에 각각 한 명 표시됐다. 이름만으로 이전 행을 삭제했다면 동명이인을 손상할 수 있으므로 두 선수 모두 최신 스냅샷에 보존했다. 최근 경기 기록도 이름과 팀 조합별로 분리됨을 확인했다.

```bash
python -m pytest -q
# 37 passed
python -m ruff check app tests
# All checks passed!
```

## 외부 데이터와 제한 사항

- 공식 KBL 선수기록과 StatsKing의 브라우저 렌더링 화면만 사용했다. 내부 API는 직접 호출하지 않았다.
- 공식 선수기록 화면의 팀 엠블럼을 현재 화면상 소속으로 사용한다.
- 선수 고유 ID는 화면에 표시되지 않아 저장하지 않는다. 동명이인은 선수명과 팀 조합으로 분리한다.
- 시즌 도중 팀을 옮긴 선수가 새 팀으로 표시되면 새 스냅샷만 현재 후보에 쓰고 이전 팀 행은 과거 근거로 남는다.

## 다른 컴퓨터에서 재현

```bash
source .venv/bin/activate
alembic upgrade head
python -m app.cli collect-player-records
python -m app.cli collect-stats-king
python -m app.cli predict-stats-king
python -m pytest -q
python -m ruff check app tests
```

## 남은 작업과 주의점

- 공식 선수기록 7페이지 중 하나라도 누락되면 완전한 스냅샷으로 저장하지 않도록 페이지 수·행 수 이상 감지를 추가할 수 있다.
- 과거 StatsKing 문제와 공식 정답을 연결해 현재 로스터 필터 적용 전후의 백테스트를 비교한다.
- 공식 화면에 선수 고유 식별자가 표시되면 동명이인 식별 구조를 강화한다.
