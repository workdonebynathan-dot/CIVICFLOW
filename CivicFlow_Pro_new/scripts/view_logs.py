import mysql.connector
from db_config import get_db_connection

def show_activity():
    try:
        conn = get_db_connection()
        if not conn or not conn.is_connected():
            print("❌ Could not connect to the database.")
            return

        cursor = conn.cursor()
        
        # 👇 FIXED: Changed 'timestamp' to 'login_time'
        cursor.execute("SELECT * FROM login_logs ORDER BY login_time DESC LIMIT 20")
        logs = cursor.fetchall()
        
        print("\n" + "="*85)
        # Adjusted columns to match your DB: id, email, role, ip_address, login_time
        print(f"{'TIME':<22} | {'ROLE':<12} | {'IP ADDRESS':<15} | {'EMAIL'}")
        print("="*85)
        
        for row in logs:
            # row structure: (id, email, role, ip_address, login_time)
            # row[0]=id, row[1]=email, row[2]=role, row[3]=ip, row[4]=time
            
            timestamp = str(row[4]) # login_time
            email = row[1]
            role = row[2]
            ip = row[3]
            
            # Note: Your current DB might be missing the 'status' column. 
            # If so, we just skip printing it to prevent errors.
            print(f"{timestamp:<22} | {role:<12} | {ip:<15} | {email}")
        
        print("="*85 + "\n")
        cursor.close()
        conn.close()
        
    except mysql.connector.Error as err:
        print(f"Error: {err}")

if __name__ == "__main__":
    show_activity()