"""
FinSight Enterprise — Power BI Semantic Model & DAX Automated Test Suite
Validates:
1. Tabular semantic model JSON specification (Kimball Star Schema)
2. Integrity of DAX measures library across all 8 enterprise folders
3. 100% mathematical tie-out between DAX measures and Gold Parquet facts
"""

import json
from pathlib import Path
import pytest

from powerbi.validate_dax_measures import validate_all_dax_measures

BASE_DIR = Path(__file__).resolve().parent.parent.parent
POWERBI_DIR = BASE_DIR / "powerbi"


def test_semantic_model_json_schema():
    """Validates that the Power BI semantic model specification conforms to Kimball standards."""
    model_path = POWERBI_DIR / "semantic_model.json"
    assert model_path.exists(), "semantic_model.json missing"

    with open(model_path, "r", encoding="utf-8") as f:
        model = json.load(f)

    assert model["name"] == "FinSight Enterprise Semantic Model"
    tables = {t["name"]: t for t in model["tables"]}

    expected_tables = {
        "dim_date", "dim_customer", "dim_product", "dim_loan",
        "fact_loan_performance", "fact_payment", "fact_financial",
        "fact_test_execution", "fact_defect", "fact_data_quality"
    }
    assert expected_tables.issubset(set(tables.keys()))

    # Verify primary keys and grains
    for t_name in expected_tables:
        t = tables[t_name]
        assert "grain" in t, f"Missing grain in {t_name}"
        assert "primaryKey" in t, f"Missing primaryKey in {t_name}"
        assert len(t["columns"]) > 0

    # Verify relationships
    rels = model["relationships"]
    assert len(rels) >= 10
    rel_pairs = {(r["fromTable"], r["toTable"]) for r in rels}
    assert ("fact_loan_performance", "dim_date") in rel_pairs
    assert ("fact_loan_performance", "dim_loan") in rel_pairs
    assert ("fact_payment", "dim_date") in rel_pairs
    assert ("fact_payment", "dim_loan") in rel_pairs
    assert ("fact_financial", "dim_date") in rel_pairs
    assert ("fact_defect", "dim_date") in rel_pairs
    assert ("fact_data_quality", "dim_date") in rel_pairs


def test_dax_measure_file_completeness():
    """Validates that dax_measures.dax and catalog contain all required measures."""
    dax_path = POWERBI_DIR / "dax_measures.dax"
    catalog_path = POWERBI_DIR / "metric-documentation" / "dax_measures_catalog.md"

    assert dax_path.exists(), "dax_measures.dax missing"
    assert catalog_path.exists(), "dax_measures_catalog.md missing"

    dax_content = dax_path.read_text(encoding="utf-8")
    catalog_content = catalog_path.read_text(encoding="utf-8")

    essential_measures = [
        "[Total Loans]",
        "[Original Principal]",
        "[Outstanding Principal]",
        "[Total Payment Volume]",
        "[Principal Collected]",
        "[Interest Collected]",
        "[Fees Collected]",
        "[Prepayments Collected]",
        "[Delinquent Balance (30+ DPD)]",
        "[Delinquency Rate (30+ DPD)]",
        "[Total Debits]",
        "[Total Credits]",
        "[GL Variance (Debit - Credit)]",
        "[Total Defects]",
        "[Critical Defects]",
        "[Major Defects]",
        "[Defect Density per 1k Ops]",
        "[Defect Injection Rate %]",
        "[Total Financial Variance Exposure]",
        "[Overall DQ Compliance %]"
    ]

    for m in essential_measures:
        assert m in dax_content, f"Missing DAX measure: {m} in dax_measures.dax"
        assert m in catalog_content, f"Missing DAX measure: {m} in dax_measures_catalog.md"


def test_dax_measure_ground_truth_reconciliation():
    """
    Validates 100% mathematical tie-out between DAX measure formulas
    and the Gold Star Schema Parquet facts.
    """
    scorecard = validate_all_dax_measures()

    assert scorecard["status"] == "ALL_MEASURES_PASSED"
    assert scorecard["measures_failed"] == 0
    assert scorecard["pass_rate_pct"] == 100.0

    measure_dict = {m["measure_name"]: m for m in scorecard["measure_results"]}

    # Control value assertions
    assert measure_dict["Total Loans"]["computed_gold_value"] == 2500
    assert measure_dict["Total Payment Volume"]["computed_gold_value"] == 351574751.19
    assert measure_dict["GL Debit-Credit Variance"]["computed_gold_value"] == 0.0
    assert measure_dict["Total Defects"]["computed_gold_value"] == 600
    assert measure_dict["Financial Variance Exposure"]["computed_gold_value"] == 901738.50
    assert measure_dict["Overall DQ Compliance %"]["computed_gold_value"] == 100.0


def test_generated_pbip_project_artifacts():
    """
    Validates that the native Power BI Project (.pbip) artifacts
    conform to official Microsoft PBIP schemas, contain conformed TOM model.bim,
    and 6-page report.json.
    """
    from powerbi.generate_pbip import validate_pbip_project_schema

    pbip_file = POWERBI_DIR / "FinSight_Enterprise.pbip"
    model_bim = POWERBI_DIR / "FinSight_Enterprise.Dataset" / "model.bim"
    report_json = POWERBI_DIR / "FinSight_Enterprise.Report" / "report.json"
    pbir_file = POWERBI_DIR / "FinSight_Enterprise.Report" / "definition.pbir"

    assert pbip_file.exists(), "FinSight_Enterprise.pbip missing"
    assert model_bim.exists(), "model.bim missing"
    assert report_json.exists(), "report.json missing"
    assert pbir_file.exists(), "definition.pbir missing"

    # Schema conformity check
    with open(pbip_file, "r", encoding="utf-8") as f:
        pbip = json.load(f)
    assert "version" in pbip
    assert "artifacts" in pbip
    assert "enableAutoAuth" not in pbip.get("settings", {}), "enableAutoAuth must NOT exist in settings"
    assert pbip["settings"].get("enableAutoRecovery") is True

    # Report definition conformity check
    with open(pbir_file, "r", encoding="utf-8") as f:
        pbir = json.load(f)
    assert "datasetReference" in pbir
    assert "byPath" in pbir["datasetReference"]
    assert "byConnection" not in pbir["datasetReference"]

    # Semantic model manifest conformity check (single coherent format)
    dataset_dir = POWERBI_DIR / "FinSight_Enterprise.Dataset"
    pbism_file = dataset_dir / "definition.pbism"
    pbidataset_file = dataset_dir / "definition.pbidataset"

    assert pbism_file.exists(), "definition.pbism must exist"
    assert not pbidataset_file.exists(), "definition.pbidataset must NOT exist"
    assert not (pbism_file.exists() and pbidataset_file.exists()), (
        "Power BI Desktop prohibits both definition.pbism and definition.pbidataset simultaneously"
    )

    # Formal jsonschema validation across all project files
    assert validate_pbip_project_schema() is True

    with open(model_bim, "r", encoding="utf-8") as f:
        bim = json.load(f)

    assert bim.get("name", "FinSight_Enterprise") == "FinSight_Enterprise"
    assert bim["compatibilityLevel"] == 1606, f"Expected compatibilityLevel 1606, got {bim.get('compatibilityLevel')}"
    assert bim["compatibilityLevel"] >= 1606, "compatibilityLevel must not be lower than the installed target (1606)"
    tables = {t["name"]: t for t in bim["model"]["tables"]}
    expected_business_tables = {
        "dim_date", "dim_customer", "dim_product", "dim_loan",
        "fact_loan_performance", "fact_payment", "fact_financial",
        "fact_test_execution", "fact_defect", "fact_data_quality", "_Measures"
    }
    assert expected_business_tables.issubset(set(tables.keys())), f"Missing business tables: {expected_business_tables - set(tables.keys())}"
    assert len(tables) >= 11
    assert "_Measures" in tables
    assert len(tables["_Measures"]["measures"]) >= 45

    # Relationship conformity check (TMSL CrossFilteringBehavior validation)
    relationships = bim["model"]["relationships"]
    assert len(relationships) >= 12
    valid_behaviors = {"oneDirection", "bothDirections", "automatic"}
    for r in relationships:
        cf = r.get("crossFilteringBehavior", "oneDirection")
        assert cf != "singleDirection", f"Relationship {r['name']} contains invalid 'singleDirection'"
        assert cf in valid_behaviors, f"Relationship {r['name']} contains invalid behavior: {cf}"
        assert cf == "oneDirection", f"Relationship {r['name']} expected 'oneDirection', got {cf}"
        assert r.get("isActive", True) is True

    with open(report_json, "r", encoding="utf-8") as f:
        rep = json.load(f)

    assert len(rep["sections"]) == 6
    page_names = [s["displayName"] for s in rep["sections"]]
    assert page_names == [
        "Executive Overview",
        "Lending Performance",
        "Financial Performance",
        "Forecast & Scenario",
        "QA & Defects",
        "Data Quality & Operations"
    ]


def test_semantic_model_mutual_exclusivity_rejection(tmp_path):
    """
    Validates that validate_pbip_project_schema explicitly fails if
    definition.pbidataset exists alongside or instead of definition.pbism.
    """
    from powerbi.generate_pbip import validate_pbip_project_schema

    pbidataset_path = POWERBI_DIR / "FinSight_Enterprise.Dataset" / "definition.pbidataset"
    assert not pbidataset_path.exists()

    try:
        # Simulate bad dual-manifest generation
        pbidataset_path.write_text('{"version": "1.0", "settings": {}}', encoding="utf-8")
        with pytest.raises(ValueError, match="Mutual exclusivity violation|both definition.pbism and definition.pbidataset"):
            validate_pbip_project_schema()
    finally:
        if pbidataset_path.exists():
            pbidataset_path.unlink()

    # Verify project is valid after cleaning up simulation
    assert validate_pbip_project_schema() is True


def test_relationship_cross_filtering_behavior_regression():
    """
    Validates that:
    1. No relationship in model.bim contains 'singleDirection'.
    2. All relationships contain valid 'oneDirection' CrossFilteringBehavior.
    3. validate_pbip_project_schema explicitly rejects 'singleDirection' with a clear error.
    """
    from powerbi.generate_pbip import validate_pbip_project_schema

    model_bim_path = POWERBI_DIR / "FinSight_Enterprise.Dataset" / "model.bim"
    with open(model_bim_path, "r", encoding="utf-8") as f:
        bim = json.load(f)

    # 1. Assert existing model.bim is completely free of singleDirection
    relationships = bim["model"]["relationships"]
    assert len(relationships) >= 12
    for r in relationships:
        cf = r.get("crossFilteringBehavior", "oneDirection")
        assert cf != "singleDirection"
        assert cf == "oneDirection"

    # 2. Simulate bad relationship with singleDirection and verify rejection
    bad_bim = json.loads(json.dumps(bim))
    bad_bim["model"]["relationships"][0]["crossFilteringBehavior"] = "singleDirection"
    try:
        with open(model_bim_path, "w", encoding="utf-8") as f:
            json.dump(bad_bim, f, indent=2)

        with pytest.raises(ValueError, match="Cannot convert value 'singleDirection' to required type 'CrossFilteringBehavior'"):
            validate_pbip_project_schema()
    finally:
        # Restore valid model.bim
        with open(model_bim_path, "w", encoding="utf-8") as f:
            json.dump(bim, f, indent=2)

    assert validate_pbip_project_schema() is True


def test_report_visual_queries_and_projections_populated():
    """
    Validates that:
    1. Exactly 6 report pages exist with correct business names.
    2. Exactly 48 visuals exist across all 6 pages as specified in layout spec.
    3. Every visual has valid visualType.
    4. Every non-textbox visual has non-empty projections and prototypeQuery.
    5. All referenced measures exist in model.bim / dax_measures.
    6. All referenced columns exist in Kimball star schema tables.
    7. No visual is merely an empty container or placeholder.
    """
    report_json_path = POWERBI_DIR / "FinSight_Enterprise.Report" / "report.json"
    model_bim_path = POWERBI_DIR / "FinSight_Enterprise.Dataset" / "model.bim"

    with open(report_json_path, "r", encoding="utf-8") as f:
        rep = json.load(f)
    with open(model_bim_path, "r", encoding="utf-8") as f:
        bim = json.load(f)

    tables_dict = {t["name"]: {c["name"] for c in t.get("columns", [])} for t in bim["model"]["tables"]}
    measures_set = {m["name"] for t in bim["model"]["tables"] for m in t.get("measures", [])}

    expected_page_names = [
        "Executive Overview",
        "Lending Performance",
        "Financial Performance",
        "Forecast & Scenario",
        "QA & Defects",
        "Data Quality & Operations"
    ]
    sections = rep["sections"]
    assert len(sections) == 6
    assert [s["displayName"] for s in sections] == expected_page_names

    expected_counts = [10, 7, 8, 6, 9, 8]
    total_visuals = 0

    for idx, sec in enumerate(sections):
        containers = sec["visualContainers"]
        assert len(containers) == expected_counts[idx], (
            f"Page {sec['displayName']} expected {expected_counts[idx]} visuals, got {len(containers)}"
        )

        for c in containers:
            total_visuals += 1
            cfg = json.loads(c["config"])
            sv = cfg["singleVisual"]
            vt = sv["visualType"]

            if vt == "textbox":
                gen = sv["objects"]["general"]
                assert len(gen) > 0
                assert len(gen[0]["properties"]["paragraphs"]) > 0
                runs = gen[0]["properties"]["paragraphs"][0]["textRuns"]
                assert len(runs) > 0
                assert len(runs[0]["value"]) > 10
            else:
                proj = sv.get("projections", {})
                assert len(proj) > 0, f"Visual {cfg.get('name')} has empty projections"

                proto = sv.get("prototypeQuery", {})
                selects = proto.get("Select", [])
                froms = proto.get("From", [])
                assert len(selects) > 0, f"Visual {cfg.get('name')} has 0 Select expressions"
                assert len(froms) > 0, f"Visual {cfg.get('name')} has 0 From entities"

                # Check all fields in prototypeQuery exist in model
                for sel in selects:
                    if "Measure" in sel:
                        m_name = sel["Measure"]["Property"]
                        assert m_name in measures_set, f"Measure {m_name} not in model.bim measures"
                    elif "Column" in sel:
                        c_name = sel["Column"]["Property"]
                        src = sel["Column"]["Expression"]["SourceRef"]["Source"]
                        ent = next(f["Entity"] for f in froms if f["Name"] == src)
                        assert ent in tables_dict, f"Table {ent} not in model.bim"
                        assert c_name in tables_dict[ent], f"Column {c_name} not in table {ent}"

    assert total_visuals == 48


def test_report_visual_placeholder_rejection_regression():
    """
    Validates that validate_pbip_project_schema explicitly rejects
    empty placeholder visuals (missing projections or prototypeQuery).
    """
    from powerbi.generate_pbip import validate_pbip_project_schema

    report_json_path = POWERBI_DIR / "FinSight_Enterprise.Report" / "report.json"
    with open(report_json_path, "r", encoding="utf-8") as f:
        rep = json.load(f)

    # Mutate one visual to be an empty placeholder
    bad_rep = json.loads(json.dumps(rep))
    bad_cfg = json.loads(bad_rep["sections"][0]["visualContainers"][0]["config"])
    bad_cfg["singleVisual"]["projections"] = {}
    bad_rep["sections"][0]["visualContainers"][0]["config"] = json.dumps(bad_cfg)

    try:
        with open(report_json_path, "w", encoding="utf-8") as f:
            json.dump(bad_rep, f, indent=2)

        with pytest.raises(ValueError, match="has empty projections|Placeholder visuals are prohibited"):
            validate_pbip_project_schema()
    finally:
        with open(report_json_path, "w", encoding="utf-8") as f:
            json.dump(rep, f, indent=2)

    assert validate_pbip_project_schema() is True


def test_semantic_model_compatibility_level_downgrade_rejection():
    """
    Validates that:
    1. model.bim compatibilityLevel is exactly 1606.
    2. validate_pbip_project_schema explicitly fails if an older compatibility level
       (e.g., 1567) or any level < 1606 is encountered.
    """
    from powerbi.generate_pbip import validate_pbip_project_schema

    model_bim_path = POWERBI_DIR / "FinSight_Enterprise.Dataset" / "model.bim"
    with open(model_bim_path, "r", encoding="utf-8") as f:
        bim = json.load(f)

    assert bim.get("compatibilityLevel") == 1606

    bad_bim = json.loads(json.dumps(bim))
    bad_bim["compatibilityLevel"] = 1567
    try:
        with open(model_bim_path, "w", encoding="utf-8") as f:
            json.dump(bad_bim, f, indent=2)

        with pytest.raises(ValueError, match="Invalid compatibilityLevel '1567' in model.bim"):
            validate_pbip_project_schema()
    finally:
        with open(model_bim_path, "w", encoding="utf-8") as f:
            json.dump(bim, f, indent=2)

    assert validate_pbip_project_schema() is True
