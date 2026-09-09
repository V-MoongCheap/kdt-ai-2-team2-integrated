# Nutrime Consumer Facet Discovery

실제 Nutrime 건강기능식품 Review에서 기존 Taxonomy로 설명되지 않는 소비자 경험 후보를 탐색한 결과다. 기존 Taxonomy와 Alias 66개는 변경하지 않았다.

## Scope
- analyzed raw reviews: 423
- primary HFF-mapped reviews: 348
- unmapped reference reviews: 75
- Naver Corpus: 후보 발견 후 약한 표현 참고용으로만 검색

## Discovery Type Counts
| type | row count |
|---|---:|
| EXISTING_FACET | 316 |
| NEW_VALUE | 0 |
| NEW_ALIAS | 32 |
| NEW_FACET_CANDIDATE | 29 |
| NON_FACET | 161 |
| SUBJECTIVE_MEDICAL_OUTCOME | 69 |

## New Facet Candidate Strength
| strength | count |
|---|---:|
| STRONG_CANDIDATE | 1 |
| MODERATE_CANDIDATE | 2 |
| WEAK_CANDIDATE | 2 |

## Candidate Review
| proposed facet | strength | reviews | products | categories | expressions | product | seller | Naver reference |
|---|---|---:|---:|---:|---:|---|---|---|
| digestive_tolerance | WEAK_CANDIDATE | 1 | 1 | 1 | 2 | NOT_VERIFIABLE | NO_SELLER_SUPPORT | KOREAN_GENERAL_CONSUMER_EXPRESSION_SUPPORT (9) |
| intake_frequency | STRONG_CANDIDATE | 15 | 8 | 1 | 4 | NOT_VERIFIABLE | SUPPORTED_SELLER_DATA | KOREAN_GENERAL_CONSUMER_EXPRESSION_SUPPORT (15) |
| mixability | WEAK_CANDIDATE | 3 | 0 | 0 | 1 | NOT_VERIFIABLE | SUPPORTED_SELLER_DATA | KOREAN_GENERAL_CONSUMER_EXPRESSION_SUPPORT (106) |
| opening_convenience | MODERATE_CANDIDATE | 2 | 1 | 1 | 2 | NOT_VERIFIABLE | NO_SELLER_SUPPORT | KOREAN_GENERAL_CONSUMER_EXPRESSION_SUPPORT (325) |
| storage_convenience | MODERATE_CANDIDATE | 2 | 1 | 1 | 2 | NOT_VERIFIABLE | SUPPORTED_SELLER_DATA | KOREAN_GENERAL_CONSUMER_EXPRESSION_SUPPORT (711) |

## Interpretation
- `EXISTING_FACET`와 `NEW_VALUE`/`NEW_ALIAS`는 신규 Facet으로 승격하지 않는다.
- 배송·가격·프로모션·판매자 응대·수량·재구매·단순 만족 표현은 Non-Facet으로 분리한다.
- 의료 효능·질병 개선 표현은 `SUBJECTIVE_MEDICAL_OUTCOME`으로 별도 분리한다.
- Product/Seller에 없는 소비자 체감 특성도 `REVIEW_ONLY` 후보로 보존할 수 있으나 자동 승인하지 않는다.
- 모든 신규 후보의 reviewer_decision은 `PENDING_REVIEW`다.
