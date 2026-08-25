import mysql.connector
from db_config import get_db_connection

conn = get_db_connection()
cur = conn.cursor()

try:
    print("Adding 'feedback_comment'...")
    cur.execute("ALTER TABLE complaints ADD COLUMN feedback_comment TEXT DEFAULT NULL")
    print("SUCCESS: feedback_comment added.")
except Exception as e:
    print(f"Skipping feedback_comment: {e}")

try:
    print("Adding 'rating'...")
    cur.execute("ALTER TABLE complaints ADD COLUMN rating INT DEFAULT NULL")
    print("SUCCESS: rating added.")
except Exception as e:
    print(f"Skipping rating: {e}")

conn.commit()
cur.close()
conn.close()
print("Done.")