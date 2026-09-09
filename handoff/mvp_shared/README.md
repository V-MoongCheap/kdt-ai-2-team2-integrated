# MVP 공유 파일 묶음

이 폴더는 다른 개발 환경에서 A/B/C 로컬 Smoke Test를 시작할 때 필요한 파일을 한곳에 모은 것이다.

## 포함 내용

- `config/`: V2.2 Taxonomy, Reviewed Alias, B 제약 조건 설정
- `smoke/demands_v2_2.csv`: Demand 20건
- `smoke/product_facets_smoke.csv`: Smoke Demand에 대응하는 상품 Facet 입력
- `smoke/seller_offers_smoke.csv`: Seller Offer 200건
- `.env.example`: 환경변수 이름만 포함하며 비밀값은 없음
- `manifest.json`: 파일 출처, 크기, SHA-256

## 실행 예시

```powershell
$env:PYTHONPATH = "src"
python -m moongcheap_ai.mvp_pipeline `
  --input handoff/mvp_shared/smoke/demands_v2_2.csv `
  --taxonomy handoff/mvp_shared/config/facet_taxonomy_v2_2.json `
  --alias-registry handoff/mvp_shared/config/model1_aliases_reviewed_v2.json `
  --product-facets handoff/mvp_shared/smoke/product_facets_smoke.csv `
  --output-dir data/processed/mvp_e2e_v2_2 `
  --dry-run
```

그 다음 `clustering_input_v2_2.csv`를 B 입력으로 사용한다. C PR이 반영되면 C Smoke 실행 파일과 `/health` 확인 명령을 이 폴더에 추가한다.

## 포함하지 않는 것

PostgreSQL 접속정보, Backend 내부키, API Key, E5 모델, 전체 상품/공고 Raw 데이터는 포함하지 않는다. 운영에서는 Parameter Store/Secret과 별도 Artifact 저장소를 사용한다.
