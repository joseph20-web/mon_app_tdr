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
