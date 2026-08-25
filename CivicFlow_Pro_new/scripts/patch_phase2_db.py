import sys
import os

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import db_config

def patch_db():
    conn = db_config.get_db_connection()
    if not conn:
        print("Failed to connect to DB.")
        return
    
    cur = conn.cursor()
    
    # 1. Add is_escalated and escalation_timestamp
    print("Checking for Phase 2 columns in 'complaints' table...")
    try:
        cur.execute("ALTER TABLE complaints ADD COLUMN is_escalated BOOLEAN DEFAULT FALSE;")
        print("Added 'is_escalated' column.")
    except Exception as e:
        print("Column 'is_escalated' might already exist:", e)
        
    try:
        cur.execute("ALTER TABLE complaints ADD COLUMN escalation_timestamp DATETIME DEFAULT NULL;")
        print("Added 'escalation_timestamp' column.")
    except Exception as e:
        print("Column 'escalation_timestamp' might already exist:", e)
        
    conn.commit()
    cur.close()
    conn.close()
    print("Phase 2 DB Patch complete!")

if __name__ == "__main__":
    patch_db()
