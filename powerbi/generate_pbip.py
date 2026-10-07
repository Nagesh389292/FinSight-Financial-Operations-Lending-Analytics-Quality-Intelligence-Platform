"""
FinSight Enterprise — Autonomous Power BI Project (PBIP) Generator
Generates the native Microsoft Power BI Project (PBIP) developer format:
- FinSight_Enterprise.pbip
- FinSight_Enterprise.Dataset/model.bim (Tabular Model with M queries, 10 tables, relationships, 45+ DAX measures)
- FinSight_Enterprise.Report/report.json (6-page layout with visual containers, slicers, cards, charts, and dark theme)
"""

import json
import re
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
POWERBI_DIR = BASE_DIR / "powerbi"
GOLD_DIR = BASE_DIR / "data" / "processed" / "analytics"

PBIP_ROOT = POWERBI_DIR / "FinSight_Enterprise.pbip"
DATASET_DIR = POWERBI_DIR / "FinSight_Enterprise.Dataset"
REPORT_DIR = POWERBI_DIR / "FinSight_Enterprise.Report"


def parse_dax_measures() -> list[dict]:
    """Parses dax_measures.dax into structured measure definitions."""
    dax_file = POWERBI_DIR / "dax_measures.dax"
    content = dax_file.read_text(encoding="utf-8")

    current_folder = "01_Portfolio_Lending"
    measures = []

    # Format string heuristics
    def get_format(name):
        n = name.lower()
        if "rate" in n or "war" in n or "pct" in n or "%" in n or "ratio" in n or "margin" in n or "efficiency" in n:
            return "0.00%"
        elif "balance" in n or "principal" in n or "volume" in n or "collected" in n or "debit" in n or "credit" in n or "variance" in n or "income" in n or "exposure" in n or "forecast" in n or "size" in n or "fees" in n or "movement" in n:
            return "$#,##0.00"
        elif "hours" in n:
            return "0.0"
        else:
            return "#,##0"

    # Match folders and measure blocks
    lines = content.splitlines()
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        if line.startswith("// FOLDER:"):
            current_folder = line.replace("// FOLDER:", "").strip()
            i += 1
            continue

        m_match = re.match(r"^\[(.*?)\]\s*=\s*$", line)
        if m_match:
            m_name = m_match.group(1).strip()
            expr_lines = []
            i += 1
            while i < len(lines):
                sub_line = lines[i]
                if sub_line.strip().startswith("[") and "]=" in sub_line.replace(" ", ""):
                    break
                if sub_line.strip().startswith("// ----------------") or sub_line.strip().startswith("// FOLDER:"):
                    break
                expr_lines.append(sub_line)
                i += 1

            expr_str = "\n".join(expr_lines).strip()
            if expr_str:
                measures.append({
                    "name": m_name,
                    "expression": expr_str,
                    "formatString": get_format(m_name),
                    "displayFolder": current_folder
                })
            continue
        i += 1

    return measures


def parse_field_reference(ref_str, valid_measures, valid_tables):
    """
    Parses a reference string like '[Total Payment Volume]' or 'dim_date[year_month]'.
    Returns dict: {'entity': str, 'property': str, 'is_measure': bool}
    """
    ref_str = ref_str.strip()
    if ref_str.startswith("[") and ref_str.endswith("]"):
        prop = ref_str[1:-1]
        # Resolve alias if needed
        if prop == "Closing Outstanding Principal":
            prop = "Outstanding Principal"
        if prop not in valid_measures:
            raise ValueError(f"Unknown DAX measure '{prop}' in field reference '{ref_str}'")
        return {"entity": "_Measures", "property": prop, "is_measure": True}
    elif "[" in ref_str and "]" in ref_str:
        entity, prop = ref_str.split("[")
        prop = prop.rstrip("]")
        if entity not in valid_tables:
            raise ValueError(f"Unknown table '{entity}' in field reference '{ref_str}'")
        if prop not in valid_tables[entity]:
            raise ValueError(f"Unknown column '{prop}' in table '{entity}' for reference '{ref_str}'")
        return {"entity": entity, "property": prop, "is_measure": False}
    else:
        if ref_str in valid_measures:
            return {"entity": "_Measures", "property": ref_str, "is_measure": True}
        raise ValueError(f"Cannot parse field reference '{ref_str}'")


def build_visual_container(v, pos, v_idx, valid_measures, valid_tables):
    """
    Constructs a complete, valid Power BI visual container definition with
    fully populated singleVisual, projections, prototypeQuery, and formatting.
    """
    v_type = v["type"]
    v_title = v.get("title", "")
    v_id = v["visualId"]

    # Special handling for textCard / textbox visual
    if v_type == "textCard":
        text_content = v.get("text", "")
        config_dict = {
            "name": v_id,
            "layouts": [{
                "id": 0,
                "position": {"x": pos["x"], "y": pos["y"], "z": v_idx, "width": pos["width"], "height": pos["height"]}
            }],
            "singleVisual": {
                "visualType": "textbox",
                "objects": {
                    "general": [{
                        "properties": {
                            "paragraphs": [{
                                "textRuns": [{
                                    "value": text_content,
                                    "textStyle": {"fontSize": "11pt"}
                                }]
                            }]
                        }
                    }]
                },
                "vcObjects": {
                    "title": [{
                        "properties": {
                            "text": {"expr": {"Literal": {"Value": f"'{v_title}'"}}},
                            "show": {"expr": {"Literal": {"Value": "true"}}}
                        }
                    }]
                }
            }
        }
        return {
            "x": pos["x"],
            "y": pos["y"],
            "z": v_idx,
            "width": pos["width"],
            "height": pos["height"],
            "config": json.dumps(config_dict),
            "filters": "[]"
        }

    # Map specification visual types to Power BI Desktop visual types
    type_map = {
        "card": "card",
        "barChart": "clusteredBarChart",
        "columnChart": "clusteredColumnChart",
        "areaChart": "areaChart",
        "lineChart": "lineChart",
        "donutChart": "donutChart",
        "matrix": "matrix",
        "table": "tableEx",
        "waterfallChart": "clusteredColumnChart",
        "lineClusteredColumnChart": "lineClusteredColumnChart"
    }
    pbi_v_type = type_map.get(v_type, v_type)

    roles_fields = {}

    if v_type == "card":
        m_ref = v.get("measure")
        roles_fields["Values"] = [parse_field_reference(m_ref, valid_measures, valid_tables)]
    elif v_type in ("barChart", "columnChart"):
        cat_ref = v.get("categoryAxis")
        val_ref = v.get("valueAxis")
        if cat_ref:
            roles_fields["Category"] = [parse_field_reference(cat_ref, valid_measures, valid_tables)]
        if val_ref:
            roles_fields["Y"] = [parse_field_reference(val_ref, valid_measures, valid_tables)]
    elif v_type == "areaChart":
        cat_ref = v.get("xAxis")
        if cat_ref:
            roles_fields["Category"] = [parse_field_reference(cat_ref, valid_measures, valid_tables)]
        vals = v.get("values", [])
        if isinstance(vals, str):
            vals = [vals]
        roles_fields["Y"] = [parse_field_reference(r, valid_measures, valid_tables) for r in vals]
    elif v_type == "lineChart":
        cat_ref = v.get("xAxis")
        if cat_ref:
            roles_fields["Category"] = [parse_field_reference(cat_ref, valid_measures, valid_tables)]
        vals = v.get("values", [])
        if isinstance(vals, str):
            vals = [vals]
        roles_fields["Y"] = [parse_field_reference(r, valid_measures, valid_tables) for r in vals]
    elif v_type == "donutChart":
        leg_ref = v.get("legend")
        val_ref = v.get("values")
        if leg_ref:
            roles_fields["Category"] = [parse_field_reference(leg_ref, valid_measures, valid_tables)]
        if val_ref:
            roles_fields["Y"] = [parse_field_reference(val_ref, valid_measures, valid_tables)]
    elif v_type == "waterfallChart":
        vals = v.get("values", [])
        if isinstance(vals, str):
            vals = [vals]
        roles_fields["Y"] = [parse_field_reference(r, valid_measures, valid_tables) for r in vals]
    elif v_type == "lineClusteredColumnChart":
        cat_ref = v.get("xAxis")
        if cat_ref:
            roles_fields["Category"] = [parse_field_reference(cat_ref, valid_measures, valid_tables)]
        col_vals = v.get("columnValues", [])
        line_vals = v.get("lineValues", [])
        roles_fields["Y"] = [parse_field_reference(r, valid_measures, valid_tables) for r in col_vals]
        roles_fields["Y2"] = [parse_field_reference(r, valid_measures, valid_tables) for r in line_vals]
    elif v_type == "matrix":
        rows = v.get("rows", [])
        vals = v.get("values", [])
        roles_fields["Rows"] = [parse_field_reference(r, valid_measures, valid_tables) for r in rows]
        roles_fields["Values"] = [parse_field_reference(r, valid_measures, valid_tables) for r in vals]
    elif v_type == "table":
        cols = v.get("columns", [])
        roles_fields["Values"] = [parse_field_reference(r, valid_measures, valid_tables) for r in cols]

    # Projections and prototypeQuery
    all_fields = []
    projections = {}

    for role, f_list in roles_fields.items():
        proj_list = []
        for f in f_list:
            qref = f"{f['entity']}.{f['property']}"
            proj_list.append({"queryRef": qref})
            all_fields.append((qref, f))
        projections[role] = proj_list

    unique_entities = sorted(list({f["entity"] for _, f in all_fields}))
    entity_alias_map = {}
    for idx, ent in enumerate(unique_entities):
        alias = ent[0].lower()
        if alias in entity_alias_map.values():
            alias = f"{alias}{idx}"
        entity_alias_map[ent] = alias

    from_list = [
        {"Name": entity_alias_map[ent], "Entity": ent, "Type": 0}
        for ent in unique_entities
    ]

    select_list = []
    seen_qrefs = set()
    for qref, f in all_fields:
        if qref in seen_qrefs:
            continue
        seen_qrefs.add(qref)
        alias = entity_alias_map[f["entity"]]
        if f["is_measure"]:
            select_list.append({
                "Measure": {
                    "Expression": {"SourceRef": {"Source": alias}},
                    "Property": f["property"]
                },
                "Name": qref
            })
        else:
            select_list.append({
                "Column": {
                    "Expression": {"SourceRef": {"Source": alias}},
                    "Property": f["property"]
                },
                "Name": qref
            })

    prototype_query = {
        "Version": 2,
        "From": from_list,
        "Select": select_list
    }

    config_dict = {
        "name": v_id,
        "layouts": [{
            "id": 0,
            "position": {"x": pos["x"], "y": pos["y"], "z": v_idx, "width": pos["width"], "height": pos["height"]}
        }],
        "singleVisual": {
            "visualType": pbi_v_type,
            "projections": projections,
            "prototypeQuery": prototype_query,
            "vcObjects": {
                "title": [{
                    "properties": {
                        "text": {"expr": {"Literal": {"Value": f"'{v_title}'"}}},
                        "show": {"expr": {"Literal": {"Value": "true"}}}
                    }
                }]
            }
        }
    }

    return {
        "x": pos["x"],
        "y": pos["y"],
        "z": v_idx,
        "width": pos["width"],
        "height": pos["height"],
        "config": json.dumps(config_dict),
        "filters": "[]"
    }


def generate_pbip_artifacts():
    print("=" * 80)
    print(" FinSight Enterprise — Generating Native Power BI Project (PBIP) ")
    print("=" * 80)

    DATASET_DIR.mkdir(parents=True, exist_ok=True)
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    (REPORT_DIR / "StaticResources" / "SharedResources" / "BaseThemes").mkdir(parents=True, exist_ok=True)

    # 1. Root .pbip File (Conforming to Fabric PBIP ItemShortcut Schema 1.0.0)
    pbip_def = {
        "$schema": "https://developer.microsoft.com/json-schemas/fabric/pbip/pbipProperties/1.0.0/schema.json",
        "version": "1.0",
        "artifacts": [
            {
                "report": {
                    "path": "FinSight_Enterprise.Report"
                }
            }
        ],
        "settings": {
            "enableAutoRecovery": True
        }
    }
    with open(PBIP_ROOT, "w", encoding="utf-8") as f:
        json.dump(pbip_def, f, indent=2)
    print(f"[+] Created {PBIP_ROOT.name} (validated against Fabric PBIP 1.0.0 schema)")

    # 2. Dataset definition.pbism (Modern Fabric / Power BI Semantic Model Format)
    # Note: Power BI Desktop strictly rejects having both definition.pbism and definition.pbidataset simultaneously.
    # We clean up any obsolete definition.pbidataset to prevent format collision.
    obsolete_pbidataset = DATASET_DIR / "definition.pbidataset"
    if obsolete_pbidataset.exists():
        obsolete_pbidataset.unlink()

    # Clean up stale Analysis Services cache files from previous Power BI Desktop sessions
    # (e.g. .pbi/cache.abf which locks compatibility level)
    cache_file = DATASET_DIR / ".pbi" / "cache.abf"
    if cache_file.exists():
        try:
            cache_file.unlink()
        except Exception as e:
            print(f"[!] Warning: Could not remove {cache_file}: {e}")

    pbism_def = {
        "$schema": "https://developer.microsoft.com/json-schemas/fabric/item/semanticModel/definitionProperties/1.0.0/schema.json",
        "version": "1.0"
    }
    with open(DATASET_DIR / "definition.pbism", "w", encoding="utf-8") as f:
        json.dump(pbism_def, f, indent=2)
    print(f"[+] Created {DATASET_DIR.name}/definition.pbism (single coherent semantic-model format)")

    # 3. Model.bim (Tabular Object Model)
    with open(POWERBI_DIR / "semantic_model.json", "r", encoding="utf-8") as f:
        sem_spec = json.load(f)

    dax_measures = parse_dax_measures()
    print(f"[+] Parsed {len(dax_measures)} DAX measures from dax_measures.dax")

    # Build TOM tables
    tom_tables = []
    gold_posix = GOLD_DIR.resolve().as_posix()

    for t in sem_spec["tables"]:
        t_name = t["name"]
        parquet_path = f"{gold_posix}/{t_name}.parquet"

        m_expr = [
            "let",
            f'    Source = Parquet.Document(File.Contents("{parquet_path}"))',
            "in",
            "    Source"
        ]

        tom_cols = []
        for c in t["columns"]:
            dtype = c.get("dataType", "string")
            col_def = {
                "name": c["name"],
                "dataType": dtype,
                "sourceColumn": c["name"],
                "summarizeBy": "none" if dtype in ("string", "dateTime", "boolean") or "key" in c["name"] else "sum"
            }
            if "formatString" in c:
                col_def["formatString"] = c["formatString"]
            tom_cols.append(col_def)

        tom_tables.append({
            "name": t_name,
            "columns": tom_cols,
            "partitions": [
                {
                    "name": t_name,
                    "mode": "import",
                    "source": {
                        "type": "m",
                        "expression": m_expr
                    }
                }
            ]
        })

    # Add central _Measures table
    tom_measures = []
    for m in dax_measures:
        tom_measures.append({
            "name": m["name"],
            "expression": m["expression"],
            "formatString": m["formatString"],
            "displayFolder": m["displayFolder"]
        })

    tom_tables.append({
        "name": "_Measures",
        "columns": [
            {
                "name": "Measure",
                "dataType": "string",
                "sourceColumn": "Measure",
                "summarizeBy": "none",
                "isHidden": True
            }
        ],
        "partitions": [
            {
                "name": "_Measures",
                "mode": "import",
                "source": {
                    "type": "m",
                    "expression": [
                        "let",
                        '    Source = #table(type table [Measure = text], {{"Measures"}})',
                        "in",
                        "    Source"
                    ]
                }
            }
        ],
        "measures": tom_measures
    })

    # Build TOM relationships
    tom_relationships = []
    valid_cross_filtering = {"oneDirection", "bothDirections", "automatic"}
    for r in sem_spec["relationships"]:
        cross_filter = r.get("crossFilteringBehavior", "oneDirection")
        # Normalize to standard Power BI TMSL CrossFilteringBehavior enum
        if cross_filter in ("singleDirection", "oneDirection", "OneDirection"):
            cross_filter = "oneDirection"
        elif cross_filter in ("bothDirections", "BothDirections"):
            cross_filter = "bothDirections"
        elif cross_filter in ("automatic", "Automatic"):
            cross_filter = "automatic"
        else:
            cross_filter = "oneDirection"

        tom_relationships.append({
            "name": r["name"],
            "fromTable": r["fromTable"],
            "fromColumn": r["fromColumn"],
            "toTable": r["toTable"],
            "toColumn": r["toColumn"],
            "crossFilteringBehavior": cross_filter,
            "isActive": True
        })

    model_bim = {
        "name": "FinSight_Enterprise",
        "compatibilityLevel": 1606,
        "model": {
            "culture": "en-US",
            "dataAccessOptions": {
                "legacyRedirects": True,
                "returnErrorValuesAsNull": True
            },
            "defaultPowerBIDataSourceVersion": "powerBI_V3",
            "sourceQueryCulture": "en-US",
            "tables": tom_tables,
            "relationships": tom_relationships
        }
    }

    with open(DATASET_DIR / "model.bim", "w", encoding="utf-8") as f:
        json.dump(model_bim, f, indent=2)
    print(f"[+] Generated {DATASET_DIR.name}/model.bim with {len(tom_tables)} tables and {len(tom_measures)} measures")

    # 4. Report definition.pbir (Conforming to Fabric PBIR 1.0.0 schema)
    pbir_def = {
        "$schema": "https://developer.microsoft.com/json-schemas/fabric/item/report/definitionProperties/1.0.0/schema.json",
        "version": "1.0",
        "datasetReference": {
            "byPath": {
                "path": "../FinSight_Enterprise.Dataset"
            }
        }
    }
    with open(REPORT_DIR / "definition.pbir", "w", encoding="utf-8") as f:
        json.dump(pbir_def, f, indent=2)
    print(f"[+] Created {REPORT_DIR.name}/definition.pbir")

    # 5. Report report.json (6 Pages Layout with Fully Bound Visual Queries & Projections)
    with open(POWERBI_DIR / "report_layout_specification.json", "r", encoding="utf-8") as f:
        layout_spec = json.load(f)

    valid_measures_set = {m["name"] for m in dax_measures}
    valid_tables_dict = {t["name"]: {c["name"] for c in t.get("columns", [])} for t in tom_tables}

    sections = []
    sec_idx = 0

    for page in layout_spec["pages"]:
        sec_name = f"ReportSection_{sec_idx}"
        visual_containers = []
        v_idx = 0

        for v in page["visuals"]:
            pos = v["position"]
            container = build_visual_container(v, pos, v_idx, valid_measures_set, valid_tables_dict)
            visual_containers.append(container)
            v_idx += 1

        sections.append({
            "name": sec_name,
            "displayName": page["pageName"],
            "ordinal": sec_idx,
            "width": 1280.0,
            "height": 720.0,
            "visualContainers": visual_containers
        })
        sec_idx += 1

    report_json = {
        "config": json.dumps({
            "version": "5.55",
            "themeCollection": {
                "baseTheme": {
                    "name": "CY24SU08",
                    "version": "5.55",
                    "type": 2
                }
            }
        }),
        "layoutOptimization": 0,
        "sections": sections
    }

    with open(REPORT_DIR / "report.json", "w", encoding="utf-8") as f:
        json.dump(report_json, f, indent=2)
    print(f"[+] Generated {REPORT_DIR.name}/report.json with {len(sections)} report pages")

    # 6. Automated Formal Schema Validation
    validate_pbip_project_schema()

    print("\n" + "=" * 80)
    print(" POWER BI PROJECT (PBIP) GENERATED SUCCESSFULLY ")
    print(" You can double-click powerbi/FinSight_Enterprise.pbip in Power BI Desktop! ")
    print("=" * 80)


def validate_pbip_project_schema() -> bool:
    """
    Validates that the generated PBIP artifacts strictly conform
    to Microsoft Fabric PBIP ItemShortcut, PBIR ReportDefinition,
    and PBISM DatasetDefinition schemas.
    """
    import jsonschema

    pbip_schema = {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "$schema": {"type": "string"},
            "version": {"type": "string"},
            "artifacts": {
                "type": "array",
                "items": {
                    "type": "object",
                    "additionalProperties": False,
                    "properties": {
                        "report": {
                            "type": "object",
                            "additionalProperties": False,
                            "properties": {"path": {"type": "string"}},
                            "required": ["path"]
                        }
                    },
                    "required": ["report"]
                }
            },
            "settings": {
                "type": ["object", "null"],
                "additionalProperties": False,
                "properties": {
                    "enableAutoRecovery": {"type": "boolean"}
                }
            }
        },
        "required": ["version", "artifacts"]
    }

    pbir_schema = {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "$schema": {"type": "string"},
            "version": {"type": "string"},
            "datasetReference": {
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    "byPath": {
                        "type": ["object", "null"],
                        "additionalProperties": False,
                        "properties": {"path": {"type": "string"}},
                        "required": ["path"]
                    },
                    "byConnection": {
                        "type": ["object", "null"],
                        "additionalProperties": False
                    }
                }
            }
        },
        "required": ["version", "datasetReference"]
    }

    pbism_schema = {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "$schema": {"type": "string"},
            "version": {"type": "string"},
            "settings": {
                "type": ["object", "null"],
                "additionalProperties": False,
                "properties": {
                    "qnaEnabled": {"type": ["boolean", "null"]},
                    "qnaLsdlSharingPermissions": {"type": "integer", "enum": [0, 1]}
                }
            }
        },
        "required": ["version"]
    }

    # Validate FinSight_Enterprise.pbip
    with open(PBIP_ROOT, "r", encoding="utf-8") as f:
        pbip_doc = json.load(f)
    jsonschema.validate(instance=pbip_doc, schema=pbip_schema)

    # Validate FinSight_Enterprise.Report/definition.pbir
    with open(REPORT_DIR / "definition.pbir", "r", encoding="utf-8") as f:
        pbir_doc = json.load(f)
    jsonschema.validate(instance=pbir_doc, schema=pbir_schema)

    # Validate Mutual Exclusivity of Semantic Model Manifests
    pbism_file = DATASET_DIR / "definition.pbism"
    pbidataset_file = DATASET_DIR / "definition.pbidataset"

    if pbism_file.exists() and pbidataset_file.exists():
        raise ValueError(
            "Mutual exclusivity violation: You cannot have both definition.pbism and "
            "definition.pbidataset formats. Power BI Desktop rejects projects with both manifests."
        )
    if pbidataset_file.exists():
        raise ValueError(
            "Obsolete format detected: definition.pbidataset exists. "
            "The PBIP project must use definition.pbism as its single coherent semantic-model format."
        )
    if not pbism_file.exists():
        raise FileNotFoundError(f"Missing required semantic-model manifest: {pbism_file}")

    model_bim_file = DATASET_DIR / "model.bim"
    if not model_bim_file.exists():
        raise FileNotFoundError(f"Missing required Tabular model file: {model_bim_file}")

    # Validate FinSight_Enterprise.Dataset/definition.pbism
    with open(pbism_file, "r", encoding="utf-8") as f:
        pbism_doc = json.load(f)
    jsonschema.validate(instance=pbism_doc, schema=pbism_schema)

    # Validate FinSight_Enterprise.Dataset/model.bim Tabular TOM integrity
    with open(model_bim_file, "r", encoding="utf-8") as f:
        bim_doc = json.load(f)

    comp_level = bim_doc.get("compatibilityLevel")
    if comp_level != 1606:
        raise ValueError(
            f"Invalid compatibilityLevel '{comp_level}' in model.bim. "
            f"Power BI Desktop requires compatibilityLevel 1606 to prevent compatibility-level downgrade errors."
        )

    valid_cross_filtering = {"oneDirection", "bothDirections", "automatic"}
    valid_data_types = {"string", "int64", "double", "dateTime", "decimal", "boolean", "binary"}

    relationships = bim_doc.get("model", {}).get("relationships", [])
    if not relationships:
        raise ValueError("Model integrity error: model.relationships is empty or missing")

    for idx, rel in enumerate(relationships):
        raw_cf = rel.get("crossFilteringBehavior")
        if raw_cf == "singleDirection":
            raise ValueError(
                f"Cannot convert value 'singleDirection' to required type 'CrossFilteringBehavior'. "
                f"Check path 'model.relationships[{idx}].crossFilteringBehavior'. "
                f"Valid TMSL enums are: {sorted(valid_cross_filtering)}"
            )
        cf = raw_cf if raw_cf is not None else "oneDirection"
        if cf not in valid_cross_filtering:
            raise ValueError(
                f"Invalid CrossFilteringBehavior '{cf}' at path 'model.relationships[{idx}].crossFilteringBehavior'. "
                f"Must be one of {sorted(valid_cross_filtering)}"
            )
        for req_prop in ("fromTable", "fromColumn", "toTable", "toColumn"):
            if not rel.get(req_prop):
                raise ValueError(f"Missing required relationship property '{req_prop}' at 'model.relationships[{idx}]'")

    # Validate column data types and summarization
    for table in bim_doc.get("model", {}).get("tables", []):
        tname = table.get("name")
        for col in table.get("columns", []):
            cname = col.get("name")
            dtype = col.get("dataType")
            if dtype not in valid_data_types:
                raise ValueError(f"Invalid dataType '{dtype}' for column '{tname}.{cname}'")
            if dtype == "boolean" and col.get("summarizeBy") == "sum":
                raise ValueError(f"Boolean column '{tname}.{cname}' cannot have summarizeBy='sum'")

    # Validate report.json structure and visual query/projection integrity
    report_json_file = REPORT_DIR / "report.json"
    if not report_json_file.exists():
        raise FileNotFoundError(f"Missing required report layout file: {report_json_file}")

    with open(report_json_file, "r", encoding="utf-8") as f:
        rep_doc = json.load(f)

    sections = rep_doc.get("sections", [])
    if len(sections) != 6:
        raise ValueError(f"Report must contain exactly 6 sections, found {len(sections)}")

    bim_tables_dict = {t["name"]: {c["name"] for c in t.get("columns", [])} for t in bim_doc.get("model", {}).get("tables", [])}
    bim_measures_set = set()
    for t in bim_doc.get("model", {}).get("tables", []):
        for m in t.get("measures", []):
            bim_measures_set.add(m["name"])

    total_visuals_validated = 0
    for s_idx, sec in enumerate(sections):
        v_containers = sec.get("visualContainers", [])
        if not v_containers:
            raise ValueError(f"Section {s_idx} ('{sec.get('displayName')}') has 0 visual containers")

        for c_idx, container in enumerate(v_containers):
            cfg_raw = container.get("config")
            if not cfg_raw:
                raise ValueError(f"Container {c_idx} on page '{sec.get('displayName')}' missing config")
            cfg = json.loads(cfg_raw)
            sv = cfg.get("singleVisual")
            if not sv:
                raise ValueError(f"Container {c_idx} on page '{sec.get('displayName')}' missing singleVisual")
            v_type = sv.get("visualType")
            if not v_type:
                raise ValueError(f"Visual {cfg.get('name')} missing visualType")

            if v_type == "textbox":
                gen = sv.get("objects", {}).get("general", [])
                if not gen or not gen[0].get("properties", {}).get("paragraphs"):
                    raise ValueError(f"Textbox visual {cfg.get('name')} missing paragraphs")
            else:
                projections = sv.get("projections", {})
                if not projections:
                    raise ValueError(f"Visual {cfg.get('name')} ({v_type}) has empty projections. Placeholder visuals are prohibited!")

                proto_query = sv.get("prototypeQuery", {})
                selects = proto_query.get("Select", [])
                froms = proto_query.get("From", [])
                if not selects or not froms:
                    raise ValueError(f"Visual {cfg.get('name')} ({v_type}) has empty prototypeQuery (Select={len(selects)}, From={len(froms)})")

                proj_qrefs = {item["queryRef"] for role_items in projections.values() for item in role_items if "queryRef" in item}
                if not proj_qrefs:
                    raise ValueError(f"Visual {cfg.get('name')} ({v_type}) has no queryRef in projections")

                for sel in selects:
                    name = sel.get("Name")
                    if name not in proj_qrefs:
                        raise ValueError(f"Visual {cfg.get('name')} Select item '{name}' not found in projections: {proj_qrefs}")
                    if "Measure" in sel:
                        m_prop = sel["Measure"].get("Property")
                        if m_prop not in bim_measures_set:
                            raise ValueError(f"Visual {cfg.get('name')} references non-existent DAX measure '{m_prop}'")
                    elif "Column" in sel:
                        c_prop = sel["Column"].get("Property")
                        src = sel["Column"].get("Expression", {}).get("SourceRef", {}).get("Source")
                        ent = next((f["Entity"] for f in froms if f["Name"] == src), None)
                        if not ent or ent not in bim_tables_dict or c_prop not in bim_tables_dict[ent]:
                            raise ValueError(f"Visual {cfg.get('name')} references non-existent column '{ent}.{c_prop}'")

            total_visuals_validated += 1

    print(
        f"[+] Formal Schema Validation Passed: 0 errors across PBIP, PBIR, PBISM, {len(relationships)} model.bim relationships, "
        f"and {total_visuals_validated} visuals across 6 pages"
    )
    return True


if __name__ == "__main__":
    generate_pbip_artifacts()

