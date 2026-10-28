# KBL 공식 데이터 수집 계약

이 문서는 2026-10-28 Asia/Seoul 기준으로 KBL 공식 웹 애플리케이션이 배포한 공개 번들과 실제 응답을 대조해 확인한 내용이다. 미확인 API는 사용하지 않는다.

## 공통 요청

- API 기준 주소: `https://api.kbl.or.kr`
- 공식 웹앱과 동일하게 필요한 공개 헤더: `Channel: WEB`, `TeamCode: XX`, `X-Requested-With: XMLHttpRequest`, `lang: ko`
- 요청 간격은 `.env`의 `KBL_REQUEST_DELAY_SECONDS`(기본 1.5초)로 제한한다.

## 확인된 엔드포인트

| 용도 | 메서드·경로 | 확인된 입력 | 주요 확인 필드 |
| --- | --- | --- | --- |
| 일정 | `GET /match/list` | `fromDate`, `toDate` (`YYYYMMDD`), `tcodeList=all` | `gmkey`, `seasonCode`, `gameDate`, `gameStart`, 홈/원정 팀 코드·명, 점수, 경기 상태 |
| 경기 상세 | `GET /match/{gmkey}` | `gmkey` | 경기 메타데이터, 팀 정보, 쿼터별 점수 |
| 팀 기록 | `GET /match/{gmkey}/team-record` | `gmkey` | 득점, 리바운드, 어시스트, 턴오버, 슛·자유투, 효율 지표 |
| 선수 기록 | `GET /match/{gmkey}/player-stat` | `gmkey` | `pcode`, 선수·팀 정보, 출전 시간, 득점, 리바운드, 어시스트 등 |

`gmkey`는 경기별 안정적 공식 식별자로 사용한다. 수집기는 `(season_id, gmkey)` 조합으로 중복을 방지하고, 같은 키의 점수·상태·통계를 반복 수집 시 갱신한다.

## 실행

```powershell
# 일정 수집: 시즌 경계는 임의 가정하지 않고 날짜 범위를 명시한다.
python -m app.cli collect-games --from-date 20261001 --to-date 20261031

# 위 명령으로 저장된 종료 경기의 공식 팀/선수 기록 수집
python -m app.cli collect-stats

# 소규모 검증 시에는 한 경기만 수집
python -m app.cli collect-stats --limit 1
```

각 HTTP 응답은 `raw_source_documents`에 원문과 SHA-256 해시로 보관하고, 모든 호출은 `collection_logs`에 남긴다. API 응답 형식이 달라져 필수 필드가 없으면 해당 수집은 실패하며 임의 데이터를 채우지 않는다.
