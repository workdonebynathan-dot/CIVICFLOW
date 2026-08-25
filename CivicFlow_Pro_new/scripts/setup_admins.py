import mysql.connector
from auth import create_user
from db_config import get_db_connection

def setup_developer():
    print("--- Setting up Developer Admin ---")
    email = "totex@admin.com"
    password = "totex"
    
    # 1. Create the user using the app's secure create_user function
    # This ensures the password is properly hashed
    print(f"Creating user {email}...")
    result = create_user("System Developer", email, password)
    
    if result:
        print("User created successfully.")
    else:
        print("User already exists. Proceeding to update role...")

    # 2. Force update the role to 'admin' (Super Admin)
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute("UPDATE users SET role='admin' WHERE email=%s", (email,))
        conn.commit()
        print(f"SUCCESS: {email} is now a Super Admin.")
    except Exception as e:
        print(f"Error updating role: {e}")
    finally:
        cur.close()
        conn.close()

def setup_departments():
    print("\n--- Setting up Department Admins ---")
    # These use plain text passwords as per your current logic
    admins = [
        ('water@admin.com', 'admin123', 'Water Board'),
        ('electric@admin.com', 'admin123', 'Electricity Board'),
        ('traffic@admin.com', 'admin123', 'Traffic Police'),
        ('municipal@admin.com', 'admin123', 'Municipality')
    ]

    conn = get_db_connection()
    cur = conn.cursor()
    
    for email, pwd, dept in admins:
        try:
            # Check if exists first to avoid duplicate errors
            cur.execute("SELECT id FROM department_admins WHERE email=%s", (email,))
            if cur.fetchone():
                print(f"Skipping {dept} (Already exists)")
            else:
                cur.execute(
                    "INSERT INTO department_admins (email, password, department) VALUES (%s, %s, %s)",
                    (email, pwd, dept)
                )
                print(f"Created Admin for: {dept}")
        except Exception as e:
            print(f"Error creating {dept}: {e}")

    conn.commit()
    cur.close()
    conn.close()
    print("Department setup complete.")

if __name__ == "__main__":
    setup_developer()
    setup_departments()