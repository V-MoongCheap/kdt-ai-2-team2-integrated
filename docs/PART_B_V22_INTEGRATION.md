# Part B의 A V2.2 연계

B는 기존 자연어 규칙과 B 기본 별칭을 항상 사용해 DB의 `extra_requirement`를 직접 해석한다.
A 승인 별칭이 제공되면 함께 활용하고, 같은 카테고리·표현의 연결이 겹칠 때 A를 우선한다.
기존 `label`은 카테고리별 코드 연결 상태를 점검하는 데 사용한다. 라벨 생성·DB 저장은
B가 수행하지 않으며, 라벨의 유무나 진단 결과는 후보 선정·점수·Backend 전송 내용을 바꾸지 않는다.

## 실행에 사용하는 파일

| 설정 | 기준 |
| --- | --- |
| `DEMAND_TAXONOMY_PATH` | A `config/facet_taxonomy_v2_2.json`; 배포 시 profile과 같은 release에 포함 |
| `MFDS_CATALOG_PROFILES_PATH` | `taxonomy_version=v2.2`인 B 상품 profile |
| `DEMAND_CONSTRAINT_ALIASES_PATH` | 선택 A `config/model1_aliases_reviewed_v2.json`; 미설정·파일 없음이면 B만 사용 |
| `DEMAND_CONSTRAINT_COMPAT_ALIASES_PATH` | 필수 B 기본 별칭 `config/demand_constraint_aliases.json`; 항상 읽음 |
| `DEMAND_CONSTRAINT_RULES_PATH` | 기존 `config/demand_constraint_rules.json` |

실행 전에 profile·taxonomy의 버전을 대조하고, A 별칭이 있으면 그 선언 버전과 카테고리·facet·코드·값까지 검증한다.
제공된 A 파일이 잘못됐으면 DB 연결 전에 중단한다. A 파일이 없다는 이유만으로는 중단하지 않는다.
환경 예시, Docker 이미지, Kubernetes ConfigMap은 동일한 A/호환 별칭 조합을 사용한다.
배포 profile·taxonomy 파일은 읽기 전용으로 함께 마운트한다.

## 기존 표현을 유지하는 방식

A 승인 파일에는 현재 제형 별칭이 포함되어 있다. 기존 B 별칭을 완전히 교체하면
“하루 한 번”, “프로바이오틱스와 아연” 등의 조건이 누락될 수 있다.
B는 기존 파일을 필수 기본 입력으로 계속 읽되 다음 규칙을 따른다. 환경 변수의 `COMPAT` 명칭은 기존 설정과의 호환을 위해 유지한다.

- 카테고리 안에 실제 존재하는 canonical value에만 기존 별칭을 연결한다.
- 같은 카테고리·표현에 A 승인 연결이 있으면 A를 우선한다. A에 없는 표현·카테고리는 B를 유지한다.
- A 파일이 미설정이거나 실제로 없으면 B만 사용한다. A 파일에서 별칭이 삭제되거나 승인 목록이 비어 있어도 B에 있으면 계속 사용한다. 삭제를 전역 사용 금지로 해석하지 않는다.
- 제공된 A 파일의 JSON·버전·대상 코드/값이 틀리거나 하나의 표현을 여러 대상으로 연결하면 중단한다. 권한 오류·디렉터리 경로도 누락으로 취급하지 않는다.
- B 파일은 필수다. B 파일이 없을 때 A만 사용하는 운영 설정은 허용하지 않는다. 평가 도구의 A-only 비교만 별도로 허용한다.
- A 파일과 공유 파서 구현은 수정하지 않는다. 검증한 A 연결과 B 기본 별칭은 메모리상의 taxonomy 사본에만 합친다.
- 기존 B 별칭의 `EXPERIMENTAL_DEVELOPMENT` 상태를 유지한다. 이를 A가 승인했다고 표시하지 않는다.

B 기본 별칭의 출처는 기존 실험 저장소 `kdt-ai-applicable-test`의
`config/manually_adjudicated_facet_aliases_v0_5.json`이다. 현재 B 파일과 10개 규칙의
내용 및 버전 `facet-alias-spike-v0.5-v026-reviewed-coverage`가 동일함을 확인했다.
모델 후보 탐색·평가 문장 생성 후 Codex 의미 검수와 반복 평가를 통해 섭취 횟수,
“정제 → 정”, 복합 성분 표현 등을 보완했다. v0.27 기록에는 “루테인 → 루테인 제품”
공백을 추가 보완한 내역도 있다. A 승인 별칭을 복제한 파일이 아니며,
별칭 파일의 버전 표기와 자연어 입력 정책 v0.46은 별도로 관리한다.

`partAIntegration` 출력에 두 별칭 버전·상태·SHA-256, taxonomy 버전·해시, profile 건수가 남는다.
이렇게 같은 V2.2라도 어떤 별칭 조합으로 실행했는지 확인할 수 있다.
`aliasMode=A_AND_B/B_ONLY`, `primaryAliasLoadStatus=LOADED/NOT_CONFIGURED/FILE_MISSING`,
`primaryBindingCount`, `compatibilitySuppressedByA`도 기록한다. 해시는 추적 정보이며
승인되지 않은 변경을 런타임에서 자동 차단하는 고정 해시 목록은 아니다.

운영에서 A를 사용하지 않으려면 `DEMAND_CONSTRAINT_ALIASES_PATH`를 빈 값으로 둔다.
B 경로는 계속 설정해야 한다. 파일이 존재하지만 내용이 잘못된 A를 무시하려면 자동 fallback에
기대지 않고 잘못된 파일을 수정하거나 A 미사용 설정을 명시한다.

## 별칭 변경 회귀 검사

일반 pytest 실행에 `test_alias_fallback.py`가 포함된다. 외부 모델·DB·Backend 없이 실행한다.

```bash
pytest -c packaging/demand-clustering/pyproject.toml \
  tests/demand_clustering/test_alias_fallback.py \
  tests/demand_clustering/test_part_a_integration.py \
  tests/demand_clustering/test_runtime_job.py
```

- A의 현재 94개 category/surface 연결을 고정 CSV의 코드 정답과 실제 파서 결과로 비교한다.
- A 표현 추가·삭제·적용 카테고리 변경도 고정 사례와 대조하여 테스트에서 알린다. 의도한 변경은 검수 후 fixture를 명시적으로 갱신한다.
- A+B와 B-only 양쪽에서 기존 129건 검수셋의 127건 정답 및 자동 오판 0건을 유지하는지 확인한다.
- A 부재·일부 삭제·카테고리 미포함, B 표현 보존, A 우선권, 잘못된 대상 연결, DB 접근 전 차단을 검증한다.

이 저장소에는 실제 CI 실행 설정이 없으며 CI/CD 인계서의 pytest 명령에 포함한다.
인프라의 배포 파이프라인에서도 이 테스트 통과를 요구해야 한다. 고정 사례는 현재 연결의
회귀를 검사하며 새로운 모든 자연어 표현의 정확도를 보장하지 않는다.

## label 활용 범위

최초 DB 조회 결과의 `label`을 원상품 profile의 category로 해석하고 다음을 집계한다.

| 진단 | 의미 |
| --- | --- |
| `MISSING` | label 미생성 또는 비어 있음 |
| `VALID_CATEGORY_LOCAL` | facet 순서·개수와 각 category-local value code가 현재 분류표에 존재 |
| `INVALID_FORMAT` | 숫자 코드 연결 형식 또는 facet 개수가 맞지 않음 |
| `UNKNOWN_VALUE_CODE` | 현재 카테고리에 없는 value code가 포함됨 |
| `CATEGORY_UNAVAILABLE` | 진단할 카테고리를 확인하지 못함 |

라벨은 MUST/EXCLUDE의 구분, PREFER/ANY_OF의 전체 의미를 보존하지 못한다. 따라서 이 진단은
연계 형식 확인이며 A와 B의 의미 해석 일치율이 아니다. DB에는 라벨 생성 시 사용한 taxonomy
버전이 없으므로 `labelSourceVersion=NOT_RECORDED_IN_DEMAND`라고 명시한다.
실제 조건 해석·후보 필터·점수는 기존 B 경로를 계속 사용한다. 집계는 배치 결과 JSON의
`partAIntegration.labelDiagnostics`에 나오며 새 DB 컬럼이나 Backend API 필드를 요구하지 않는다.

## 기존 profile을 V2.2 release로 준비

저장소 루트에서 실행한다. 원본 파일과 출력 디렉터리는 실제 로컬 경로를 지정한다.

```bash
PYTHONPATH=src python scripts/evaluation/prepare_b_profile_release.py \
  --profiles <기존_catalog_profiles.csv> \
  --source-taxonomy <기존_taxonomy_candidate_v2_1.json> \
  --taxonomy config/facet_taxonomy_v2_2.json \
  --output-dir data/processed/b_v22_release
```

카테고리, facet 이름·순서, value 코드·문자열이 모두 같을 때만 전환한다. 전환 전후의
runtime facet 매핑과 상품 비교용 원문도 동일해야 한다. 차이가 있으면 변환을 거절하며
MFDS 원본 근거에서 다시 생성해야 한다. 출력은 `catalog_profiles.csv`, `taxonomy.json`,
해시와 검증 결과를 담은 `manifest.json`이다. 기존 파일·상품 ID·상품 근거를 보존한다.
이 절차는 기존 ID가 실제 Backend `product_catalog.id`와 일치하는지까지 증명하지 않는다.

새 MFDS profile을 생성하는 `build_catalog_wide_mfds_profiles.py`도 이제 `--taxonomy`에서
버전을 읽고 같은 taxonomy 파일을 release에 저장한다. `--taxonomy-version`을 추가한다면
해당 파일의 선언 버전과 일치해야 한다.

## 해석 결과 비교

```bash
PYTHONPATH=src python scripts/evaluation/compare_b_v22_interpretations.py \
  --input tests/demand_clustering/fixtures/v22_alias_migration.csv \
          tests/demand_constraints/fixtures/v042_approved_eval.csv \
  --baseline-taxonomy <기존_taxonomy_candidate_v2_1.json> \
  --output data/reports/b_v22_integration/interpretation_comparison.json
```

기존 B, A 별칭만 적용, A+B 호환 설정의 세 결과를 함께 기록한다. 각 결과에는 상태,
처리 모드, 조건 유형·facet·code, ANY_OF 그룹이 포함된다. 조건 누락과 결과 변경을 별도로
집계한다. 이 비교는 해석 변화 검사이며 DB·Backend·E5를 포함한 전체 통합 성능 평가는 아니다.

## 2026-09-10 개인 브랜치 검증

- 기준 develop: `ecb384a` (PR #16 포함).
- 기존 검수 fixture 129건 + 전환 사례 15건, 총 144건 비교.
- A 별칭만 교체하면 기존 조건이 누락되는 입력 6건.
- A+B 호환 설정 적용 후 기존 조건 누락 0건. 변경 2건은 “가루”와 “알약”이 A 승인 값으로 구조화되는 개선이다.
- 로컬 실험 profile 45,996건을 V2.2 release로 준비했고 runtime facet 매핑·상품 비교 원문 변경은 0건.
- label의 없음·정상·알 수 없는 코드·잘못된 형식을 바꿔 넣어도 동일한 Backend 요청이 생성되는 모의 배치 테스트를 포함한다.
- B·A·공통 및 배포 매니페스트 테스트 449건 통과. 이후 추가한 profile 생성기 검증을 포함한 해당 파일의 3건도 통과했다. C/API 테스트는 이번 변경 범위에서 재실행하지 않았다.
- 변경된 Python 파일의 Ruff 검사와 `git diff --check` 통과.
- Docker 이미지 빌드, non-root/read-only/network-none 환경에서 CLI 및 승인·호환 별칭 해석 확인.
- 실제 Backend 전송·운영 DB 조회·E5 추론·클러스터 배포는 이번 검증에 포함하지 않았다.

원본 대량 profile과 실행 결과는 `data/processed/` 또는 `data/reports/`에 보관하며 Git에 포함하지 않는다.

추가로 v0.46 당시 검수셋 129건과 합성 수요 원본 5,000건을 같은 환경에서 다시 평가했다.
이번 호환 설정은 검수셋 127/129, 자동 PARSED 79/79를 유지했고, 5,000건 모두 당시
저장 결과와 비교 대상 의미가 같았다. 데이터의 한계와 재현 명령은
[자연어 해석 재평가](PART_B_V22_PARSER_REGRESSION.md)에 기록했다.

## B 기본 유지 및 A 선택 적용 보완 검증

- C/API를 제외한 전체 테스트 576건 통과.
- A 승인 연결 94건과 추가·삭제 검출, A+B/B-only 각각 기존 검수 129건 검사 포함.
- 144건 전환 비교를 다시 실행하여 A+B의 기존 조건 누락 0건, 기존과 달라진 2건을 유지.
- Docker 이미지 재빌드 성공. non-root/read-only/network-none 환경에서 A+B, A 미설정,
  A 파일 없음 모두 B 섭취 횟수 조건이 유지되고 잘못된 A 코드가 거절됨을 확인.
- 변경한 Python 파일 Ruff 및 `git diff --check` 통과.
- 이번 fallback 보완 후 대량 5,000건 평가는 재실행하지 않았다. 위의 5,000건 수치는
  이전 구현 `8a223ab`의 결과이며 이번 변경 검증과 구분한다.
- 실제 DB/Backend 호출, E5 추론, 운영 배포는 수행하지 않았다.
