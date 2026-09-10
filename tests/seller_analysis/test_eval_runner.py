"""고정 평가셋으로 현재 구현을 채점한다.

21절 「Seller Analysis 목표 지표」 를 실제로 재고, 채점기가 통과시키면 안 되는 것을
통과시키지 않는지도 본다.

⛔ 정답은 생성기가 세운 값이므로 이 채점은 순환하지 않는다.
"""

from __future__ import annotations

import csv
import json
import unittest
from pathlib import Path

from moongcheap_ai.seller_analysis.bid_guide import (
    METRICS_VERSION,
    ContractViolation,
    VersionMismatch,
    handle_bid_guide,
)
from moongcheap_ai.seller_analysis.evaluation.eval_set import (
    EVAL_FIELDS,
    GROUND_TRUTH_FIELDS,
    MIN_PARTICIPANTS,
    SCENARIO_QUOTA,
    GeneratorError,
    _exact_ratio,
    build_cases,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
DATASET_DIR = REPO_ROOT / "data" / "evaluation" / "seller_analysis"


def read_csv(name: str) -> list[dict[str, str]]:
    with (DATASET_DIR / name).open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def as_request(row: dict[str, str]) -> dict:
    """평가 행을 계약 요청으로 바꾼다.

    평가 문서 16절의 입력 Schema 는 계산에 쓰이는 5개 값만 정의한다. 나머지 계약 필드는
    계산에 영향을 주지 않는 참조·버전 값이므로 여기서 고정값으로 채운다
    (16절 — *"실제 API Response의 최종 Field명은 Backend / AI API Contract와 동일하게 맞춘다"*).
    """
    payload = {
        "request_id": row["eval_id"],
        "input_context_version": "eval-context-v1",
        # 계산에 쓰이지 않는 참조값이다. 정수 계약이므로 eval_id 의 일련번호를 쓴다.
        "cluster_ref": int(row["eval_id"].rsplit("_", 1)[-1]),
        "product_ref": int(row["eval_id"].rsplit("_", 1)[-1]),
        "calculation_policy_version": METRICS_VERSION,
    }
    for field in (
        "participant_count",
        "total_demand_quantity",
        "minimum_success_quantity",
        "maximum_supply_quantity",
    ):
        payload[field] = int(row[field])

    overrides = json.loads(row["invalid_input_overrides"] or "{}")
    for field in overrides.get("remove", []):
        payload.pop(field, None)
    payload.update(overrides.get("set", {}))
    return payload


class EvalRunnerTest(unittest.TestCase):
    """실행기가 테스트와 같은 결론을 내는지 본다. 채점 경로가 둘로 갈리면 안 된다."""

    def test_runner_reports_every_target_met(self):
        from moongcheap_ai.seller_analysis.evaluation.runner import TARGETS, evaluate

        report = evaluate()
        self.assertEqual(report["case_count"], 100)
        self.assertEqual(report["failures"], [])
        self.assertTrue(report["all_targets_met"])
        for name in TARGETS:
            self.assertIn(name, report["metrics"], name)

    def test_runner_counts_invalid_cases_outside_numeric_accuracy(self):
        """18.1절 — Invalid Input Case 는 Numeric Accuracy 의 분모에서 제외한다."""
        from moongcheap_ai.seller_analysis.evaluation.runner import evaluate

        metrics = evaluate()["metrics"]
        self.assertEqual(metrics["numeric_accuracy"]["denominator"], 95)
        self.assertEqual(metrics["invalid_input_rejection_accuracy"]["denominator"], 5)

    def test_runner_does_not_build_its_own_answers(self):
        """⛔ 실행기가 정답을 계산하면 채점이 순환한다. 정답 CSV 만 읽어야 한다."""
        source = (
            Path(__file__).resolve().parents[2]
            / "src" / "moongcheap_ai" / "seller_analysis" / "evaluation" / "runner.py"
        ).read_text(encoding="utf-8")
        self.assertIn("GROUND_TRUTH_CSV", source)
        self.assertNotIn("build_cases", source)


class EvalSetScoringTest(unittest.TestCase):
    """평가셋으로 현재 구현을 채점한다. 21절 「Seller Analysis 목표 지표」 기준."""

    @classmethod
    def setUpClass(cls):
        eval_rows = {row["eval_id"]: row for row in read_csv("seller_analysis_eval_v1.csv")}
        cls.pairs = [
            (eval_rows[truth["eval_id"]], truth)
            for truth in read_csv("seller_analysis_ground_truth_v1.csv")
        ]

    def _responses(self):
        for row, truth in self.pairs:
            if truth["expected_request_result"] != "SUCCESS":
                continue
            yield truth, handle_bid_guide(as_request(row))["metrics"]

    def test_numeric_accuracy_is_100_percent(self):
        for truth, metrics in self._responses():
            with self.subTest(eval_id=truth["eval_id"]):
                self.assertEqual(
                    metrics["moq_attainment_ratio"],
                    float(truth["expected_moq_attainment_ratio"]),
                )
                self.assertEqual(
                    metrics["supply_coverage_ratio"],
                    float(truth["expected_supply_coverage_ratio"]),
                )

    def test_moq_and_supply_status_accuracy_are_100_percent(self):
        """상태는 응답에 없다. 계약대로 **비율에서 도출**해 채점한다.

        「AI API Contract」 5절 Response 표가 `metrics` 를 네 필드로 정하므로 상태 필드는
        응답에 싣지 않는다. `ratio >= 1.0` 이 충족과 동치라는 것이 이 채점의 전제다.
        """
        for truth, metrics in self._responses():
            with self.subTest(eval_id=truth["eval_id"]):
                derived_moq = (
                    "MOQ_MET" if metrics["moq_attainment_ratio"] >= 1.0 else "MOQ_NOT_MET"
                )
                derived_supply = (
                    "SUPPLY_SUFFICIENT"
                    if metrics["supply_coverage_ratio"] >= 1.0
                    else "SUPPLY_INSUFFICIENT"
                )
                self.assertEqual(derived_moq, truth["expected_moq_status"])
                self.assertEqual(derived_supply, truth["expected_supply_status"])

    def test_invalid_input_rejection_accuracy_is_100_percent(self):
        for row, truth in self.pairs:
            if truth["expected_request_result"] != "REJECTED":
                continue
            with self.subTest(eval_id=truth["eval_id"]):
                with self.assertRaises((ContractViolation, VersionMismatch)):
                    handle_bid_guide(as_request(row))

    def test_no_individual_consumer_value_reaches_the_response(self):
        """20절 「개인정보 안전성 평가」 — PII Leakage Rate 0%."""
        for row, truth in self.pairs:
            if truth["expected_request_result"] != "SUCCESS":
                continue
            body = json.dumps(handle_bid_guide(as_request(row)), ensure_ascii=False)
            for leaked in ("member_id", "user_id", "buyer_id", "MEMBER_"):
                self.assertNotIn(leaked, body)

    def test_evidence_never_contradicts_the_status(self):
        """18.4절 Evidence Consistency — 설명과 구조화 결과가 어긋나지 않는다."""
        for row, truth in self.pairs:
            if truth["expected_request_result"] != "SUCCESS":
                continue
            result = handle_bid_guide(as_request(row))
            evidence = " ".join(result["calculation_evidence"])
            with self.subTest(eval_id=truth["eval_id"]):
                self.assertIn(truth["expected_moq_status"], evidence)
                self.assertIn(truth["expected_supply_status"], evidence)


class EvalRunnerRigourTest(unittest.TestCase):
    """B4 — 실행기가 통과시키면 안 되는 것들을 통과시켰다."""

    def _report_with_body(self, mutate):
        from unittest import mock

        from moongcheap_ai.seller_analysis.evaluation import runner

        original = runner.handle_bid_guide

        def patched(payload):
            body = original(payload)
            mutate(body)
            return body

        with mock.patch.object(runner, "handle_bid_guide", side_effect=patched):
            return runner.evaluate()

    def test_wrong_type_fails_schema_validation(self):
        """계약은 `analysis_reason` 을 string 으로 정한다. 정수 123 은 통과하면 안 된다.

        키 집합만 비교하던 검사는 이것을 95/95 로 통과시켰다.
        """
        def to_integer(body):
            body["analysis_reason"] = 123

        report = self._report_with_body(to_integer)
        self.assertEqual(report["metrics"]["response_schema_validation_success"]["count"], 0)
        self.assertFalse(report["all_targets_met"])

    def test_out_of_range_value_fails_schema_validation(self):
        """`minimum` 도 계약이다. 음수 비율은 구조가 맞아도 계약 위반이다."""
        def negative_ratio(body):
            body["metrics"]["moq_attainment_ratio"] = -1.0

        report = self._report_with_body(negative_ratio)
        self.assertEqual(report["metrics"]["response_schema_validation_success"]["count"], 0)

    def test_extra_sentence_fails_evidence_consistency(self):
        """계약은 근거를 *"템플릿으로만"* 만들라고 한다. 덧붙은 문장은 템플릿이 아니다."""
        def append_sentence(body):
            body["calculation_evidence"].append("검증용 모순 문장: 모든 수량 계산은 잘못됐습니다.")

        report = self._report_with_body(append_sentence)
        self.assertEqual(report["metrics"]["evidence_consistency"]["count"], 0)
        self.assertFalse(report["all_targets_met"])

    def test_empty_dataset_is_not_a_pass(self):
        """⛔ 채점하지 못한 것은 통과가 아니다. `all([])` 이 참이라는 사실에 기대지 않는다."""
        from unittest import mock

        from moongcheap_ai.seller_analysis.evaluation import runner

        with mock.patch.object(runner, "read_csv", return_value=[]):
            report = runner.evaluate()
        self.assertEqual(report["case_count"], 0)
        self.assertFalse(report["all_targets_met"])
        self.assertTrue(report["unmeasured_metrics"])

    def test_validator_refuses_keywords_it_does_not_implement(self):
        """계약에 새 키워드가 생기면 조용히 넘어가지 않고 멈춘다."""
        from moongcheap_ai.seller_analysis.evaluation.runner import validate_against_schema

        with self.assertRaises(NotImplementedError):
            validate_against_schema("x", {"type": "string", "pattern": "^x$"})


class NumericToleranceTest(unittest.TestCase):
    """18.1절이 *"사전에 정한 허용 오차"* 를 요구한다. 그 값을 못박는다."""

    def test_tolerance_is_far_below_the_declared_precision(self):
        """⛔ 자리수를 허용 오차로 쓰면 그 자리수 명세가 무의미해진다.

        계약이 비율을 소수 4자리로 두므로(`numeric(5,4)`) 허용 오차가 1e-4 면
        마지막 자리가 통째로 덮인다. 표현 오차만 흡수하는 폭이어야 한다.
        """
        from moongcheap_ai.seller_analysis.bid_guide import RATIO_PRECISION
        from moongcheap_ai.seller_analysis.evaluation.runner import NUMERIC_TOLERANCE

        self.assertLess(NUMERIC_TOLERANCE, 10 ** -RATIO_PRECISION / 1000)

    def test_tolerance_does_not_hide_a_real_error(self):
        """마지막 자리 한 칸이 틀리면 잡아야 한다."""
        from unittest import mock

        from moongcheap_ai.seller_analysis.evaluation import runner

        original = runner.handle_bid_guide

        def off_by_one_ulp(payload):
            body = original(payload)
            body["metrics"]["moq_attainment_ratio"] += 10 ** -runner.__dict__.get("RATIO", 4)
            return body

        with mock.patch.object(runner, "handle_bid_guide", side_effect=off_by_one_ulp):
            report = runner.evaluate()
        self.assertEqual(report["metrics"]["numeric_accuracy"]["count"], 0)

    def test_report_records_the_tolerance_it_used(self):
        from moongcheap_ai.seller_analysis.evaluation.runner import NUMERIC_TOLERANCE, evaluate

        self.assertEqual(evaluate()["numeric_tolerance"], NUMERIC_TOLERANCE)
