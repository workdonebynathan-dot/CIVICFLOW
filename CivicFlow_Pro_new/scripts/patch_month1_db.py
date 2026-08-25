import mysql.connector
from db_config import get_db_connection

def migrate_db():
    conn = get_db_connection()
    if not conn:
        print("Failed to connect to database.")
        return
        
    cur = conn.cursor()
    
    # 1. Add columns to complaints table
    columns = [
        ("upvotes", "INT DEFAULT 0"),
        ("routing_engine", "VARCHAR(50) DEFAULT 'Heuristic (Keyword)'"),
        ("confidence_score", "DECIMAL(5, 2) DEFAULT 100.00")
    ]
    
    for col_name, col_def in columns:
        try:
            print(f"Adding {col_name} to complaints...")
            cur.execute(f"ALTER TABLE complaints ADD COLUMN {col_name} {col_def}")
            print(f"SUCCESS: {col_name} added.")
        except mysql.connector.Error as e:
            # If it already exists, it will throw an error, which is fine
            if e.errno == 1060: # ER_DUP_FIELDNAME
                print(f"Column {col_name} already exists.")
            else:
                print(f"Skipping {col_name}: {e}")

    # 2. Create complaint_upvotes table
    try:
        print("Creating complaint_upvotes table...")
        cur.execute("""
            CREATE TABLE IF NOT EXISTS complaint_upvotes (
                complaint_id INT,
                user_id INT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (complaint_id, user_id)
            )
        """)
        print("SUCCESS: complaint_upvotes table created.")
    except Exception as e:
        print(f"Failed to create complaint_upvotes table: {e}")

    conn.commit()
    cur.close()
    conn.close()
    print("Database migration completed.")

if __name__ == "__main__":
    migrate_db()
