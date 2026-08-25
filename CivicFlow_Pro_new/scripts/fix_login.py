import mysql.connector
from werkzeug.security import generate_password_hash, check_password_hash
from db_config import get_db_connection

def manual_fix():
    print("--- 🛠 DIAGNOSTIC & FIX TOOL ---")
    
    email = "citizen@test.com"
    raw_password = "123"  # Simple password for testing
    
    conn = get_db_connection()
    cur = conn.cursor()

    # 1. Check if user exists
    print(f"\n1. Checking for existing user: {email}...")
    cur.execute("SELECT * FROM users WHERE email = %s", (email,))
    existing_user = cur.fetchone()

    if existing_user:
        print(f"   Found existing user (ID: {existing_user[0]}). Deleting to reset...")
        cur.execute("DELETE FROM users WHERE email = %s", (email,))
        conn.commit()
        print("   User deleted.")
    else:
        print("   User not found (Database is clean).")

    # 2. Create the user manually
    print(f"\n2. Creating new user '{email}' with password '{raw_password}'...")
    hashed_pw = generate_password_hash(raw_password)
    
    try:
        cur.execute(
            "INSERT INTO users (name, email, password, role) VALUES (%s, %s, %s, 'user')",
            ("Test Citizen", email, hashed_pw)
        )
        conn.commit()  # <--- CRITICAL STEP
        print("   ✅ SUCCESS: User saved to database.")
    except Exception as e:
        print(f"   ❌ ERROR SAVING USER: {e}")
        return

    # 3. Verify immediately
    print(f"\n3. Verifying login logic...")
    cur.execute("SELECT * FROM users WHERE email = %s", (email,))
    user = cur.fetchone()
    
    # user tuple structure: (id, name, email, password_hash, role, created_at)
    # password_hash is at index 3
    stored_hash = user[3]
    
    if check_password_hash(stored_hash, raw_password):
        print("   ✅ VERIFICATION PASSED: Password matches hash.")
        print(f"   --> Login Creds: {email} / {raw_password}")
        print("   --> PLEASE TRY LOGGING IN WITH THESE EXACT DETAILS NOW.")
    else:
        print("   ❌ VERIFICATION FAILED: Hash mismatch.")

    cur.close()
    conn.close()

if __name__ == "__main__":
    manual_fix()