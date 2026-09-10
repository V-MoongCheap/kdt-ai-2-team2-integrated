"""Prepare profile metadata against a proven compatible taxonomy release."""

import argparse
import json
from pathlib import Path

from moongcheap_ai.demand_clustering.evaluation.profile_release import prepare_profile_release


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--profiles", type=Path, required=True)
    parser.add_argument("--source-taxonomy", type=Path, required=True)
    parser.add_argument("--taxonomy", type=Path, default=Path("config/facet_taxonomy_v2_2.json"))
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(prepare_profile_release(
        args.profiles, args.source_taxonomy, args.taxonomy, args.output_dir,
    ), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
