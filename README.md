# 뭉치 AI (MoongCheap AI)

수요 주도형 공동구매 플랫폼의 AI 파트 저장소입니다.

## MVP 기능

1. **상품 Facet Discovery 및 Demand Labeling**
   - 상품 원문에서 Facet/Value/Alias 후보를 도출하고 Human Review 후 taxonomy를 확정
   - Backend가 저장한 Demand의 `extra_requirement`를 승인된 Facet Value와 Label로 변환
   - 자연어 처리는 실시간 요청이 아닌 비동기 Batch를 기본으로 함

2. **Demand Clustering**
   - 동일 `catalog_id`를 우선으로 Facet/가격/수량/대체상품 조건을 비교
   - `demand_board`를 Cluster로 사용
   - V0는 Rule 기반으로 시작하고 Embedding/Hybrid는 Gold Set 실험 후 선택

3. **Seller Offer Matching 및 Seller Demand Analysis**
   - Seller Offer는 `product`, 매칭 결과는 `product_award_evaluation`을 사용
   - 최종 매칭은 재현 가능한 Rule/Score 기반으로 처리하며 LLM의 임의 판단에 맡기지 않음
   - 수요 분석 수치는 SQL/Python 집계가 원천이며 LLM은 선택적 설명만 담당

## 시스템 담당 범위

- AI와 Backend는 동일한 PostgreSQL의 원본 데이터를 기준으로 사용합니다.
- AI Batch는 필요한 Demand와 DemandBoard를 읽기 전용으로 조회하고,
  생성·편입·대체 제안 계획 JSON을 Backend 내부 API로 전달합니다.
- 상태 변경 DML, 잠금과 트랜잭션은 Backend가 담당합니다.
- AI는 인증·권한, 원본 데이터, 수요·응찰·낙찰 상태를 관리하지 않습니다.
- AI 전용 DB, 임의의 테이블/컬럼/상태 추가를 전제로 하지 않습니다.
- Consumer RAG 챗봇은 현재 MVP에서 제외합니다.
- 특정 모델(Qwen3 등), Vector DB, 상시 모델 서버는 확정하지 않습니다.

## 저장소 구조

- `src/moongcheap_ai`: AI 서비스 및 데이터 파이프라인 구현
- `docs`: AI 서비스 설계, Facet taxonomy 및 API contract
- `docker`, `k8s`: 수요 클러스터링 이미지와 Kubernetes 기본 실행 계약
- `.github`: PR/이슈 템플릿 및 협업 설정

## 개발 작업 흐름

로컬·CI에서 같은 의존성 정의와 `uv.lock`을 사용합니다. Python 3.12 이상이
필요하며, 수요 클러스터링 컨테이너는 Python 3.13 / Linux CPU 환경을 사용합니다.

```bash
uv sync --locked --extra data --extra dev
uv run --no-sync pytest
```

기존 `pip install -r requirements.txt`도 같은 extra를 설치하지만 `uv.lock`을
적용하지는 않습니다. CPU E5도 사용할 개발 환경은
`uv sync --locked --extra data --extra dev --extra embeddings`로 설치합니다.
기본 테스트는 외부 DB·Backend·LLM·모델 다운로드 없이 실행합니다.
의존성 정의와 Ruff 규칙은 `pyproject.toml`, 해결된 버전은 `uv.lock`에서 관리합니다.

수요 클러스터링 운영 설정과 실패 후 다음 배치 처리 정책은
[배치 README](src/moongcheap_ai/demand_clustering/README.md)를 참고하세요.
이미지 빌드, 모델·데이터 마운트 및 인프라 전달 조건은
[컨테이너 실행 안내](docs/DEMAND_CLUSTERING_CONTAINER.md)에 정리했습니다.
CronJob·환경 변수·Secret·AI 전용 노드 설정은
[Kubernetes 안내](k8s/README.md)를 참고하세요. CI에서는 `kubectl`을 준비한 뒤
`tools/verify_kubernetes_manifests.sh`도 실행합니다. 실제 클러스터 접속은 필요 없습니다.

1. `main`에서 작업 브랜치를 생성합니다.
2. 작업 Branch에서 기존 AI Commit Convention을 따릅니다.
3. `develop` 대상 PR로 개발 통합 및 Dev 배포를 진행합니다.
4. 검증 후 `main`에 반영하여 Demo/Production 배포를 진행합니다.
5. 작성자가 아닌 팀원 1명의 승인과 CI 통과 후 squash merge합니다.

자세한 규칙은 [CONTRIBUTING.md](CONTRIBUTING.md)를 참고하세요.
