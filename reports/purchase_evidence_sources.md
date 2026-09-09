# 한국 건강기능식품 Purchase/Sales Evidence Sources

이 보고서는 실제 구매·판매 기반 근거와 단순 생산량·검색순위·시장 기사 자료를 구분한다. 검증 전 자료는 파이프라인에 넣지 않는다.

| Source | Basis | HFF 분리 | Access | Cost | Status | Next Step |
|---|---|---|---|---|---|---|
| Foodpolis / 식품정보24 | 공식 소매채널 판매정보 대시보드 | YES | MANUAL_DASHBOARD_EXPORT | UNKNOWN | WAITING_FOR_DASHBOARD_ACCESS | 승인 후 마이페이지 → 나만의 대시보드 → 서비스 접속에서 Export |
| LG U+ 건강기능식품 융합데이터 | 공급처에 무료 파일 제공 문의 중이며 검증된 파일 미확보 | UNKNOWN | PROVIDER_RESPONSE_PENDING | FREE_ONLY | WAITING_FOR_PROVIDER_RESPONSE | 회신 및 파일 확보 후 기존 Adapter로 처리 |
| 공공데이터포털 / FIS / 연구자료 | 후보 탐색 대상이나 Product-level HFF 구매·판매 원자료는 현재 로컬 검증 없음 | UNKNOWN | SEARCH_REQUIRED | FREE_ONLY | NOT_VERIFIED | 원자료·분류 기준·재사용 조건을 확인한 뒤 등록 |

## 현재 판정
- 검증 완료된 Product-level 또는 Category-level 구매/판매 원자료: 0개.
- Foodpolis 공식 서비스 소개에는 소매채널 판매정보가 존재하지만 Open API 상세 Endpoint는 현재 확인되지 않았다(`FOODPOLIS_OPEN_API_AVAILABLE=false`).
- Foodpolis는 사용자의 대시보드 신청 후 승인 대기 상태이며, 비공개 API를 추측하지 않는다.
- LG U+는 제공처 회신 대기 상태이며, 추가 다운로드 시도를 요구하지 않는다.
- 생산실적, 일반 시장규모, 검색·클릭 비율은 구매/판매 evidence로 승격하지 않는다.
