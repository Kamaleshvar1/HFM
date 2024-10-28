import sqlite3
from werkzeug.security import generate_password_hash

def create_admin_user(username, password):
    # Connect to your database
    conn = sqlite3.connect('attendance.db')
    cursor = conn.cursor()

    # Create admin_users table if it doesn't exist
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS admin_users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL UNIQUE,
            password TEXT NOT NULL
        )
    ''')

    # Hash the password
    hashed_password = generate_password_hash(password)

    # Insert the admin user into the table
    try:
        cursor.execute('INSERT INTO admin_users (username, password) VALUES (?, ?)', (username, hashed_password))
        conn.commit()
        print(f"Admin user '{username}' created successfully.")
    except sqlite3.IntegrityError:
        print(f"Username '{username}' already exists.")
    finally:
        conn.close()

# Replace these values with your desired username and password
username = "admin1"  # Change this to your preferred username
password = "admin123"  # Change this to a secure password

# Call the function to create the admin user
create_admin_user(username, password)
