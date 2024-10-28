# from flask import Flask
# import sqlite3
#
# app = Flask(__name__)  # Define the Flask app here
#
#
# def initialize_db():
#     conn = sqlite3.connect("attendance.db")
#     cur = conn.cursor()
#
#     # Create users table
#     cur.execute('''
#     CREATE TABLE IF NOT EXISTS users (
#         user_id TEXT PRIMARY KEY,
#         name TEXT NOT NULL,
#         room_number TEXT NOT NULL
#     )
#     ''')
#
#     # Create attendance table
#     cur.execute('''
#     CREATE TABLE IF NOT EXISTS attendance (
#         id INTEGER PRIMARY KEY AUTOINCREMENT,
#         user_id TEXT NOT NULL,
#         date DATE NOT NULL,
#         status TEXT NOT NULL,
#         unique_code TEXT NOT NULL,
#         FOREIGN KEY (user_id) REFERENCES users (user_id)
#     )
#     ''')
#
#     conn.commit()
#     conn.close()
#
#
# if __name__ == '__main__':
#     initialize_db()  # Call the function to create the tables
#     app.run(debug=True)  # Start the Flask app
import sqlite3


def initialize_db():
    conn = sqlite3.connect("attendance.db")
    cur = conn.cursor()

    # Create the users table without the unique_code field
    cur.execute('''
    CREATE TABLE IF NOT EXISTS users (
        user_id TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        room_number TEXT NOT NULL
    )
    ''')

    # Create the attendance table with unique_code
    cur.execute('''
    CREATE TABLE IF NOT EXISTS attendance (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id TEXT NOT NULL,
        date DATE NOT NULL,
        status TEXT NOT NULL,
        unique_code TEXT NOT NULL,
        FOREIGN KEY (user_id) REFERENCES users (user_id)
    )
    ''')

    conn.commit()
    conn.close()


# Initialize the database
if __name__ == '__main__':
    initialize_db()
