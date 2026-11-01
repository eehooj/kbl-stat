# Daily Picks 공식 정답 일일 누적

## 목표와 완료 시각

- 목표: 정확도 평가 표본이 자동으로 늘어나도록 일일 갱신 흐름에 과거 Daily Picks 공식 정답 수집을 포함한다.
- 완료: 2026-11-01 (Asia/Seoul)

## 변경 내용

- `refresh-daily`에 `Daily Picks 공식 정답` 단계를 추가했다.
- `--result-days` 옵션으로 매일 다시 확인할 과거 일수를 지정한다.
- 기본값은 최근 4일이며 요청 상한은 7일이다.
- 같은 과거 날짜를 겹쳐 확인해 화면의 일시적 실패나 실행 누락 뒤에도 정답을 보완할 수 있다.
- 기존 문제·정답은 갱신 방식으로 저장하므로 중복 정답 행을 만들지 않는다.

## 실행

```bash
python -m app.cli refresh-daily --attempts 2 --game-limit 5 --result-days 4
```

수집된 공식 정답은 다음 평가에 자동으로 포함된다.

```bash
python -m app.cli backtest-daily-picks
python -m app.cli evaluate-daily-picks-lookbacks
python -m app.cli evaluate-daily-picks-strategies
```

## 정확도 개선 원칙

- 상대 허용 기록 결합 전략은 기존 20건에서 55.0%보다 높은 60.0%였지만 생산 규칙에는 아직 적용하지 않았다.
- 이후 자동 누적되는 신규 정답에서도 개선이 반복되는지 확인한다.
- 기존 표본과 신규 표본을 구분하지 않고 반복 조정해 생기는 과적합을 피한다.

## 외부 데이터 제한

- 공식 KBL Daily Picks 브라우저 화면에서 정답으로 표시된 선택지만 저장한다.
- 정답자 개인정보는 저장하지 않는다.
- 내부 API는 직접 호출하지 않는다.
