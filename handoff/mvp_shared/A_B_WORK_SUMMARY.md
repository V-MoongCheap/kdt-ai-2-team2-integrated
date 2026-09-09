# A/B 오늘 작업 요약

- A: V2.2 Taxonomy와 검수 완료 Alias를 Rule/Alias Runtime에 연결하고, `processed_at` 기준 재처리 방지 및 상태별 결과 기록을 추가했다.
- B: A의 `clustering_input`을 기존 결정적 Cluster baseline에 연결해 Catalog·Category·Facet Label·대체품 허용 여부를 반영한 Cluster를 생성하도록 검증했다.
- 통합: CSV Dry-run에서 200건 기준 Labeling 후 198건을 Clustering으로 전달했으며, 전체 테스트 `412 passed`를 확인했다.
