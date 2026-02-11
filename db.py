import sqlite3
import pandas as pd
from datetime import datetime

DB_NAME = "assessment_v2.db"

def init_db():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    
    # 1. PROJECTS (The Company being audited)
    c.execute('''
        CREATE TABLE IF NOT EXISTS projects (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            company_name TEXT UNIQUE,
            industry TEXT,
            created_at TEXT
        )
    ''')
    
    # 2. ASSESSMENTS (An individual scorer's session)
    c.execute('''
        CREATE TABLE IF NOT EXISTS assessments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id INTEGER,
            scorer_name TEXT,
            created_at TEXT,
            FOREIGN KEY(project_id) REFERENCES projects(id),
            UNIQUE(project_id, scorer_name)
        )
    ''')
    
    # 3. SCORES (The actual data points)
    c.execute('''
        CREATE TABLE IF NOT EXISTS scores (
            assessment_id INTEGER,
            section_id TEXT,
            question_id TEXT,
            score INTEGER,
            PRIMARY KEY (assessment_id, question_id),
            FOREIGN KEY(assessment_id) REFERENCES assessments(id)
        )
    ''')
    conn.commit()
    conn.close()

# --- PROJECT MANAGEMENT ---
def create_project(name, industry):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    try:
        c.execute("INSERT INTO projects (company_name, industry, created_at) VALUES (?, ?, ?)",
                  (name, industry, datetime.now().strftime("%Y-%m-%d %H:%M")))
        conn.commit()
        return c.lastrowid
    except sqlite3.IntegrityError:
        return None # Duplicate name
    finally:
        conn.close()

def get_all_projects():
    conn = sqlite3.connect(DB_NAME)
    df = pd.read_sql_query("SELECT * FROM projects ORDER BY created_at DESC", conn)
    conn.close()
    return df

# --- SCORER MANAGEMENT ---
def join_project(project_id, scorer_name):
    """Creates a new assessment slot for a user if it doesn't exist."""
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    # Check if user already exists for this project
    c.execute("SELECT id FROM assessments WHERE project_id=? AND scorer_name=?", (project_id, scorer_name))
    row = c.fetchone()
    
    if row:
        assessment_id = row[0]
    else:
        c.execute("INSERT INTO assessments (project_id, scorer_name, created_at) VALUES (?, ?, ?)",
                  (project_id, scorer_name, datetime.now().strftime("%Y-%m-%d %H:%M")))
        assessment_id = c.lastrowid
        conn.commit()
    conn.close()
    return assessment_id

def get_project_scorers(project_id):
    conn = sqlite3.connect(DB_NAME)
    df = pd.read_sql_query("SELECT scorer_name FROM assessments WHERE project_id=?", conn, params=(project_id,))
    conn.close()
    return df['scorer_name'].tolist()

# --- SCORING ---
def save_score(assessment_id, question_id, section_id, score):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute('''
        INSERT INTO scores (assessment_id, question_id, section_id, score)
        VALUES (?, ?, ?, ?)
        ON CONFLICT(assessment_id, question_id) 
        DO UPDATE SET score=excluded.score
    ''', (assessment_id, question_id, section_id, score))
    conn.commit()
    conn.close()

def get_my_scores(assessment_id):
    """Get scores for the current logged-in user."""
    conn = sqlite3.connect(DB_NAME)
    df = pd.read_sql_query("SELECT * FROM scores WHERE assessment_id=?", conn, params=(assessment_id,))
    conn.close()
    return df

def get_aggregated_scores(project_id):
    """
    MAGIC QUERY: Joins Projects -> Assessments -> Scores
    Calculates the average score for every question across all users.
    """
    conn = sqlite3.connect(DB_NAME)
    query = '''
        SELECT 
            s.section_id,
            s.question_id,
            AVG(s.score) as avg_score,
            GROUP_CONCAT(s.score) as all_raw_scores,
            COUNT(s.score) as scorer_count
        FROM scores s
        JOIN assessments a ON s.assessment_id = a.id
        WHERE a.project_id = ?
        GROUP BY s.question_id
    '''
    df = pd.read_sql_query(query, conn, params=(project_id,))
    conn.close()
    return df