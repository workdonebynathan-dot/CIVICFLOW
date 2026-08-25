import mysql.connector

def get_db_connection():
    try:
        connection = mysql.connector.connect(
            host="localhost",
            user="root",          # Your MySQL Username
            password="MYSQL",          # Your MySQL Password (leave empty if none)
            database="civicflow"  # The Database Name
        )
        return connection
    except mysql.connector.Error as err:
        print(f"Error: {err}")
        return None