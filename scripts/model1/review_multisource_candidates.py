"""Run deterministic review gates against Model 1 multi-source candidates."""
from __future__ import annotations

import argparse
from pathlib import Path

from moongcheap_ai.data_foundation.model1_review import write_review_artifacts


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--candidates", type=Path, default=Path("data/processed/model1_multisource_v1/multisource_model_candidates_v1.csv"))
    parser.add_argument("--input", type=Path, default=Path("data/processed/model1_multisource_v1/multisource_model_input_v1.jsonl"))
    parser.add_argument("--output-dir", type=Path, default=Path("data/processed/model1_multisource_v1"))
    args = parser.parse_args()
    print(write_review_artifacts(args.candidates, args.input, args.output_dir))


if __name__ == "__main__":
    main()
