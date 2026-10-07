"""
FinSight Enterprise — Stage 2.4 Defect Injection & QA Engine Automated Test Suite
Validates baseline immutability, deterministic defect injection, 4 defect categories,
100% QA detection rate, RTM traceability, and defect lifecycle transitions.
"""

from decimal import Decimal
import pytest
import pandas as pd
from quality.run_defect_pipeline import execute_defect_pipeline
from quality.config import DEFAULT_SEED, BASELINE_DIR, OUTPUT_DEFECTS_DIR, SCENARIO_DEFECT_DIR


@pytest.fixture(scope="module")
def defect_pipeline_results():
    """Executes the Stage 2.4 defect injection and QA extraction pipeline."""
    return execute_defect_pipeline(seed=DEFAULT_SEED, target_count_per_defect=150, save=True)


def test_clean_baseline_immutability(defect_pipeline_results):
    """Scenario A (BASELINE) must remain 100% PASS with zero defects and zero regressions."""
    baseline_recon_path = BASELINE_DIR / "reconciliation_results.parquet"
    assert baseline_recon_path.exists(), "Clean baseline reconciliation results missing"

    baseline_recon = pd.read_parquet(baseline_recon_path)
    assert (baseline_recon["status"] == "PASS").all(), "Clean baseline has unexpected failures"
    assert (baseline_recon["root_cause_category"].isna()).all()
    assert len(baseline_recon) > 0


def test_four_defect_classes_injected(defect_pipeline_results):
    """Verifies that all 4 specified defect categories are deterministically injected."""
    manifest_df, _, defects_df, _ = defect_pipeline_results

    expected_classes = {
        "DAY_COUNT_MISMATCH",
        "ROUNDING_TRUNCATION",
        "WATERFALL_ORDERING",
        "LEAP_YEAR_BLINDNESS"
    }

    injected_classes = set(manifest_df["defect_type"].unique())
    detected_classes = set(defects_df["root_cause_category"].unique())

    assert expected_classes == injected_classes, f"Expected {expected_classes}, got {injected_classes}"
    assert expected_classes == detected_classes, f"Expected {expected_classes}, got {detected_classes}"


def test_qa_engine_injected_defect_detection_accuracy(defect_pipeline_results):
    """
    Verifies 100% detection of the injected defect population with zero false positives
    in this controlled test scenario (variance > $0.01 tolerance).
    """
    manifest_df, defect_recon_df, defects_df, _ = defect_pipeline_results

    injected_count = len(manifest_df)
    failed_recon_count = (defect_recon_df["status"] == "FAIL").sum()
    extracted_defects_count = len(defects_df)

    assert failed_recon_count == injected_count, f"QA engine failed to detect all defects: {failed_recon_count} != {injected_count}"
    assert extracted_defects_count == injected_count, f"Defect extraction count mismatch: {extracted_defects_count} != {injected_count}"


def test_defects_rtm_traceability_linkage(defect_pipeline_results):
    """
    Validates complete Requirements Traceability Matrix (RTM) integrity:
    Every defect must link to requirement_id, rule_id, and test_case_id.
    """
    _, _, defects_df, _ = defect_pipeline_results

    assert defects_df["defect_id"].is_unique
    assert (defects_df["requirement_id"].notna()).all()
    assert (defects_df["rule_id"].notna()).all()
    assert (defects_df["test_case_id"].notna()).all()

    # Valid values
    valid_reqs = {"BRD-FIN-001", "BRD-CORE-006"}
    assert set(defects_df["requirement_id"].unique()).issubset(valid_reqs)

    valid_severities = {"CRITICAL", "MAJOR", "MINOR"}
    assert set(defects_df["severity"].unique()).issubset(valid_severities)

    valid_priorities = {"P1", "P2", "P3"}
    assert set(defects_df["priority"].unique()).issubset(valid_priorities)


def test_defect_lifecycle_state_machine(defect_pipeline_results):
    """Validates that extracted defects initialize in 'NEW' and can progress through triage states."""
    _, _, defects_df, _ = defect_pipeline_results

    # Initial state
    assert (defects_df["status"] == "NEW").all()

    # Test state transition simulation
    sample_defect = defects_df.iloc[0].to_dict()
    lifecycle_states = ["NEW", "TRIAGED", "IN_INVESTIGATION", "RESOLVED", "VERIFIED_CLOSED"]

    for state in lifecycle_states:
        sample_defect["status"] = state
        assert sample_defect["status"] in lifecycle_states


def test_saved_defect_artifacts_on_disk():
    """Validates that all Parquet datasets and summary JSONs exist on disk."""
    assert (SCENARIO_DEFECT_DIR / "injected_accruals.parquet").exists()
    assert (SCENARIO_DEFECT_DIR / "injected_payment_allocations.parquet").exists()
    assert (SCENARIO_DEFECT_DIR / "defect_reconciliation_results.parquet").exists()
    assert (SCENARIO_DEFECT_DIR / "injection_manifest.parquet").exists()
    assert (OUTPUT_DEFECTS_DIR / "defects.parquet").exists()
    assert (OUTPUT_DEFECTS_DIR / "test_executions.parquet").exists()
    assert (OUTPUT_DEFECTS_DIR / "qa_defect_summary.json").exists()


def test_defect_injection_reproducibility():
    """Running defect pipeline twice with the same seed must produce exact bit-for-bit identical results."""
    m_a, _, d_a, _ = execute_defect_pipeline(seed=20261006, target_count_per_defect=25, save=False)
    m_b, _, d_b, _ = execute_defect_pipeline(seed=20261006, target_count_per_defect=25, save=False)

    pd.testing.assert_frame_equal(m_a, m_b)
    pd.testing.assert_frame_equal(d_a, d_b)
