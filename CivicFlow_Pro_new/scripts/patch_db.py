import sqlite3

def patch_database():
    print("🚑 Patching database...")
    try:
        conn = sqlite3.connect('civicflow.db')
        cursor = conn.cursor()
        
        # List of columns to check and add
        columns_to_add = [
            ("complaints", "latitude", "TEXT"),
            ("complaints", "longitude", "TEXT"),
            ("complaints", "feedback_comment", "TEXT"),
            ("complaints", "rating", "INTEGER"),
            ("complaints", "hierarchy_status", "TEXT DEFAULT 'Section Clerk'"),
            ("complaints", "current_desk", "TEXT DEFAULT 'Section Clerk'"),
            ("users", "phone", "TEXT"),
            ("users", "address", "TEXT")
        ]

        for table, col, dtype in columns_to_add:
            try:
                # Try to select the column to see if it exists
                cursor.execute(f"SELECT {col} FROM {table} LIMIT 1")
            except sqlite3.OperationalError:
                # If it fails, the column is missing -> Add it
                print(f"   ➕ Adding missing column: {col} to {table}")
                cursor.execute(f"ALTER TABLE {table} ADD COLUMN {col} {dtype}")

        conn.commit()
        conn.close()
        print("✅ Database successfully updated! You can now submit complaints.")
        
    except Exception as e:
        print(f"❌ Error patching database: {e}")

if __name__ == "__main__":
    patch_database()