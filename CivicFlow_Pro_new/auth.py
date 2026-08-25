import mysql.connector
from werkzeug.security import generate_password_hash, check_password_hash
from db_config import get_db_connection

def create_user(name, email, password):
    """Creates a new user and SAVES them to the database."""
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        # 1. Check if email exists
        cur.execute("SELECT id FROM users WHERE email = %s", (email,))
        if cur.fetchone():
            print(f"❌ Signup Failed: Email {email} already exists.")
            return False

        # 2. Hash Password
        hashed_pw = generate_password_hash(password)

        # 3. Insert User
        cur.execute(
            "INSERT INTO users (name, email, password, role) VALUES (%s, %s, %s, 'user')",
            (name, email, hashed_pw)
        )
        
        # 4. THE MOST IMPORTANT LINE: SAVE THE DATA
        conn.commit() 
        print(f"✅ SUCCESS: User {email} saved to database.")
        return True

    except Exception as e:
        print(f"❌ Error creating user: {e}")
        return False
    finally:
        cur.close()
        conn.close()

def verify_user(email, password):
    """Checks credentials for login."""
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute("SELECT * FROM users WHERE email = %s", (email,))
        user = cur.fetchone()
        
        # Schema: id(0), name(1), email(2), password(3), role(4)
        if user and check_password_hash(user[3], password):
            return user
        return None
    except Exception as e:
        print(f"Error verifying user: {e}")
        return None
    finally:
        cur.close()
        conn.close()