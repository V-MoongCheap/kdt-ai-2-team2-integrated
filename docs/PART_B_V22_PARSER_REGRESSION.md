# Part B V2.2 전환과 v0.46 자연어 해석 재평가

## 평가 범위

현재 `config/demand_constraint_rules.json`은 `demand-requirement-policy-v0.46`이며,
문장 해석 핵심은 v0.42, 서비스 입력 정책은 v0.46이다. KiwiPiePy 0.23.2를 사용한다.
이번 실행은 기존 모델 생성·검수 데이터를 재사용하며 외부 LLM 호출은 없다.

과거 frontier model API는 후보 규칙 탐색과 다양한 평가 문장 생성에 활용했다.
실제 수요별 해석은 Kiwi와 고정 규칙으로 수행한다. 따라서 이번 비교에서는 규칙을
다시 생성하지 않고 taxonomy와 별칭 연결 변경이 기존 해석 결과에 미치는 영향을 본다.

비교 설정은 다음 세 가지다.

- `before`: 기존 V2.1 taxonomy + 기존 B 별칭.
- `aOnly`: A V2.2 taxonomy + A 승인 별칭.
- `after`: A V2.2 taxonomy + A 승인 별칭 + 이번 B 호환 별칭 설정.

V2.1과 V2.2의 16개 category, 48개 facet, 413개 value에 대해 category-local 코드,
facet 순서, 값 문자열이 동일함을 확인했다. 버전 이름이 바뀌었지만 이 두 파일의
분류 기준이 달라진 것은 아니다. 별칭 연결 범위는 달라지므로 별도로 평가한다.

## 평가셋과 채점

기존 검수 129건은 세 모델이 생성한 144건을 Codex가 사전 의미 검수하여 확정한
개발 평가셋이다. 사람이 만든 실제 사용자 정답셋이 아니며 정규화 고유 문장은
120건이다. 과거에는 코드 동결 후 독립 평가에 사용했지만, 이번 재사용 결과는
회귀 평가로 해석한다.

129건에는 기대 상태와 facet/value code, MUST/EXCLUDE/PREFER 정답이 있다.
`parse()`의 문장 해석과 `interpret()`의 서비스 정책을 각각 채점한다. 자동 PARSED
오판 수를 따로 기록하여 정확한 조건을 생성하지 못한 REVIEW와 구분한다.

합성 수요 5,000건은 v0.46 당시 입력 원본의 SHA-256과 동일한 파일을 사용한다.
입력 해시는 `51d5df1143bad1907222abe951e2075a299c632e5ff74128bd2766679a09818c`다.
대체품 동의가 있고 요구사항이 비어 있지 않은 입력은 3,046건이다.
상태, 처리 모드, 조건 유형·facet·code, ANY_OF 그룹과 MAX 집계, 자유 텍스트,
동등 taxonomy code 정보를 비교한다. 당시 저장된 v0.46 결과 CSV와도 대조한다.

5,000건의 구조화 비율은 정확도가 아니다. 이 개발셋을 보며 과거 규칙을 보완했으며,
동의한 입력에는 신규 별칭인 “가루”, “알약”, “하루 한 번”이 없다. 신규 별칭 적용은
별도의 전환 사례 15건으로 점검하고, 미관측 자연어 정확도는 새로운 독립 평가로
확인해야 한다.

## 2026-09-10 실행 결과

평가 대상은 개인 브랜치의 B V2.2 연계 구현 `8a223ab`이다.

| 항목 | 기존 B | A 별칭만 | A+B 호환 설정 |
| --- | ---: | ---: | ---: |
| 기존 검수셋 정답 | 127/129 | 127/129 | 127/129 |
| 자동 PARSED 중 정답 | 79/79 | 79/79 | 79/79 |
| 자동 PARSED 오판 | 0 | 0 | 0 |
| 기대 REVIEW를 REVIEW로 처리 | 48/48 | 48/48 | 48/48 |
| 5,000건 중 PARSED | 2,519 | 2,519 | 2,519 |
| PASSTHROUGH | 266 | 266 | 266 |
| CONFLICT | 261 | 261 | 261 |
| NONE / NOT_APPLICABLE | 275 / 1,679 | 275 / 1,679 | 275 / 1,679 |
| 당시 v0.46 결과 CSV와 의미가 다른 입력 | 0 | 0 | 0 |
| 기존 조건이 누락된 입력 | 0 | 0 | 0 |

129건 결과는 `parse()`와 `interpret()` 양쪽에서 동일하다. 전체 정답률은
98.45%이며 기존 두 실패 `openai-NP-046-1`, `openai-NP-048-1`도 그대로다.
“액상은 절대 포함 금지라고 하고, 1일 1회는 반드시 선택해 주세요.” 같은 문장을
인용·전언으로 보아 자동 확정하지 못하고 REVIEW로 넘기는 기존 한계다.

5,000건에서 대체품 동의 및 비어 있지 않은 요구사항 3,046건 중 2,519건을 구조화하므로
구조화 비율은 82.70%다. 정확도 정답이 없는 이 입력에서 82.70%를 정확도라고 쓰지 않는다.
상태별 집계뿐 아니라 비교 대상 필드의 행별 의미도 전부 기존 결과와 같았다.

기존 [전환 사례 비교](PART_B_V22_INTEGRATION.md#해석-결과-비교)는 다른 점을 드러낸다.
129건에 별도 전환 사례 15건을 더한 144건에서는 A 별칭만 적용하면 기존 조건이
누락되는 입력이 6건이었다. 예를 들어 “하루 한 번 먹는 제품이면 좋겠어요.”는
섭취 횟수 PREFER 조건을 잃고 PASSTHROUGH가 된다. “프로바이오틱스와 아연”도
복합 성분 대신 일부 성분만 남는다.

이번 A+B 호환 설정에서는 그 6건을 모두 유지했고, “가루면 좋겠어요.”와
“알약 제품이면 좋겠어요.”는 각각 A의 분말·캡슐 연결에 따라 구조화됐다.
즉, 기존 회귀 성능은 유지되었지만 별칭 파일을 단순 교체해도 안전하다는 결과는 아니다.
신규 별칭을 포함한 부정·인용·비교·복합 조건의 일반화 성능까지 입증한 것도 아니다.

## 재현 방법

저장소 루트에서 기존 실험 파일 경로를 지정한다. 별도의 모델 API 키가 필요하지 않다.

```bash
PYTHONPATH=src python scripts/evaluation/evaluate_b_v22_parser_regression.py \
  --baseline-taxonomy <기존_taxonomy_candidate_v2_1.json> \
  --service-input <part_c_clustering_input_grounded_5000_v1.csv> \
  --archived-service-output <v046_service_aligned_part_c_input_5000_candidate.csv> \
  --output data/reports/b_v22_integration/parser_regression_v046.json
```

기존 실험 폴더가 이 저장소와 나란히 있다면 입력 원본은
`../kdt-ai-applicable-test/archive/purchase-request-generation/`, 당시 결과 CSV는
`../kdt-ai-applicable-test/artifacts/`, 이전 taxonomy는
`../kdt-ai-applicable-test/data/part_a_original/`에 있다.

결과 JSON에는 입력·설정 해시, Kiwi/규칙 버전, 설정별 지표, 검수셋 실패 내역,
서비스 입력별 변경 사례가 저장된다. 대량 결과와 기존 외부 실험 파일은 Git에 포함하지 않는다.
실행 시간·처리량, E5 검색 품질, 실제 DB/Backend 연결은 이 정확도 회귀 평가 범위에 포함하지 않는다.
