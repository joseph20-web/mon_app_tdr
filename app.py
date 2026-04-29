import io
import re
import sqlite3
from datetime import datetime
from typing import Dict, List, Tuple

import pandas as pd
import streamlit as st

DB_PATH = "tdr_payroll.db"
DEFAULT_FIXED_SALARY = 75.0

KPI_DEFINITIONS = [
    {
        "code": "KPI1_NEW_ACTIVE_AGENTS",
        "label": "New Active Agents (20%)",
        "column": "NEW Agent Active",
        "weight": 20,
        "rates": [0.05, 0.07, 0.08, 0.10],
    },
    {
        "code": "KPI2_MAINTAIN_ACTIVE_BASE",
        "label": "Maintain Existing Base Active Agent (20%)",
        "column": "Active M-pesa Agent",
        "weight": 20,
        "rates": [0.05, 0.07, 0.08, 0.10],
    },
    {
        "code": "KPI3_QUALITY_ACQUISITION",
        "label": "Quality M-pesa client Acquisition (15%)",
        "column": "Achiev. Quality Acquisition",
        "weight": 15,
        "rates": [0.09, 0.15, 0.21, 0.25],
    },
    {
        "code": "KPI4_AGENT_DOING_ACQUISITION",
        "label": "Agent doing M-pesa client Acquisition (15%)",
        "column": "Actives Agents Doing quality Acquisitions",
        "weight": 15,
        "rates": [0.20, 0.27, 0.32, 0.40],
    },
    {
        "code": "KPI5_CASH_IN",
        "label": "Cash In (10%)",
        "column": "Cash in",
        "weight": 10,
        "rates": [0.000007, 0.000011, 0.000016, 0.000022],
    },
    {
        "code": "KPI6_DMS",
        "label": "DMS (5%)",
        "column": "DMS",
        "weight": 5,
        "rates": [0.04, 0.05, 0.06, 0.07],
    },
    {
        "code": "KPI7_FORMATION_AML",
        "label": "Formation AML (5%)",
        "column": "Formation AML",
        "weight": 5,
        "rates": [0.09, 0.12, 0.17, 0.19],
    },
]

KPI_DISPLAY_ORDER = [
    ("KPI1_NEW_ACTIVE_AGENTS", "New Active Agents"),
    ("KPI2_MAINTAIN_ACTIVE_BASE", "Maintain Base Active"),
    ("KPI3_QUALITY_ACQUISITION", "Quality Acquisition"),
    ("KPI4_AGENT_DOING_ACQUISITION", "Agents Doing Acquisition"),
    ("KPI5_CASH_IN", "Cash In"),
    ("KPI6_DMS", "DMS"),
    ("KPI7_FORMATION_AML", "Formation AML"),
]

BANDS = [
    {"label": "0-60", "min": 0, "max": 60},
    {"label": "61-80", "min": 61, "max": 80},
    {"label": "81-100", "min": 81, "max": 100},
    {"label": ">100", "min": 100.000001, "max": None},
]

REQUIRED_COLUMNS = [
    "REGION",
    "POOL",
    "SUPERVISOR_NAME",
    "TDR_NAMES",
    "TDR_TEL",
    "Achiev. Quality Acquisition",
    "Actives Agents Doing quality Acquisitions",
    "Active M-pesa Agent",
    "Cash in",
    "Formation AML",
    "DMS",
    "NEW Agent Active",
]
AGENT_REQUIRED_COLUMNS = [
    "REGION",
    "POOL",
    "SUPERVISOR_NAME",
    "TDR_NAMES",
    "TDR_TEL",
]

COLUMN_ALIASES_TARGET = {
    "TDR_TEL": ["tdr_tel", "tdr_phone", "telephone", "phone", "new_tdr_tel"],
    "Achiev. Quality Acquisition": [
        "target_achiev_quality_acquisition",
        "target_quality_acquisition",
        "quality_acquisition_target",
        "quality_m_pesa_client_acquisition",
        "kpi3",
    ],
    "Actives Agents Doing quality Acquisitions": [
        "target_actives_agents_doing_quality_acquisitions",
        "target_active_agents_doing_quality_acquisitions",
        "agents_doing_quality_acquisitions_target",
        "agent_doing_m_pesa_client_acquisition",
        "kpi4",
    ],
    "Active M-pesa Agent": [
        "target_active_m_pesa_agent",
        "target_active_mpesa_agent",
        "active_mpesa_agent_target",
        "maintain_existing_base_active_agent",
        "maintain_base_active",
        "kpi2",
    ],
    "Cash in": ["target_cash_in", "cash_in_target", "target_cashin", "kpi5"],
    "Formation AML": ["target_formation_aml", "formation_aml_target", "kpi7"],
    "DMS": ["target_dms", "dms_target", "kpi6"],
    "NEW Agent Active": [
        "target_new_agent_active",
        "new_agent_active_target",
        "new_active_agents",
        "kpi1",
    ],
}

COLUMN_ALIASES = {
    "REGION": ["region"],
    "POOL": ["pool"],
    "SUPERVISOR_NAME": ["supervisor_name", "supervisor", "supervisorname"],
    "TDR_NAMES": ["tdr_names", "tdr_name", "tdr", "agent_name", "nom_agent"],
    "TDR_TEL": ["tdr_tel", "tdr_phone", "telephone", "phone", "tdr_number"],
    "Achiev. Quality Acquisition": [
        "achiev_quality_acquisition",
        "achievqualityacquisition",
        "quality_acquisition",
    ],
    "Actives Agents Doing quality Acquisitions": [
        "actives_agents_doing_quality_acquisitions",
        "active_agents_doing_quality_acquisitions",
        "agents_doing_quality_acquisitions",
    ],
    "Achiev.Inflow": ["achiev_inflow", "achievinflow", "inflow"],
    "Active M-pesa Agent": [
        "active_m_pesa_agent",
        "active_mpesa_agent",
        "mpesa_active_agent",
        "maintain_base_active",
        "maintain_existing_base_active_agent",
    ],
    "Cash in": ["cash_in", "cashin"],
    "Formation AML": ["formation_aml", "aml_formation", "aml_training"],
    "DMS": ["dms"],
    "NEW Agent Active": ["new_agent_active", "new_active_agent"],
}


def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def init_db(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS agents (
            telephone TEXT PRIMARY KEY,
            nom TEXT NOT NULL,
            region TEXT,
            pool TEXT,
            supervisor TEXT,
            salaire_fixe REAL NOT NULL DEFAULT 75,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS commissions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            kpi_code TEXT NOT NULL,
            kpi_label TEXT NOT NULL,
            band_label TEXT NOT NULL,
            min_value REAL NOT NULL,
            max_value REAL,
            rate REAL NOT NULL,
            UNIQUE(kpi_code, band_label)
        );

        CREATE TABLE IF NOT EXISTS performances (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            month TEXT NOT NULL,
            telephone TEXT NOT NULL,
            nom TEXT NOT NULL,
            region TEXT,
            pool TEXT,
            supervisor TEXT,
            achiev_quality_acquisition REAL DEFAULT 0,
            active_agents_quality_acq REAL DEFAULT 0,
            achiev_inflow REAL DEFAULT 0,
            active_mpesa_agent REAL DEFAULT 0,
            cash_in REAL DEFAULT 0,
            formation_aml REAL DEFAULT 0,
            dms REAL DEFAULT 0,
            new_agent_active REAL DEFAULT 0,
            kpi1_prime REAL DEFAULT 0,
            kpi2_prime REAL DEFAULT 0,
            kpi3_prime REAL DEFAULT 0,
            kpi4_prime REAL DEFAULT 0,
            kpi5_prime REAL DEFAULT 0,
            kpi6_prime REAL DEFAULT 0,
            kpi7_prime REAL DEFAULT 0,
            variable_total REAL DEFAULT 0,
            salaire_fixe REAL DEFAULT 75,
            salaire_total REAL DEFAULT 0,
            imported_at TEXT DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(month, telephone)
        );
        """
    )
    conn.commit()
    seed_default_commissions(conn)


def seed_default_commissions(conn: sqlite3.Connection) -> None:
    count = conn.execute("SELECT COUNT(*) AS c FROM commissions").fetchone()["c"]
    if count > 0:
        return
    for kpi in KPI_DEFINITIONS:
        for idx, band in enumerate(BANDS):
            conn.execute(
                """
                INSERT INTO commissions (kpi_code, kpi_label, band_label, min_value, max_value, rate)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    kpi["code"],
                    kpi["label"],
                    band["label"],
                    band["min"],
                    band["max"],
                    kpi["rates"][idx],
                ),
            )
    conn.commit()


def load_commissions(conn: sqlite3.Connection) -> Dict[str, List[sqlite3.Row]]:
    rows = conn.execute(
        "SELECT * FROM commissions ORDER BY kpi_code, min_value ASC"
    ).fetchall()
    grouped: Dict[str, List[sqlite3.Row]] = {}
    for row in rows:
        grouped.setdefault(row["kpi_code"], []).append(row)
    return grouped


def parse_phone(value) -> str:
    if pd.isna(value):
        return ""
    text = str(value).strip()
    if text.endswith(".0"):
        text = text[:-2]
    # Keep digits only to match Excel formats like +243..., 243..., 243... .0
    digits = "".join(ch for ch in text if ch.isdigit())
    return digits or text


def to_float(value) -> float:
    if pd.isna(value):
        return 0.0
    if isinstance(value, str):
        txt = value.strip()
        txt = txt.replace(" ", "")
        # Keep only numeric relevant chars (supports "6,53 €")
        txt = re.sub(r"[^0-9,.\-]", "", txt)
        if "," in txt and "." in txt:
            # Ex: 1,234.56 -> 1234.56
            txt = txt.replace(",", "")
        elif "," in txt and "." not in txt:
            # Ex: 6,53 -> 6.53
            txt = txt.replace(",", ".")
        value = txt
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def normalize_text(value: str) -> str:
    text = str(value).strip().lower()
    normalized_chars = []
    for ch in text:
        if ch.isalnum():
            normalized_chars.append(ch)
        else:
            normalized_chars.append("_")
    normalized = "".join(normalized_chars)
    while "__" in normalized:
        normalized = normalized.replace("__", "_")
    return normalized.strip("_")


def normalize_variants(value: str) -> List[str]:
    base = normalize_text(value)
    variants = {base}
    for prefix in ("new_", "sa_", "the_"):
        if base.startswith(prefix):
            variants.add(base[len(prefix) :])
    for suffix in ("_new", "_value", "_pct"):
        if base.endswith(suffix):
            variants.add(base[: -len(suffix)])
    variants.add(base.replace("mpesa", "m_pesa"))
    variants.add(base.replace("m_pesa", "mpesa"))
    return [v for v in variants if v]


def resolve_columns(df: pd.DataFrame) -> Dict[str, str]:
    normalized_columns = {normalize_text(col): col for col in df.columns}
    resolved: Dict[str, str] = {}

    for required in REQUIRED_COLUMNS:
        required_norm = normalize_text(required)
        alias_list = [required_norm] + COLUMN_ALIASES.get(required, [])
        found = None

        # 1) Exact normalized alias match
        for alias in alias_list:
            for variant in normalize_variants(alias):
                if variant in normalized_columns:
                    found = normalized_columns[variant]
                    break
            if found:
                break

        # 2) Partial token match for messy/truncated headers
        if not found:
            alias_tokens = []
            for alias in alias_list:
                alias_tokens.extend([t for t in normalize_text(alias).split("_") if len(t) > 2])
            alias_tokens = list(dict.fromkeys(alias_tokens))
            best_score = 0
            best_col = None
            for norm_col, original_col in normalized_columns.items():
                score = sum(1 for token in alias_tokens if token in norm_col)
                if score > best_score:
                    best_score = score
                    best_col = original_col
            # Need at least 2 matching tokens to avoid bad mapping.
            if best_score >= 2 and best_col not in resolved.values():
                found = best_col

        if found:
            resolved[required] = found
    return resolved


def resolve_target_columns(df: pd.DataFrame) -> Dict[str, str]:
    normalized_columns = {normalize_text(col): col for col in df.columns}
    resolved: Dict[str, str] = {}
    required_target_columns = ["TDR_TEL"] + [k["column"] for k in KPI_DEFINITIONS]

    for required in required_target_columns:
        required_norm = normalize_text(required)
        alias_list = [required_norm] + COLUMN_ALIASES_TARGET.get(required, [])
        found = None

        for alias in alias_list:
            for variant in normalize_variants(alias):
                if variant in normalized_columns:
                    found = normalized_columns[variant]
                    break
            if found:
                break

        if not found:
            tokens = [t for t in required_norm.split("_") if len(t) > 2]
            for norm_col, original_col in normalized_columns.items():
                token_hits = sum(1 for token in tokens if token in norm_col)
                has_target_hint = "target" in norm_col or "objectif" in norm_col
                if token_hits >= 2 and (required == "TDR_TEL" or has_target_hint):
                    found = original_col
                    break

        if found:
            resolved[required] = found

    return resolved


def read_evidence_file(uploaded_file) -> Tuple[pd.DataFrame, List[str]]:
    # Some evidence files have a title row before real headers.
    for header_row in range(0, 15):
        uploaded_file.seek(0)
        df = pd.read_excel(uploaded_file, engine="openpyxl", header=header_row)
        df.columns = [str(col).strip() for col in df.columns]
        mapping = resolve_columns(df)
        missing = [col for col in REQUIRED_COLUMNS if col not in mapping]
        if not missing:
            standardized_df = df.rename(columns={v: k for k, v in mapping.items()})
            return standardized_df, []

    return pd.DataFrame(), [col for col in REQUIRED_COLUMNS]


def read_agents_file(uploaded_file) -> Tuple[pd.DataFrame, List[str]]:
    for header_row in range(0, 20):
        uploaded_file.seek(0)
        df = pd.read_excel(uploaded_file, engine="openpyxl", header=header_row)
        df.columns = [str(col).strip() for col in df.columns]
        mapping = resolve_columns(df)
        missing = [col for col in AGENT_REQUIRED_COLUMNS if col not in mapping]
        if not missing:
            standardized_df = df.rename(columns={v: k for k, v in mapping.items()})
            return standardized_df, []
    return pd.DataFrame(), AGENT_REQUIRED_COLUMNS


def read_target_file(uploaded_file) -> Tuple[pd.DataFrame, List[str]]:
    required_target_columns = ["TDR_TEL"] + [k["column"] for k in KPI_DEFINITIONS]
    best_df = None
    best_mapping: Dict[str, str] = {}
    best_score = -1

    for header_row in range(0, 30):
        uploaded_file.seek(0)
        df = pd.read_excel(uploaded_file, engine="openpyxl", header=header_row)
        df.columns = [str(col).strip() for col in df.columns]
        mapping = resolve_target_columns(df)
        score = len(mapping)
        if score > best_score:
            best_score = score
            best_df = df
            best_mapping = mapping
        if score == len(required_target_columns):
            standardized_df = df.rename(columns={v: k for k, v in mapping.items()})
            return standardized_df, []

    if best_df is not None and "TDR_TEL" in best_mapping:
        # Accept partial mapping; missing KPI targets will be filled with 0.
        standardized_df = best_df.rename(columns={v: k for k, v in best_mapping.items()})
        for col in [k["column"] for k in KPI_DEFINITIONS]:
            if col not in standardized_df.columns:
                standardized_df[col] = 0
        return standardized_df, []

    return pd.DataFrame(), required_target_columns


def pick_rate(performance: float, bands: List[sqlite3.Row]) -> float:
    if performance <= 0:
        return 0.0

    # Apply thresholds as business rules:
    # <= 60, <= 80, <= 100, > 100
    # This avoids gaps for decimal percentages (e.g. 80.5).
    bounded = [b for b in bands if b["max_value"] is not None]
    bounded.sort(key=lambda b: float(b["max_value"]))
    for band in bounded:
        if performance <= float(band["max_value"]):
            return float(band["rate"])

    open_ended = [b for b in bands if b["max_value"] is None]
    if open_ended:
        return float(open_ended[0]["rate"])

    return 0.0


def pick_band_label(performance: float, bands: List[sqlite3.Row]) -> str:
    if performance <= 0:
        return "0-60"

    bounded = [b for b in bands if b["max_value"] is not None]
    bounded.sort(key=lambda b: float(b["max_value"]))
    for band in bounded:
        if performance <= float(band["max_value"]):
            return str(band["band_label"])

    open_ended = [b for b in bands if b["max_value"] is None]
    if open_ended:
        return str(open_ended[0]["band_label"])
    return "N/A"


def compute_salary_row(
    row: pd.Series,
    target_row: pd.Series,
    agent: sqlite3.Row,
    commissions: Dict[str, List[sqlite3.Row]],
) -> Dict:
    fixed = float(agent["salaire_fixe"])
    prime_map = {}
    performance_pct_map = {}
    band_map = {}

    for kpi in KPI_DEFINITIONS:
        realization = to_float(row[kpi["column"]])
        target = to_float(target_row.get(kpi["column"], 0))
        perf_pct = (realization / target) * 100 if target > 0 else 0.0
        rate = pick_rate(perf_pct, commissions[kpi["code"]])
        band_label = pick_band_label(perf_pct, commissions[kpi["code"]])
        prime = realization * rate if realization > 0 else 0.0
        prime_map[kpi["code"]] = {
            "performance": realization,
            "target": target,
            "rate": rate,
            "prime": prime,
        }
        performance_pct_map[kpi["code"]] = perf_pct
        band_map[kpi["code"]] = band_label

    variable_total = sum(item["prime"] for item in prime_map.values())
    total_salary = variable_total + fixed

    return {
        "telephone": parse_phone(row["TDR_TEL"]),
        "nom": row["TDR_NAMES"],
        "region": row["REGION"],
        "pool": row["POOL"],
        "supervisor": row["SUPERVISOR_NAME"],
        "Achiev. Quality Acquisition": to_float(row["Achiev. Quality Acquisition"]),
        "Actives Agents Doing quality Acquisitions": to_float(
            row["Actives Agents Doing quality Acquisitions"]
        ),
        "Achiev.Inflow": to_float(row.get("Achiev.Inflow", 0)),
        "Active M-pesa Agent": to_float(row["Active M-pesa Agent"]),
        "Cash in": to_float(row["Cash in"]),
        "Formation AML": to_float(row["Formation AML"]),
        "DMS": to_float(row["DMS"]),
        "NEW Agent Active": to_float(row["NEW Agent Active"]),
        "Perf % KPI1": performance_pct_map["KPI1_NEW_ACTIVE_AGENTS"],
        "Perf % KPI2": performance_pct_map["KPI2_MAINTAIN_ACTIVE_BASE"],
        "Perf % KPI3": performance_pct_map["KPI3_QUALITY_ACQUISITION"],
        "Perf % KPI4": performance_pct_map["KPI4_AGENT_DOING_ACQUISITION"],
        "Perf % KPI5": performance_pct_map["KPI5_CASH_IN"],
        "Perf % KPI6": performance_pct_map["KPI6_DMS"],
        "Perf % KPI7": performance_pct_map["KPI7_FORMATION_AML"],
        "Bande KPI1": band_map["KPI1_NEW_ACTIVE_AGENTS"],
        "Bande KPI2": band_map["KPI2_MAINTAIN_ACTIVE_BASE"],
        "Bande KPI3": band_map["KPI3_QUALITY_ACQUISITION"],
        "Bande KPI4": band_map["KPI4_AGENT_DOING_ACQUISITION"],
        "Bande KPI5": band_map["KPI5_CASH_IN"],
        "Bande KPI6": band_map["KPI6_DMS"],
        "Bande KPI7": band_map["KPI7_FORMATION_AML"],
        "KPI1 Prime": prime_map["KPI1_NEW_ACTIVE_AGENTS"]["prime"],
        "KPI2 Prime": prime_map["KPI2_MAINTAIN_ACTIVE_BASE"]["prime"],
        "KPI3 Prime": prime_map["KPI3_QUALITY_ACQUISITION"]["prime"],
        "KPI4 Prime": prime_map["KPI4_AGENT_DOING_ACQUISITION"]["prime"],
        "KPI5 Prime": prime_map["KPI5_CASH_IN"]["prime"],
        "KPI6 Prime": prime_map["KPI6_DMS"]["prime"],
        "KPI7 Prime": prime_map["KPI7_FORMATION_AML"]["prime"],
        "KPI1 Target": prime_map["KPI1_NEW_ACTIVE_AGENTS"]["target"],
        "KPI2 Target": prime_map["KPI2_MAINTAIN_ACTIVE_BASE"]["target"],
        "KPI3 Target": prime_map["KPI3_QUALITY_ACQUISITION"]["target"],
        "KPI4 Target": prime_map["KPI4_AGENT_DOING_ACQUISITION"]["target"],
        "KPI5 Target": prime_map["KPI5_CASH_IN"]["target"],
        "KPI6 Target": prime_map["KPI6_DMS"]["target"],
        "KPI7 Target": prime_map["KPI7_FORMATION_AML"]["target"],
        "KPI1 Rate": prime_map["KPI1_NEW_ACTIVE_AGENTS"]["rate"],
        "KPI2 Rate": prime_map["KPI2_MAINTAIN_ACTIVE_BASE"]["rate"],
        "KPI3 Rate": prime_map["KPI3_QUALITY_ACQUISITION"]["rate"],
        "KPI4 Rate": prime_map["KPI4_AGENT_DOING_ACQUISITION"]["rate"],
        "KPI5 Rate": prime_map["KPI5_CASH_IN"]["rate"],
        "KPI6 Rate": prime_map["KPI6_DMS"]["rate"],
        "KPI7 Rate": prime_map["KPI7_FORMATION_AML"]["rate"],
        "Variable Total": variable_total,
        "Salaire Fixe": fixed,
        "Salaire Total": total_salary,
    }


def build_inspired_view(results_df: pd.DataFrame) -> pd.DataFrame:
    base_cols = ["telephone", "nom", "region", "pool", "supervisor"]
    rows = []
    for _, row in results_df.iterrows():
        item = {col: row[col] for col in base_cols}
        for idx, (kpi_code, kpi_label) in enumerate(KPI_DISPLAY_ORDER, start=1):
            item[f"{kpi_label} | Target"] = row[f"KPI{idx} Target"]
            if idx <= 4:
                item[f"{kpi_label} | Réalisation"] = row[
                    [
                        "NEW Agent Active",
                        "Active M-pesa Agent",
                        "Achiev. Quality Acquisition",
                        "Actives Agents Doing quality Acquisitions",
                    ][idx - 1]
                ]
            elif idx == 5:
                item[f"{kpi_label} | Réalisation"] = row["Cash in"]
            elif idx == 6:
                item[f"{kpi_label} | Réalisation"] = row["DMS"]
            else:
                item[f"{kpi_label} | Réalisation"] = row["Formation AML"]
            item[f"{kpi_label} | %Perf"] = row[f"Perf % KPI{idx}"]
            item[f"{kpi_label} | Bande"] = row[f"Bande KPI{idx}"]
            item[f"{kpi_label} | Commission"] = row[f"KPI{idx} Rate"]
            item[f"{kpi_label} | Prime"] = row[f"KPI{idx} Prime"]
        item["Salaire Variable"] = row["Variable Total"]
        item["Salaire Fixe"] = row["Salaire Fixe"]
        item["Salaire Total"] = row["Salaire Total"]
        rows.append(item)
    return pd.DataFrame(rows)


def validate_commission_consistency(results_df: pd.DataFrame) -> List[str]:
    issues: List[str] = []
    for _, row in results_df.iterrows():
        phone = row.get("telephone", "N/A")
        for idx in range(1, 8):
            realization_col = {
                1: "NEW Agent Active",
                2: "Active M-pesa Agent",
                3: "Achiev. Quality Acquisition",
                4: "Actives Agents Doing quality Acquisitions",
                5: "Cash in",
                6: "DMS",
                7: "Formation AML",
            }[idx]
            realization = to_float(row.get(realization_col, 0))
            rate = to_float(row.get(f"KPI{idx} Rate", 0))
            expected_prime = realization * rate if realization > 0 else 0.0
            actual_prime = to_float(row.get(f"KPI{idx} Prime", 0))
            if abs(expected_prime - actual_prime) > 0.01:
                issues.append(
                    f"TDR {phone} - KPI{idx}: prime attendue {expected_prime:.2f}, trouvee {actual_prime:.2f}"
                )
    return issues


def normalize_band_label(value: str) -> str:
    text = normalize_text(value)
    if text in {"0_60", "0to60", "0_a_60"}:
        return "0-60"
    if text in {"61_80", "61to80", "61_a_80"}:
        return "61-80"
    if text in {"81_100", "81to100", "81_a_100"}:
        return "81-100"
    if text in {"100", "100_plus", "gt_100", "plus_100"} or "100" in text:
        return ">100"
    return value


def map_kpi_code_from_text(value: str) -> str:
    text = normalize_text(value)
    rules = [
        ("KPI1_NEW_ACTIVE_AGENTS", ["kpi1", "new_active", "new_agent_active"]),
        ("KPI2_MAINTAIN_ACTIVE_BASE", ["kpi2", "maintain", "base_active", "active_mpesa"]),
        ("KPI3_QUALITY_ACQUISITION", ["kpi3", "quality_acquisition", "quality"]),
        ("KPI4_AGENT_DOING_ACQUISITION", ["kpi4", "agents_doing", "doing_acquisition"]),
        ("KPI5_CASH_IN", ["kpi5", "cash_in", "cashin"]),
        ("KPI6_DMS", ["kpi6", "dms"]),
        ("KPI7_FORMATION_AML", ["kpi7", "formation_aml", "aml"]),
    ]
    for code, keywords in rules:
        if any(keyword in text for keyword in keywords):
            return code
    return ""


def import_commission_file(conn: sqlite3.Connection, uploaded_file) -> Tuple[int, List[str]]:
    errors: List[str] = []
    updated = 0

    def find_col(normalized_cols: Dict[str, str], candidates: List[str]) -> str:
        for key, original in normalized_cols.items():
            for cand in candidates:
                if cand == key or cand in key:
                    return original
        return ""

    uploaded_file.seek(0)
    df = pd.read_excel(uploaded_file, engine="openpyxl")
    df.columns = [str(col).strip() for col in df.columns]
    normalized_cols = {normalize_text(col): col for col in df.columns}

    # Format A: one row per KPI + band.
    kpi_col = find_col(
        normalized_cols,
        ["kpi", "kpis", "kpi_code", "kpi_label", "indicator", "indicateur"],
    )
    band_col = find_col(
        normalized_cols,
        ["band", "bands", "bande", "band_label", "tranche"],
    )
    rate_col = find_col(
        normalized_cols,
        [
            "rate",
            "commission",
            "commission_par_bande",
            "commission_bande",
            "value",
            "valeur",
            "taux",
            "paiement",
        ],
    )

    if kpi_col and band_col and rate_col:
        for _, row in df.iterrows():
            kpi_code = map_kpi_code_from_text(str(row.get(kpi_col, "")))
            raw_band = str(row.get(band_col, ""))
            band = normalize_band_label(raw_band)
            raw_band_norm = normalize_text(raw_band)
            if raw_band_norm in {"band_1", "bande_1"}:
                band = "0-60"
            elif raw_band_norm in {"band_2", "bande_2"}:
                band = "61-80"
            elif raw_band_norm in {"band_3", "bande_3"}:
                band = "81-100"
            elif raw_band_norm in {"band_4", "bande_4"}:
                band = ">100"
            rate = to_float(row.get(rate_col, 0))
            if not kpi_code or band not in {"0-60", "61-80", "81-100", ">100"}:
                continue
            conn.execute(
                "UPDATE commissions SET rate = ? WHERE kpi_code = ? AND band_label = ?",
                (rate, kpi_code, band),
            )
            updated += 1
        conn.commit()
        return updated, errors

    # Format B: one row per KPI with 4 band columns.
    possible_band_cols = {
        "0-60": None,
        "61-80": None,
        "81-100": None,
        ">100": None,
    }
    for norm_key, original_col in normalized_cols.items():
        band = normalize_band_label(norm_key)
        if band in possible_band_cols:
            possible_band_cols[band] = original_col

    if kpi_col and all(possible_band_cols.values()):
        for _, row in df.iterrows():
            kpi_code = map_kpi_code_from_text(str(row.get(kpi_col, "")))
            if not kpi_code:
                continue
            for band, col_name in possible_band_cols.items():
                rate = to_float(row.get(col_name, 0))
                conn.execute(
                    "UPDATE commissions SET rate = ? WHERE kpi_code = ? AND band_label = ?",
                    (rate, kpi_code, band),
                )
                updated += 1
        conn.commit()
        return updated, errors

    errors.append(
        "Format non reconnu. Le fichier doit contenir soit "
        "[KPI, Bande, Commission], soit [KPI, 0-60, 61-80, 81-100, >100]."
    )
    return updated, errors


def save_performances(conn: sqlite3.Connection, month: str, results_df: pd.DataFrame) -> None:
    for _, row in results_df.iterrows():
        conn.execute(
            """
            INSERT INTO performances (
                month, telephone, nom, region, pool, supervisor,
                achiev_quality_acquisition, active_agents_quality_acq, achiev_inflow,
                active_mpesa_agent, cash_in, formation_aml, dms, new_agent_active,
                kpi1_prime, kpi2_prime, kpi3_prime, kpi4_prime, kpi5_prime, kpi6_prime, kpi7_prime,
                variable_total, salaire_fixe, salaire_total
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(month, telephone) DO UPDATE SET
                nom=excluded.nom,
                region=excluded.region,
                pool=excluded.pool,
                supervisor=excluded.supervisor,
                achiev_quality_acquisition=excluded.achiev_quality_acquisition,
                active_agents_quality_acq=excluded.active_agents_quality_acq,
                achiev_inflow=excluded.achiev_inflow,
                active_mpesa_agent=excluded.active_mpesa_agent,
                cash_in=excluded.cash_in,
                formation_aml=excluded.formation_aml,
                dms=excluded.dms,
                new_agent_active=excluded.new_agent_active,
                kpi1_prime=excluded.kpi1_prime,
                kpi2_prime=excluded.kpi2_prime,
                kpi3_prime=excluded.kpi3_prime,
                kpi4_prime=excluded.kpi4_prime,
                kpi5_prime=excluded.kpi5_prime,
                kpi6_prime=excluded.kpi6_prime,
                kpi7_prime=excluded.kpi7_prime,
                variable_total=excluded.variable_total,
                salaire_fixe=excluded.salaire_fixe,
                salaire_total=excluded.salaire_total,
                imported_at=CURRENT_TIMESTAMP
            """,
            (
                month,
                row["telephone"],
                row["nom"],
                row["region"],
                row["pool"],
                row["supervisor"],
                row["Achiev. Quality Acquisition"],
                row["Actives Agents Doing quality Acquisitions"],
                row["Achiev.Inflow"],
                row["Active M-pesa Agent"],
                row["Cash in"],
                row["Formation AML"],
                row["DMS"],
                row["NEW Agent Active"],
                row["KPI1 Prime"],
                row["KPI2 Prime"],
                row["KPI3 Prime"],
                row["KPI4 Prime"],
                row["KPI5 Prime"],
                row["KPI6 Prime"],
                row["KPI7 Prime"],
                row["Variable Total"],
                row["Salaire Fixe"],
                row["Salaire Total"],
            ),
        )
    conn.commit()


def salary_color(value) -> str:
    if value > 500:
        return "background-color: #d1fae5; color: #065f46;"
    if value >= 200:
        return "background-color: #ffedd5; color: #9a3412;"
    return "background-color: #fee2e2; color: #991b1b;"


def inject_app_styles() -> None:
    st.markdown(
        """
        <style>
        .stApp {
            background:
                radial-gradient(circle at top left, rgba(16, 185, 129, 0.10), transparent 28%),
                radial-gradient(circle at top right, rgba(59, 130, 246, 0.10), transparent 24%),
                linear-gradient(180deg, #f8fafc 0%, #eef4ff 100%);
        }
        .block-container {
            padding-top: 1.4rem;
            padding-bottom: 2rem;
            max-width: 1450px;
        }
        div[data-testid="stSidebar"] {
            background: linear-gradient(180deg, #0f172a 0%, #172554 100%);
        }
        div[data-testid="stSidebar"] * {
            color: #e5eefb;
        }
        .hero-card {
            padding: 1.2rem 1.25rem;
            border-radius: 18px;
            background: linear-gradient(135deg, #0f766e 0%, #1d4ed8 100%);
            color: white;
            box-shadow: 0 18px 40px rgba(15, 23, 42, 0.14);
            margin-bottom: 1rem;
        }
        .hero-title {
            font-size: 1.85rem;
            font-weight: 700;
            margin-bottom: 0.25rem;
        }
        .hero-subtitle {
            font-size: 0.98rem;
            opacity: 0.92;
        }
        .metric-card {
            background: rgba(255, 255, 255, 0.92);
            border: 1px solid rgba(148, 163, 184, 0.22);
            border-radius: 16px;
            padding: 0.95rem 1rem;
            box-shadow: 0 10px 24px rgba(15, 23, 42, 0.06);
            margin-bottom: 0.75rem;
        }
        .metric-label {
            color: #475569;
            font-size: 0.84rem;
            margin-bottom: 0.2rem;
        }
        .metric-value {
            color: #0f172a;
            font-size: 1.45rem;
            font-weight: 700;
        }
        .section-caption {
            background: rgba(255, 255, 255, 0.82);
            border-left: 5px solid #2563eb;
            border-radius: 12px;
            padding: 0.8rem 1rem;
            margin: 0.2rem 0 1rem 0;
            color: #334155;
        }
        div[data-testid="stExpander"] {
            background: rgba(255, 255, 255, 0.84);
            border: 1px solid rgba(148, 163, 184, 0.20);
            border-radius: 14px;
            overflow: hidden;
        }
        div[data-testid="stDataFrame"], div[data-testid="stMarkdownContainer"] table {
            background: rgba(255, 255, 255, 0.95);
            border-radius: 12px;
        }
        .stButton > button, .stDownloadButton > button {
            border-radius: 12px;
            border: none;
            box-shadow: 0 8px 18px rgba(37, 99, 235, 0.16);
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def render_page_banner(title: str, subtitle: str) -> None:
    st.markdown(
        f"""
        <div class="hero-card">
            <div class="hero-title">{title}</div>
            <div class="hero-subtitle">{subtitle}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_metric_cards(metrics: List[Tuple[str, str]]) -> None:
    cols = st.columns(len(metrics))
    for col, (label, value) in zip(cols, metrics):
        with col:
            st.markdown(
                f"""
                <div class="metric-card">
                    <div class="metric-label">{label}</div>
                    <div class="metric-value">{value}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )


def render_section_caption(text: str) -> None:
    st.markdown(f'<div class="section-caption">{text}</div>', unsafe_allow_html=True)


def show_logic_schema() -> None:
    with st.expander("Comprendre la logique de calcul (schéma simple)"):
        st.markdown(
            """
            ### Flux de l'application

            1. **Entrées**
               - `target.xlsx` (objectifs par KPI et par TDR)
               - `evidence.xlsx` (réalisations par KPI et par TDR)
               - table `commissions` (bandes + taux)
               - table `agents` (salaire fixe)

            2. **Traitement**
               - Match des agents par `TDR_TEL`
               - Pour chaque KPI: `performance % = (réalisation / target) * 100`
               - Positionnement dans la bande (`0-60`, `61-80`, `81-100`, `>100`)
               - Prime KPI: `réalisation * taux_de_la_bande`

            3. **Sorties**
               - `variable_total = somme(primes KPI)`
               - `salaire_total = variable_total + salaire_fixe`
               - sauvegarde dans `performances` + export CSV/Excel
            """
        )

        st.info(
            "Règle clé: si la réalisation est 0, la prime KPI est 0. "
            "Si le target est 0, la performance % est considérée à 0."
        )


def show_home(conn: sqlite3.Connection) -> None:
    total_agents = conn.execute("SELECT COUNT(*) AS c FROM agents").fetchone()["c"]
    total_months = conn.execute("SELECT COUNT(DISTINCT month) AS c FROM performances").fetchone()["c"]
    render_page_banner(
        "Gestion des Salaires TDR - Vodacash",
        "Importez les targets et les realisations pour calculer automatiquement la paie mensuelle des agents.",
    )
    render_metric_cards(
        [
            ("Agents en base", str(total_agents)),
            ("Mois archives", str(total_months)),
            ("Salaire fixe standard", f"{DEFAULT_FIXED_SALARY:.0f} USD"),
        ]
    )
    render_section_caption("Zone principale de calcul: chargez les fichiers, lancez le calcul et verifiez les primes KPI.")
    show_logic_schema()
    selected_month = st.selectbox(
        "Mois de paie",
        options=[
            datetime.now().strftime("%Y-%m"),
            (datetime.now().replace(day=1) - pd.DateOffset(months=1)).strftime("%Y-%m"),
            (datetime.now().replace(day=1) - pd.DateOffset(months=2)).strftime("%Y-%m"),
        ],
    )

    target_file = st.file_uploader(
        "Déposez le fichier target.xlsx",
        type=["xlsx"],
        accept_multiple_files=False,
    )

    uploaded_file = st.file_uploader(
        "Déposez le fichier evidence.xlsx (réalisations)",
        type=["xlsx"],
        accept_multiple_files=False,
    )

    if st.button(
        "Importer et Calculer",
        type="primary",
        disabled=(uploaded_file is None or target_file is None),
    ):
        try:
            df, missing = read_evidence_file(uploaded_file)
            if missing:
                st.error(f"Colonnes manquantes dans le fichier: {', '.join(missing)}")
                st.info(
                    "Vérifiez que le fichier contient bien les colonnes attendues, "
                    "même si la ligne d'en-tête n'est pas la première."
                )
                return
            target_df, target_missing = read_target_file(target_file)
            if target_missing:
                st.error(
                    "Colonnes target manquantes dans le fichier target: "
                    + ", ".join(target_missing)
                )
                target_file.seek(0)
                raw_target_df = pd.read_excel(target_file, engine="openpyxl", header=None)
                sample_headers = raw_target_df.head(5).fillna("").astype(str)
                st.info("Aperçu des 5 premières lignes du fichier target pour diagnostic:")
                st.dataframe(sample_headers, use_container_width=True)
                return

            target_df["TDR_TEL"] = target_df["TDR_TEL"].apply(parse_phone)
            target_map = {
                parse_phone(row["TDR_TEL"]): row for _, row in target_df.iterrows()
            }

            unknown_agents = []
            unknown_targets = []
            results = []
            commissions = load_commissions(conn)
            progress = st.progress(0, text="Calcul des salaires en cours...")

            for idx, row in df.iterrows():
                phone = parse_phone(row["TDR_TEL"])
                if not phone:
                    continue
                target_row = target_map.get(phone)
                if target_row is None:
                    unknown_targets.append(
                        {"telephone": phone, "nom": str(row.get("TDR_NAMES", "")).strip()}
                    )
                    progress.progress((idx + 1) / len(df), text=f"Traitement ligne {idx + 1}/{len(df)}")
                    continue
                agent = conn.execute(
                    "SELECT * FROM agents WHERE telephone = ?", (phone,)
                ).fetchone()
                if not agent:
                    unknown_agents.append(
                        {
                            "telephone": phone,
                            "nom": str(row["TDR_NAMES"]).strip(),
                            "region": str(row["REGION"]).strip(),
                            "pool": str(row["POOL"]).strip(),
                            "supervisor": str(row["SUPERVISOR_NAME"]).strip(),
                        }
                    )
                else:
                    results.append(compute_salary_row(row, target_row, agent, commissions))
                progress.progress((idx + 1) / len(df), text=f"Traitement ligne {idx + 1}/{len(df)}")

            progress.empty()

            if unknown_agents:
                st.warning("Certains agents sont absents de la base. Ajoutez-les avant calcul complet.")
                unknown_df = pd.DataFrame(unknown_agents).drop_duplicates(subset=["telephone"])
                st.dataframe(unknown_df, use_container_width=True)
                with st.expander("Ajouter ces agents en masse"):
                    if st.button("Ajouter tous les agents inconnus"):
                        for item in unknown_df.to_dict(orient="records"):
                            conn.execute(
                                """
                                INSERT OR IGNORE INTO agents (telephone, nom, region, pool, supervisor, salaire_fixe)
                                VALUES (?, ?, ?, ?, ?, ?)
                                """,
                                (
                                    item["telephone"],
                                    item["nom"] or "Nom inconnu",
                                    item["region"],
                                    item["pool"],
                                    item["supervisor"],
                                    DEFAULT_FIXED_SALARY,
                                ),
                            )
                        conn.commit()
                        st.success("Agents ajoutés. Relancez l'import pour recalculer.")

            if unknown_targets:
                st.warning(
                    "Certains agents n'ont pas de target correspondant dans le fichier target.xlsx."
                )
                st.dataframe(pd.DataFrame(unknown_targets).drop_duplicates(), use_container_width=True)

            if results:
                results_df = pd.DataFrame(results)
                validation_issues = validate_commission_consistency(results_df)
                save_performances(conn, selected_month, results_df)

                st.success(f"{len(results_df)} salaires calculés et enregistrés pour {selected_month}.")
                if validation_issues:
                    st.error(
                        "Controle commission: incoherences detectees. "
                        "Verifiez les lignes ci-dessous."
                    )
                    st.dataframe(
                        pd.DataFrame({"anomalie": validation_issues}),
                        use_container_width=True,
                    )
                else:
                    st.success(
                        "Controle commission OK: chaque prime KPI = realisation x commission de la bande."
                    )
                with st.expander("Voir les détails du calcul", expanded=True):
                    styler = results_df.style
                    if hasattr(styler, "map"):
                        styler = styler.map(salary_color, subset=["Salaire Total"])
                    else:
                        styler = styler.applymap(salary_color, subset=["Salaire Total"])

                    styled_df = styler.format(
                        {
                            "Variable Total": "{:.2f}",
                            "Salaire Fixe": "{:.2f}",
                            "Salaire Total": "{:.2f}",
                            "KPI1 Prime": "{:.2f}",
                            "KPI2 Prime": "{:.2f}",
                            "KPI3 Prime": "{:.2f}",
                            "KPI4 Prime": "{:.2f}",
                            "KPI5 Prime": "{:.2f}",
                            "KPI6 Prime": "{:.2f}",
                            "KPI7 Prime": "{:.2f}",
                            "Perf % KPI1": "{:.2f}",
                            "Perf % KPI2": "{:.2f}",
                            "Perf % KPI3": "{:.2f}",
                            "Perf % KPI4": "{:.2f}",
                            "Perf % KPI5": "{:.2f}",
                            "Perf % KPI6": "{:.2f}",
                            "Perf % KPI7": "{:.2f}",
                        }
                    )
                    st.dataframe(styled_df, use_container_width=True)

                with st.expander("Vue tableau inspire (Target / Realisation / % / Bande / Commission / Prime)"):
                    inspired_df = build_inspired_view(results_df)
                    inspired_styler = inspired_df.style
                    if hasattr(inspired_styler, "map"):
                        inspired_styler = inspired_styler.map(
                            salary_color, subset=["Salaire Total"]
                        )
                    else:
                        inspired_styler = inspired_styler.applymap(
                            salary_color, subset=["Salaire Total"]
                        )
                    st.dataframe(
                        inspired_styler.format(
                            {
                                col: "{:.2f}"
                                for col in inspired_df.columns
                                if any(
                                    key in col
                                    for key in [
                                        "Target",
                                        "Réalisation",
                                        "%Perf",
                                        "Commission",
                                        "Prime",
                                        "Salaire",
                                    ]
                                )
                                and "Bande" not in col
                            }
                        ),
                        use_container_width=True,
                    )
            else:
                st.error(
                    "Aucun salaire calculé. Vérifiez la correspondance des téléphones "
                    "entre evidence et target, puis l'existence des agents en base."
                )
                st.info(
                    f"Lignes evidence: {len(df)} | Targets uniques: {len(set(target_map.keys()))} | "
                    f"Agents sans target: {len(pd.DataFrame(unknown_targets).drop_duplicates()) if unknown_targets else 0} | "
                    f"Agents absents en base: {len(pd.DataFrame(unknown_agents).drop_duplicates()) if unknown_agents else 0}"
                )
        except Exception as exc:
            st.error(f"Erreur pendant l'import/calcul: {exc}")

    st.divider()
    st.subheader("Historique des salaires")
    months = conn.execute(
        "SELECT DISTINCT month FROM performances ORDER BY month DESC"
    ).fetchall()
    month_options = [m["month"] for m in months]
    if month_options:
        selected_history_month = st.selectbox("Choisir un mois", month_options, key="history_month")
        hist_df = pd.read_sql_query(
            "SELECT telephone, nom, region, supervisor, variable_total, salaire_fixe, salaire_total, imported_at FROM performances WHERE month = ? ORDER BY salaire_total DESC",
            conn,
            params=[selected_history_month],
        )
        st.dataframe(hist_df, use_container_width=True)

        csv_data = hist_df.to_csv(index=False).encode("utf-8")
        st.download_button(
            "Exporter en CSV",
            data=csv_data,
            file_name=f"salaires_{selected_history_month}.csv",
            mime="text/csv",
        )

        excel_buffer = io.BytesIO()
        with pd.ExcelWriter(excel_buffer, engine="openpyxl") as writer:
            hist_df.to_excel(writer, sheet_name="Salaires", index=False)
        st.download_button(
            "Exporter en Excel",
            data=excel_buffer.getvalue(),
            file_name=f"salaires_{selected_history_month}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
    else:
        st.info("Aucun historique disponible pour le moment.")


def show_commissions(conn: sqlite3.Connection) -> None:
    commission_count = conn.execute("SELECT COUNT(*) AS c FROM commissions").fetchone()["c"]
    render_page_banner(
        "Configuration des Commissions",
        "Ajustez les taux par bande ou importez un fichier Excel pour mettre a jour les commissions en masse.",
    )
    render_metric_cards(
        [
            ("Lignes de commission", str(commission_count)),
            ("KPIs configures", str(len(KPI_DEFINITIONS))),
            ("Bandes par KPI", "4"),
        ]
    )
    render_section_caption("Vous pouvez modifier manuellement les bandes ci-dessous ou importer directement un fichier de commissions.")

    with st.expander("Importer un fichier de commissions", expanded=True):
        uploaded_commission_file = st.file_uploader(
            "Fichier commission.xlsx",
            type=["xlsx"],
            accept_multiple_files=False,
            key="commission_file_uploader",
        )
        if st.button(
            "Importer commissions",
            type="primary",
            disabled=uploaded_commission_file is None,
        ):
            try:
                updated_count, import_errors = import_commission_file(conn, uploaded_commission_file)
                if import_errors:
                    for err in import_errors:
                        st.error(err)
                elif updated_count == 0:
                    st.warning("Aucune commission mise à jour. Vérifiez le contenu du fichier.")
                else:
                    st.success(f"Import réussi: {updated_count} valeurs de commission mises à jour.")
            except Exception as exc:
                st.error(f"Erreur pendant l'import des commissions: {exc}")

    commissions = load_commissions(conn)

    for kpi in KPI_DEFINITIONS:
        st.markdown(f"### {kpi['label']}")
        band_rows = commissions.get(kpi["code"], [])
        cols = st.columns(4)
        for i, band in enumerate(band_rows):
            max_txt = "et plus" if band["max_value"] is None else f"à {band['max_value']}"
            label = f"{band['min_value']} {max_txt}"
            with cols[i]:
                new_rate = st.number_input(
                    f"Bande {band['band_label']}",
                    min_value=0.0,
                    value=float(band["rate"]),
                    format="%.6f",
                    key=f"{kpi['code']}_{band['band_label']}",
                    help=label,
                )
                if new_rate != float(band["rate"]):
                    conn.execute(
                        "UPDATE commissions SET rate = ? WHERE id = ?",
                        (new_rate, band["id"]),
                    )
                    conn.commit()
        st.divider()
    st.success("Les commissions affichées sont synchronisées avec la base.")


def show_agents(conn: sqlite3.Connection) -> None:
    total_agents = conn.execute("SELECT COUNT(*) AS c FROM agents").fetchone()["c"]
    region_count = conn.execute(
        "SELECT COUNT(DISTINCT COALESCE(region, '')) AS c FROM agents"
    ).fetchone()["c"]
    render_page_banner(
        "Gestion des Agents",
        "Centralisez la base TDR, importez des listes en masse et maintenez les informations de reference.",
    )
    render_metric_cards(
        [
            ("Agents actifs en base", str(total_agents)),
            ("Regions repertoriees", str(region_count)),
            ("Fixe par defaut", f"{DEFAULT_FIXED_SALARY:.0f} USD"),
        ]
    )
    render_section_caption("Ajoutez, importez, mettez a jour ou supprimez des agents selon vos besoins.")

    with st.expander("Importer des agents en masse (Excel)", expanded=True):
        uploaded_agents_file = st.file_uploader(
            "Fichier agents/evidence.xlsx",
            type=["xlsx"],
            accept_multiple_files=False,
            key="agents_file_uploader",
        )
        if st.button(
            "Importer agents",
            type="primary",
            disabled=uploaded_agents_file is None,
        ):
            try:
                agents_df_import, missing = read_agents_file(uploaded_agents_file)
                if missing:
                    st.error(
                        "Colonnes manquantes pour import agents: " + ", ".join(missing)
                    )
                else:
                    inserted = 0
                    updated = 0
                    skipped = 0
                    for _, row in agents_df_import.iterrows():
                        phone = parse_phone(row.get("TDR_TEL", ""))
                        name = str(row.get("TDR_NAMES", "")).strip()
                        if not phone or not name:
                            skipped += 1
                            continue
                        exists = conn.execute(
                            "SELECT 1 FROM agents WHERE telephone = ?",
                            (phone,),
                        ).fetchone()
                        if exists:
                            updated += 1
                        else:
                            inserted += 1
                        conn.execute(
                            """
                            INSERT OR REPLACE INTO agents
                            (telephone, nom, region, pool, supervisor, salaire_fixe)
                            VALUES (?, ?, ?, ?, ?, ?)
                            """,
                            (
                                phone,
                                name,
                                str(row.get("REGION", "")).strip(),
                                str(row.get("POOL", "")).strip(),
                                str(row.get("SUPERVISOR_NAME", "")).strip(),
                                DEFAULT_FIXED_SALARY,
                            ),
                        )
                    conn.commit()
                    st.success(
                        f"Import terminé: {inserted} ajoutés, {updated} mis à jour, {skipped} ignorés."
                    )
            except Exception as exc:
                st.error(f"Erreur import agents: {exc}")

    with st.expander("Ajouter un agent", expanded=True):
        with st.form("add_agent_form"):
            col1, col2 = st.columns(2)
            with col1:
                nom = st.text_input("Nom complet")
                telephone = st.text_input("Téléphone")
                region = st.text_input("Région")
            with col2:
                pool = st.text_input("Pool")
                supervisor = st.text_input("Supervisor")
                salaire_fixe = st.number_input("Salaire fixe (USD)", min_value=0.0, value=75.0)
            submitted = st.form_submit_button("Ajouter")
            if submitted:
                if not telephone.strip() or not nom.strip():
                    st.error("Le nom et le téléphone sont obligatoires.")
                else:
                    conn.execute(
                        """
                        INSERT OR REPLACE INTO agents (telephone, nom, region, pool, supervisor, salaire_fixe)
                        VALUES (?, ?, ?, ?, ?, ?)
                        """,
                        (telephone.strip(), nom.strip(), region.strip(), pool.strip(), supervisor.strip(), salaire_fixe),
                    )
                    conn.commit()
                    st.success("Agent enregistré.")

    agents_df = pd.read_sql_query("SELECT * FROM agents ORDER BY nom ASC", conn)
    st.subheader("Liste des agents")
    st.dataframe(agents_df, use_container_width=True)

    with st.expander("Modifier / Supprimer un agent"):
        if agents_df.empty:
            st.info("Aucun agent en base.")
            return
        selected_phone = st.selectbox("Sélectionner un agent", agents_df["telephone"].tolist())
        selected = agents_df[agents_df["telephone"] == selected_phone].iloc[0]

        with st.form("edit_agent_form"):
            nom_edit = st.text_input("Nom", value=selected["nom"])
            region_edit = st.text_input("Région", value=selected["region"] or "")
            pool_edit = st.text_input("Pool", value=selected["pool"] or "")
            supervisor_edit = st.text_input("Supervisor", value=selected["supervisor"] or "")
            fixe_edit = st.number_input("Salaire fixe (USD)", min_value=0.0, value=float(selected["salaire_fixe"]))

            col_upd, col_del = st.columns(2)
            with col_upd:
                update_submitted = st.form_submit_button("Mettre à jour")
            with col_del:
                delete_submitted = st.form_submit_button("Supprimer")

            if update_submitted:
                conn.execute(
                    """
                    UPDATE agents
                    SET nom = ?, region = ?, pool = ?, supervisor = ?, salaire_fixe = ?
                    WHERE telephone = ?
                    """,
                    (nom_edit.strip(), region_edit.strip(), pool_edit.strip(), supervisor_edit.strip(), fixe_edit, selected_phone),
                )
                conn.commit()
                st.success("Agent mis à jour.")

            if delete_submitted:
                conn.execute("DELETE FROM agents WHERE telephone = ?", (selected_phone,))
                conn.commit()
                st.warning("Agent supprimé.")


def main() -> None:
    st.set_page_config(page_title="Gestion Salaires TDR", page_icon=":moneybag:", layout="wide")
    inject_app_styles()
    conn = get_connection()
    init_db(conn)

    menu = st.sidebar.radio(
        "Navigation",
        options=["Accueil", "Configuration des Commissions", "Gestion des Agents"],
    )

    if menu == "Accueil":
        show_home(conn)
    elif menu == "Configuration des Commissions":
        show_commissions(conn)
    else:
        show_agents(conn)

    conn.close()


if __name__ == "__main__":
    main()
