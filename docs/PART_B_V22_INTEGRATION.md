# Part B의 A V2.2 연계

B는 A의 승인 분류표와 별칭을 사용해 DB의 `extra_requirement`를 직접 해석한다.
기존 `label`은 카테고리별 코드 연결 상태를 점검하는 데 사용한다. 라벨 생성·DB 저장은
B가 수행하지 않으며, 라벨의 유무나 진단 결과는 후보 선정·점수·Backend 전송 내용을 바꾸지 않는다.

## 실행에 사용하는 파일

| 설정 | 기준 |
| --- | --- |
| `DEMAND_TAXONOMY_PATH` | A `config/facet_taxonomy_v2_2.json`; 배포 시 profile과 같은 release에 포함 |
| `MFDS_CATALOG_PROFILES_PATH` | `taxonomy_version=v2.2`인 B 상품 profile |
| `DEMAND_CONSTRAINT_ALIASES_PATH` | A `config/model1_aliases_reviewed_v2.json` |
| `DEMAND_CONSTRAINT_COMPAT_ALIASES_PATH` | 기존 B `config/demand_constraint_aliases.json`; 선택 호환 설정 |
| `DEMAND_CONSTRAINT_RULES_PATH` | 기존 `config/demand_constraint_rules.json` |

실행 전에 profile·taxonomy·A 별칭의 선언 버전을 대조하고 다르면 DB 연결 전에 중단한다.
환경 예시, Docker 이미지, Kubernetes ConfigMap은 동일한 A/호환 별칭 조합을 사용한다.
배포 profile·taxonomy 파일은 읽기 전용으로 함께 마운트한다.

## 기존 표현을 유지하는 방식

A 승인 파일에는 현재 제형 별칭이 포함되어 있다. 기존 B 별칭을 완전히 교체하면
“하루 한 번”, “프로바이오틱스와 아연” 등의 조건이 누락될 수 있다.
B는 해당 파일을 명시적인 호환 입력으로 함께 읽되 다음 규칙을 따른다.

- 카테고리 안에 실제 존재하는 canonical value에만 기존 별칭을 연결한다.
- 같은 표현이 A 승인 파일에도 있으면 A의 연결을 우선한다.
- A 파일과 공유 파서 구현은 수정하지 않는다. 호환 별칭은 메모리상의 taxonomy 사본에만 추가한다.
- 기존 B 별칭의 `EXPERIMENTAL_DEVELOPMENT` 상태를 유지한다. 이를 A가 승인했다고 표시하지 않는다.
- 향후 A와 공유 승인 범위를 정리하면 호환 파일의 표현을 옮기거나 제거한다.

`partAIntegration` 출력에 두 별칭 버전·상태·SHA-256, taxonomy 버전·해시, profile 건수가 남는다.
이렇게 같은 V2.2라도 어떤 별칭 조합으로 실행했는지 확인할 수 있다.

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
