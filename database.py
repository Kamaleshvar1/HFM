import sqlite3

# Connect to SQLite database (or create it if it doesn't exist)
# conn = sqlite3.connect('attendance.db')
#
# # Create a cursor to execute SQL commands
# cur = conn.cursor()
#
# # Create Users table
# cur.execute('''
#     CREATE TABLE IF NOT EXISTS users (
#         user_id TEXT PRIMARY KEY,
#         name TEXT NOT NULL,
#         room_number TEXT
#     )
# ''')
#
# # Create Attendance table
# cur.execute('''
#     CREATE TABLE IF NOT EXISTS attendance (
#         id INTEGER PRIMARY KEY AUTOINCREMENT,
#         user_id TEXT NOT NULL,
#         date DATE NOT NULL,
#         status TEXT DEFAULT 'present',
#         FOREIGN KEY (user_id) REFERENCES users (user_id)
#     )
# ''')
#
# # Commit changes and close connection
# conn.commit()
# conn.close()

# Reconnect to the database
conn = sqlite3.connect('attendance.db')
cur = conn.cursor()

# Sample data for users
sample_users = [
    ('21104301', 'Manoj', '101'),
    ('21104302', 'Viswa', '102'),
    ('21104303', 'Kamaleshvar', '103'),
    ('21104304', 'Harish', '104'),
    ('21104305', 'Dinesh', '105')
]

# Insert data into users table
cur.executemany('INSERT OR IGNORE INTO users (user_id, name, room_number) VALUES (?, ?, ?)', sample_users)

# Commit changes and close connection
conn.commit()
conn.close()
