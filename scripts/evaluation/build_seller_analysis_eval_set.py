"""영역 2 고정 평가셋 100건을 생성한다.

구현은 `moongcheap_ai.seller_analysis.evaluation.eval_set` 에 있다.
이 파일은 진입점만 맡는다.

    python scripts/evaluation/build_seller_analysis_eval_set.py

⛔ 생성기는 `bid_guide` 를 부르지 않는다. 정답을 구현이 만들면 채점이 순환한다.
"""

from __future__ import annotations

from moongcheap_ai.seller_analysis.evaluation.eval_set import main

if __name__ == "__main__":
    main()
