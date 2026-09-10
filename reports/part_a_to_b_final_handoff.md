# Part A -> Part B 최종 Contract Handoff

## 실제 B Parser 경로

- Parser 생성: `src/moongcheap_ai/demand_clustering/runtime_job.py:328`
- 실제 해석: `src/moongcheap_ai/demand_clustering/substitute_proposal_planner.py:266`
- 공통 타입 정의: `src/moongcheap_ai/demand_constraints/input_policy.py`의 `DemandRequirementResult`

B는 현재 `demand.extra_requirement` 원문을 `DemandConstraintParser.interpret()`에 넣어 결과를 만든다. 이번 작업에서는 B 코드를 수정하지 않는다.

## 공통 Output Contract

Part A도 다음 필드와 내부 타입을 사용한다.

```text
status
constraints
warnings
clauses
interpretation_method
preference_groups
semantic_preferences
diagnostic_code
taxonomy_equivalences
effective_requirement_mode
```

`constraints`의 각 항목은 `facet_name`, `value_code`, `value`, `constraint_type`, `evidence_clause`를 사용한다. `value_code`는 Category-local V2.2 code다. `preference_groups`는 B가 사용하는 `ANY_OF` 구조를 그대로 보존한다.

Part A의 CSV는 B baseline 호환을 위해 `label`과 원본 ID도 유지하지만, 요구사항 해석의 기준은 위 `DemandRequirementResult` 구조다. 별도의 camelCase 조건 DTO는 만들지 않는다.

## 상태와 실행 모드

| 상태 | 실행 모드 |
| --- | --- |
| `PARSED` | `STRUCTURED` |
| `PASSTHROUGH` | `SEMANTIC_TEXT` |
| `NONE`, `CONFLICT`, `TAXONOMY_AMBIGUOUS`, `REVIEW`, `NOT_APPLICABLE` | `NONE` |

A는 E5를 실행하지 않는다. `PASSTHROUGH` 결과의 `semantic_preferences`만 제공하고 E5 ranking은 B 책임이다.

## Serialization

`DemandRequirementResult.to_dict()`와 `DemandRequirementResult.from_dict()`를 사용한다.

검증 범위:

- status
- constraints
- preference_groups
- semantic_preferences
- diagnostic_code
- effective_requirement_mode

Fixture: `tests/fixtures/part_a_to_b/demand_requirement_results.json` (20건)

## 결과 전달 방식

현재 Backend ERD에는 A 결과를 저장·전달하기 위한 별도 JSON/TEXT 컬럼이나 processed result table이 확인되지 않았다. `demand.label`과 `demand.processed_at` 직접 저장 준비는 되어 있지만, 구조화된 `DemandRequirementResult`를 B가 읽는 운영 경로는 Backend와 합의되지 않았다.

```text
PART_A_OUTPUT_TRANSPORT = NOT_YET_DEFINED
PART_A_OUTPUT_CONSUMED_BY_B = NOT_YET
```

임의 migration은 만들지 않는다.

## B Parser bypass 제안

장기적으로 `substitute_proposal_planner.py:266`의 원문 Parser 호출 지점에서 다음 우선순위를 적용한다.

```python
if precomputed_requirement is not None:
    requirement = precomputed_requirement
else:
    requirement = self._requirement_parser.interpret(...)
```

A 결과가 없는 legacy/local 실행은 기존 Parser를 fallback으로 유지할 수 있다. 이 변경은 B 팀의 후속 작업이며 이번 커밋에서는 수행하지 않았다.

## 현재 판정

- `PART_A_OUTPUT_CONTRACT = READY`
- `PART_A_OUTPUT_CONSUMED_BY_B = NOT_YET`
- Local pipeline execution: PASS
- B/C 알고리즘 수정: 없음

