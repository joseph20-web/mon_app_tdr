"""
SCRIPT D'INITIALISATION DE LA BASE DE DONNÉES TDR
À exécuter UNE SEULE FOIS pour importer la liste des agents
"""

import sqlite3
import pandas as pd
import os
from datetime import datetime

# ============================================
# 1. CONNEXION À LA BASE DE DONNÉES
# ============================================
DB_PATH = "tdr_management.db"

def init_database():
    """Crée toutes les tables nécessaires"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Table des agents (TDR)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS agents (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            telephone TEXT UNIQUE NOT NULL,
            nom TEXT NOT NULL,
            region TEXT,
            pool TEXT,
            supervisor TEXT,
            mpesa_regmanager TEXT,
            salaire_fixe REAL DEFAULT 75,
            date_creation TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Table des commissions (paramètres modifiables)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS commissions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            kpi_name TEXT NOT NULL,
            bande_min REAL,
            bande_max REAL,
            valeur REAL,
            mois TEXT,
            UNIQUE(kpi_name, bande_min, bande_max, mois)
        )
    ''')
    
    # Table des performances mensuelles
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS performances_mensuelles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            telephone TEXT NOT NULL,
            mois TEXT NOT NULL,
            kpi1_performance REAL,
            kpi1_prime REAL,
            kpi2_performance REAL,
            kpi2_prime REAL,
            kpi3_performance REAL,
            kpi3_prime REAL,
            kpi4_performance REAL,
            kpi4_prime REAL,
            kpi5_performance REAL,
            kpi5_prime REAL,
            kpi6_performance REAL,
            kpi6_prime REAL,
            kpi7_performance REAL,
            kpi7_prime REAL,
            salaire_variable REAL,
            salaire_total REAL,
            date_calcul TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (telephone) REFERENCES agents(telephone)
        )
    ''')
    
    # Table des historiques d'import
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS historique_imports (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            fichier_nom TEXT,
            date_import TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            nb_agents_traites INTEGER,
            mois_concerne TEXT
        )
    ''')
    
    conn.commit()
    conn.close()
    print("✅ Base de données initialisée avec succès!")


def import_liste_tdr(fichier_excel):
    """
    Importe la liste des TDR depuis le fichier Excel
    """
    # Lire le fichier Excel
    df = pd.read_excel(fichier_excel, skiprows=1)  # skiprows=1 pour ignorer la ligne vide
    
    # Afficher les colonnes pour vérification
    print("\n📋 Colonnes trouvées dans le fichier:")
    print(df.columns.tolist())
    
    # Renommer les colonnes pour correspondre à notre structure
    colonnes_mapping = {
        'REGION': 'region',
        'MPESA_REGMANAGER': 'mpesa_regmanager',
        'SUPERVISOR_NAME': 'supervisor',
        'POOL': 'pool',
        'TDR_NAMES': 'nom',
        'NEW TDR_TEL': 'telephone'
    }
    
    # Vérifier si les colonnes existent
    for ancien, nouveau in colonnes_mapping.items():
        if ancien not in df.columns:
            print(f"⚠️ Attention: Colonne '{ancien}' non trouvée!")
    
    # Renommer les colonnes
    df = df.rename(columns=colonnes_mapping)
    
    # Garder seulement les colonnes nécessaires
    colonnes_necessaires = ['region', 'mpesa_regmanager', 'supervisor', 'pool', 'nom', 'telephone']
    for col in colonnes_necessaires:
        if col not in df.columns:
            print(f"❌ Erreur: Colonne '{col}' manquante après renommage!")
            return
    
    # Nettoyer les données
    df = df[colonnes_necessaires].copy()
    
    # Supprimer les lignes vides
    df = df.dropna(subset=['telephone', 'nom'])
    
    # Convertir les téléphones en string
    df['telephone'] = df['telephone'].astype(str).str.strip()
    df['nom'] = df['nom'].astype(str).str.strip()
    
    # Remplacer les valeurs NaN par des chaînes vides
    df = df.fillna('')
    
    print(f"\n📊 {len(df)} agents trouvés dans le fichier")
    
    # Connexion à la base
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Compteurs
    nb_inseres = 0
    nb_ignores = 0
    
    # Insérer chaque agent
    for index, row in df.iterrows():
        try:
            cursor.execute('''
                INSERT OR REPLACE INTO agents 
                (telephone, nom, region, pool, supervisor, mpesa_regmanager, salaire_fixe, date_creation)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                row['telephone'],
                row['nom'],
                row['region'],
                row['pool'],
                row['supervisor'],
                row['mpesa_regmanager'],
                75.0,  # Salaire fixe par défaut
                datetime.now()
            ))
            nb_inseres += 1
            print(f"   ✅ [{nb_inseres}] {row['nom']} - {row['telephone']}")
        except Exception as e:
            nb_ignores += 1
            print(f"   ❌ Erreur pour {row['nom']}: {e}")
    
    conn.commit()
    conn.close()
    
    print(f"\n🎉 Importation terminée!")
    print(f"   - Agents insérés/mis à jour: {nb_inseres}")
    print(f"   - Agents ignorés (erreur): {nb_ignores}")
    
    return nb_inseres


def initialiser_commissions_par_defaut():
    """
    Initialise les commissions par défaut dans la base
    """
    # Configuration des KPI avec leurs bandes et valeurs
    # Format: (kpi_name, bande_min, bande_max, valeur)
    commissions_defaut = [
        # KPI 1 - New Active Agents
        ("New_Active_Agents", 0, 60, 6.53),
        ("New_Active_Agents", 61, 80, 8.71),
        ("New_Active_Agents", 81, 100, 10.89),
        ("New_Active_Agents", 101, 999999, 13.07),
        
        # KPI 2 - Maintain Existing Base Active Agent
        ("Maintain_Base_Active", 0, 60, 0.21),
        ("Maintain_Base_Active", 61, 80, 0.28),
        ("Maintain_Base_Active", 81, 100, 0.36),
        ("Maintain_Base_Active", 101, 999999, 0.43),
        
        # KPI 3 - Quality Acquisition
        ("Quality_Acquisition", 0, 60, 0.18),
        ("Quality_Acquisition", 61, 80, 0.25),
        ("Quality_Acquisition", 81, 100, 0.31),
        ("Quality_Acquisition", 101, 999999, 0.37),
        
        # KPI 4 - Agents Doing Quality Acquisitions
        ("Agents_Doing_Quality", 0, 60, 0.37),
        ("Agents_Doing_Quality", 61, 80, 0.49),
        ("Agents_Doing_Quality", 81, 100, 0.61),
        ("Agents_Doing_Quality", 101, 999999, 0.74),
        
        # KPI 5 - Cash In
        ("Cash_In", 0, 60, 0.000018),
        ("Cash_In", 61, 80, 0.000024),
        ("Cash_In", 81, 100, 0.000030),
        ("Cash_In", 101, 999999, 0.000036),
        
        # KPI 6 - DMS
        ("DMS", 0, 60, 0.05),
        ("DMS", 61, 80, 0.07),
        ("DMS", 81, 99, 0.09),
        ("DMS", 100, 999999, 0.11),
        
        # KPI 7 - Formation AML
        ("Formation_AML", 0, 60, 0.13),
        ("Formation_AML", 61, 80, 0.17),
        ("Formation_AML", 81, 99, 0.21),
        ("Formation_AML", 100, 999999, 0.26),
    ]
    
    mois_courant = datetime.now().strftime("%Y-%m")
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    for kpi, min_val, max_val, valeur in commissions_defaut:
        cursor.execute('''
            INSERT OR REPLACE INTO commissions 
            (kpi_name, bande_min, bande_max, valeur, mois)
            VALUES (?, ?, ?, ?, ?)
        ''', (kpi, min_val, max_val, valeur, mois_courant))
    
    conn.commit()
    conn.close()
    
    print("✅ Commissions par défaut initialisées!")


def verifier_base():
    """Affiche un résumé de la base de données"""
    conn = sqlite3.connect(DB_PATH)
    
    # Nombre d'agents
    df_agents = pd.read_sql_query("SELECT COUNT(*) as nb FROM agents", conn)
    print(f"\n📊 RÉSUMÉ DE LA BASE:")
    print(f"   - Nombre d'agents: {df_agents['nb'].iloc[0]}")
    
    # Aperçu des agents
    df_apercu = pd.read_sql_query("SELECT telephone, nom, region, pool FROM agents LIMIT 10", conn)
    print(f"\n📋 APERÇU DES AGENTS (10 premiers):")
    print(df_apercu.to_string(index=False))
    
    # Nombre de commissions
    df_comm = pd.read_sql_query("SELECT COUNT(*) as nb FROM commissions", conn)
    print(f"\n💰 Commissions configurées: {df_comm['nb'].iloc[0]}")
    
    conn.close()


# ============================================
# EXÉCUTION PRINCIPALE
# ============================================
if __name__ == "__main__":
    print("=" * 60)
    print("    INITIALISATION DE LA BASE TDR")
    print("=" * 60)
    
    # 1. Créer la base de données
    init_database()
    
    # 2. Importer la liste des TDR
    fichier_liste = "liste tdr.xlsx"
    
    if os.path.exists(fichier_liste):
        print(f"\n📂 Lecture du fichier: {fichier_liste}")
        import_liste_tdr(fichier_liste)
    else:
        print(f"\n❌ Fichier '{fichier_liste}' non trouvé!")
        print("   Assurez-vous que le fichier est dans le même dossier que ce script.")
        print("   Ou modifiez le nom du fichier dans le code.")
    
    # 3. Initialiser les commissions par défaut
    initialiser_commissions_par_defaut()
    
    # 4. Vérifier la base
    verifier_base()
    
    print("\n" + "=" * 60)
    print("    INITIALISATION TERMINÉE!")
    print("=" * 60)
    print("\n💡 Prochaines étapes:")
    print("   1. Lancez l'application: streamlit run app.py")
    print("   2. Importez evidence.xlsx pour calculer les salaires")
    print("   3. Configurez les commissions si nécessaire")