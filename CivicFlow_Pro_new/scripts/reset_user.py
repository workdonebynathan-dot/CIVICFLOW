import mysql.connector
from db_config import get_db_connection

def delete_broken_user():
    email = ""  # <--- The email from your logs
    
    print(f"--- Fixing Account: {email} ---")
    conn = get_db_connection()
    cur = conn.cursor()
    
    # Check if user exists
    cur.execute("SELECT id, name FROM users WHERE email = %s", (email,))    
    user = cur.fetchone()
    
    if user:
        print(f"Found User ID: {user[0]} (Name: {user[1]})")
        # DELETE THE USER
        cur.execute("DELETE FROM users WHERE email = %s", (email,))
        conn.commit()
        print("✅ User DELETED successfully.")
        print("👉 Now go to the Sign Up page and register this email again.")
    else:
        print("❌ User not found. You can just register normally.")
        
    cur.close()
    conn.close()

if __name__ == "__main__":
    delete_broken_user()