# 한국 건강기능식품 Purchase/Sales Evidence Sources

이 보고서는 실제 구매·판매 기반 근거와 단순 생산량·검색순위·시장 기사 자료를 구분한다. 검증 전 자료는 파이프라인에 넣지 않는다.

| Source | Basis | HFF 분리 | Access | Cost | Status | Next Step |
|---|---|---|---|---|---|---|
| Foodpolis / 식품정보24 | 공식 소매채널 판매정보 대시보드 | YES | MANUAL_DOWNLOAD | UNKNOWN | WAITING_FOR_MANUAL_DOWNLOAD | 공식 계정으로 Export 파일을 내려받아 data/raw/purchase/foodpolis/에 보관 |
| LG U+ 건강기능식품 융합데이터 | 공개 소개자료에서 시장지표가 언급되었으나 검증된 다운로드 URL/파일 미확인 | UNKNOWN | NOT_VERIFIED | FREE_ONLY | MISSING_VALID_SOURCE | 공식 무료 파일 또는 API URL을 확인하기 전에는 사용하지 않음 |
| 공공데이터포털 / FIS / 연구자료 | 후보 탐색 대상이나 Product-level HFF 구매·판매 원자료는 현재 로컬 검증 없음 | UNKNOWN | SEARCH_REQUIRED | FREE_ONLY | NOT_VERIFIED | 원자료·분류 기준·재사용 조건을 확인한 뒤 등록 |

## 현재 판정
- 검증 완료된 Product-level 또는 Category-level 구매/판매 원자료: 0개.
- Foodpolis는 공식 수동 Export 파일을 받기 전까지 `WAITING_FOR_MANUAL_DOWNLOAD`으로 유지한다.
- LG U+ 자료는 확인 가능한 공식 다운로드 파일이 없어 `MISSING_VALID_SOURCE`로 유지한다.
- 생산실적, 일반 시장규모, 검색·클릭 비율은 구매/판매 evidence로 승격하지 않는다.
