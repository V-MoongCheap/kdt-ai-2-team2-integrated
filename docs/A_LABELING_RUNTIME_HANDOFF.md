# A파트 연결 실행 계약

## 흐름

```text
PostgreSQL read-only
  demand -> product_catalog -> category.facet
  -> TaxonomyLoader / product facet defaults
  -> demand label + facet_values
  -> Backend internal API
```

DB 연결정보와 Backend Endpoint가 아직 확정되지 않은 환경에서는 다음처럼
동일한 Labeling Core를 CSV로 검증한다.

```powershell
$env:PYTHONPATH = "src"
python -m moongcheap_ai.data_foundation.runtime_job `
  --input path/to/demands.csv `
  --taxonomy path/to/taxonomy.json `
  --dry-run
```

## 환경변수

- `A_DATABASE_URL`: PostgreSQL DSN. 런타임은 read-only session으로 연결한다.
- `A_TAXONOMY_PATH`: 승인된 Taxonomy artifact 경로
- `A_PRODUCT_FACETS_PATH`: 선택적 Product Facet mapping artifact
- `A_BACKEND_BASE_URL`: Backend base URL
- `A_BACKEND_INTERNAL_KEY`: 배포 환경에서 주입하는 내부 API Secret
- `A_LABEL_RESULT_ENDPOINT`: Backend와 합의한 라벨 결과 Endpoint. 임의 기본값을 두지 않는다.
- `A_BACKEND_HTTP_TIMEOUT_SECONDS`: 기본 15초

## DB 직접 저장 계약

제공된 Backend ERD 기준 운영 방식은 `demand` 테이블 직접 갱신이다. A는
미처리 Demand를 읽고, 성공한 결과만 `label`과 `processed_at`을 같은
트랜잭션으로 갱신한다.

- `demand.id`를 기준으로 갱신
- `demand.label`에 압축 Label 저장
- `demand.processed_at`에 성공 처리 시각 저장
- `processed_at IS NULL` 조건으로 재처리 경쟁 방지
- `REVIEW`/예외 행은 완료 처리하지 않음

`constraints`, 상태, 진단 정보는 실제 ERD에 없는 컬럼을 임의로 가정하지
않고, 배치 산출물 또는 별도 결과 저장 구조가 확정된 뒤 추가한다.

## Kubernetes/운영 원칙

- CronJob은 배치 1회 실행 후 종료한다.
- Taxonomy와 Product Facet artifact는 버전 경로로 마운트한다.
- DB URL와 Internal Key는 Secret으로 주입한다.
- API 호출 실패 시 임의 재시도하지 않고 다음 배치에서 미처리 수요를 재조회한다.
- `.env`, API Key, Raw Review, 생성 산출물은 Git에 올리지 않는다.
