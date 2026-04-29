# TDR Payroll - Django

Application Django professionnelle pour le calcul des salaires des agents TDR (Vodacash).
Migration de l'ancienne app Streamlit/SQLite vers Django avec base prete pour PostgreSQL,
moteur de calcul en `Decimal`, design responsive et exports Excel/PDF.

## Fonctionnalites

- Dashboard analytique (top performeurs, salaires par region, anomalies).
- Cycles de paie mensuels (`PayrollCycle`) avec upload combine `target.xlsx + evidence.xlsx`.
- Moteur de calcul en `Decimal`: `(realisation / target) * 100` -> bande -> commission -> prime.
- Bandes continues: `Band1 (<=60), Band2 (<=80), Band3 (<=100), Band4 (>100)`.
- Detection automatique des entetes Excel + alias + parsing des montants europeens (`6,53 EUR`).
- Imports dedies: agents, evidence, targets, grille de commissions.
- CRUD complet des agents, edition de la grille des commissions, simulation libre.
- Recalcul instantane d'un cycle apres modification d'un taux.
- Exports Excel (Synthese + Detail KPI + Anomalies) et PDF (synthese cycle, bulletin agent).
- Migration automatique de l'ancienne base SQLite (`migrate_legacy_db`).
- Tests unitaires sur le moteur de calcul + le parser Excel.

## Prerequis

- Python 3.10+
- pip

## Demarrage rapide

```bash
cd tdr_payroll
python -m pip install -r ../requirements.txt
python manage.py migrate
python manage.py seed_defaults
python manage.py migrate_legacy_db   # facultatif, importe tdr_payroll.db existant
python manage.py createsuperuser
python manage.py runserver
```

L'application est disponible sur http://127.0.0.1:8000/.

L'admin Django est sur http://127.0.0.1:8000/admin/.

## Configuration

Les variables peuvent etre passees via un fichier `.env` ou des variables d'environnement
(grace a `python-decouple`):

| Variable | Description | Defaut |
|----------|-------------|--------|
| `DJANGO_SECRET_KEY` | Cle secrete | cle de dev |
| `DJANGO_DEBUG` | Mode debug | `True` |
| `DJANGO_ALLOWED_HOSTS` | Hotes autorises (separes par virgule) | `*` |
| `DATABASE_URL` | URL PostgreSQL `postgres://user:pass@host:5432/db` | (vide -> SQLite) |
| `LEGACY_SQLITE_PATH` | Chemin de la base legacy a migrer | `../tdr_payroll.db` |

Si `DATABASE_URL` est defini, Django utilise PostgreSQL via `psycopg2-binary`. Sinon SQLite local.

## Structure

```
tdr_payroll/
  agents/           # CRUD agents, regions, pools, supervisors, import excel
  commissions/      # KPI, bandes, taux, import grille
  payroll/          # cycles, calcul, imports target/evidence, exports
  dashboard/        # vue d'accueil
  core/             # excel parser, alias, commande migrate_legacy_db
  templates/        # base.html + theme moderne
  static/css/       # theme.css
```

## Workflow paie

1. Aller sur **Upload &amp; Calcul**.
2. Choisir le mois (YYYY-MM) et uploader `target.xlsx` + `evidence.xlsx`.
3. L'application detecte les entetes, normalise, matche les agents par telephone,
   calcule chaque KPI puis le salaire total.
4. Le cycle est cree ou mis a jour. Une page detail liste chaque agent + KPI + bande.
5. Boutons disponibles: **Recalculer**, **Valider**, **Exporter Excel/PDF**, **Bulletin agent PDF**.

## Verification rapide

Lancer la suite de tests:

```bash
python manage.py test core payroll
```

Sortie attendue: `Ran 16 tests ... OK`.

## Migration des donnees existantes

```bash
python manage.py migrate_legacy_db --path ../tdr_payroll.db
```

Cette commande:
- recupere les `agents` (avec creation des Region/Pool/Supervisor),
- recupere la grille `commissions` (sous forme de `CommissionRate` avec `valid_from = today`),
- recupere l'historique des `performances` en `PayrollCycle` + `PayrollEntry` + `PayrollKPIDetail`.

## Bonnes pratiques

- Gardez la grille des commissions versionnee via `valid_from`/`valid_to`.
- En cas de modification d'un taux pour un mois deja calcule, cliquer sur **Recalculer** dans le cycle correspondant.
- Les anomalies (`prime != realisation * taux` ou `target manquant`) sont automatiquement
  surlignees dans le tableau et listees dans la feuille Excel "Anomalies".
