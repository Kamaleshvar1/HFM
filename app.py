from flask import Flask, request, render_template, redirect, url_for
import sqlite3
from datetime import datetime


app = Flask(__name__)

# Connect to SQLite database (or create if it doesn't exist)
def get_db_connection():
    conn = sqlite3.connect("attendance.db")
    conn.row_factory = sqlite3.Row
    return conn

@app.route('/')
def home():
    return render_template('index.html')  # Form to enter user ID

@app.route('/mark_attendance', methods=['POST'])
def mark_attendance():
    user_id = request.form['user_id']
    date = datetime.now().date()

    conn = get_db_connection()
    cur = conn.cursor()
    # Check if user exists
    user = cur.execute("SELECT * FROM users WHERE user_id = ?", (user_id,)).fetchone()
    if user:
        # Log attendance if not already marked
        attendance = cur.execute("SELECT * FROM attendance WHERE user_id = ? AND date = ?", (user_id, date)).fetchone()
        if not attendance:
            cur.execute("INSERT INTO attendance (user_id, date, status) VALUES (?, ?, 'present')", (user_id, date))
            conn.commit()
            message = "Attendance marked successfully."
        else:
            message = "Attendance already marked."
    else:
        message = "User ID not found."
    conn.close()
    return render_template("result.html", message=message)

# Admin panel to add users
@app.route('/admin')
def admin_panel():
    return render_template('admin.html')  # Form to enter new user details

# Route to handle adding new users
@app.route('/add_user', methods=['POST'])
def add_user():
    user_id = request.form['user_id']
    name = request.form['name']
    room_number = request.form['room_number']

    conn = get_db_connection()
    cur = conn.cursor()
    # Insert the new user data into the users table
    cur.execute("INSERT OR IGNORE INTO users (user_id, name, room_number) VALUES (?, ?, ?)", (user_id, name, room_number))
    conn.commit()
    conn.close()
    return redirect(url_for('admin_panel'))

if __name__ == '__main__':
    app.run(debug=True)
