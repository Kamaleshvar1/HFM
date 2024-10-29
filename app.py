from flask import Flask, request, redirect, url_for, session, render_template, flash, send_file
from werkzeug.security import generate_password_hash, check_password_hash
import sqlite3
from datetime import datetime, timedelta, time
import qrcode
import os
import random
import requests
from dotenv import load_dotenv

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY")  # Change this to a random secret key
load_dotenv()


# Connect to SQLite database (or create if it doesn't exist)
def get_db_connection():
    conn = sqlite3.connect("attendance.db")
    conn.row_factory = sqlite3.Row
    return conn


# Admin login route
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        recaptcha_response = request.form['g-recaptcha-response']

        # Verify reCAPTCHA
        secret_key = os.getenv("RECAPTCHA_KEY")  # Replace with your actual secret key
        payload = {
            'secret': secret_key,
            'response': recaptcha_response
        }

        response = requests.post('https://www.google.com/recaptcha/api/siteverify', data=payload)
        result = response.json()

        if result['success']:
            conn = get_db_connection()
            user = conn.execute('SELECT * FROM admin_users WHERE username = ?', (username,)).fetchone()
            conn.close()

            if user and check_password_hash(user['password'], password):
                session['user_id'] = user['id']  # Save user ID in session
                return redirect(url_for('admin_panel'))
            else:
                return render_template('login.html', error='Invalid credentials')
        else:
            return render_template('login.html', error='reCAPTCHA verification failed. Please try again.')

    return render_template('login.html')


# Logout route
@app.route('/logout')
def logout():
    session.pop('user_id', None)  # Remove user ID from session
    return redirect(url_for('login'))


def add_columns():
    conn = get_db_connection()
    cur = conn.cursor()
    # Add the unique_code and code_expiry columns to users table if they do not already exist
    try:
        cur.execute("ALTER TABLE users ADD COLUMN unique_code TEXT")
    except sqlite3.OperationalError:
        pass  # unique_code column already exists

    try:
        cur.execute("ALTER TABLE users ADD COLUMN code_expiry DATETIME")
    except sqlite3.OperationalError:
        pass  # code_expiry column already exists

    conn.commit()
    conn.close()


# Call this function at the start of the app to add any missing columns
add_columns()


# Initialize database tables if they don't exist
def initialize_db():
    conn = get_db_connection()
    cur = conn.cursor()

    # Create users table if it doesn't exist
    cur.execute('''CREATE TABLE IF NOT EXISTS users (
                    user_id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    room_number TEXT,
                    unique_code TEXT,
                    code_expiry DATETIME
                )''')

    # Create attendance table with updated schema
    cur.execute('''CREATE TABLE IF NOT EXISTS attendance (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT,
                    date DATE,
                    morning_status TEXT,
                    afternoon_status TEXT,
                    night_status TEXT,
                    FOREIGN KEY (user_id) REFERENCES users (user_id)
                )''')

    # Create session_timings table if it doesn't exist
    cur.execute('''CREATE TABLE IF NOT EXISTS session_timings (
                    session_name TEXT PRIMARY KEY,
                    start_time TEXT,
                    end_time TEXT
                )''')

    # Add default session timings if they are not set
    default_timings = [
        ('morning', '08:00', '12:00'),
        ('afternoon', '12:00', '14:00'),
        ('night', '18:30', '21:00')
    ]
    for name, start, end in default_timings:
        cur.execute("INSERT OR IGNORE INTO session_timings (session_name, start_time, end_time) VALUES (?, ?, ?)",
                    (name, start, end))

    conn.commit()
    conn.close()


initialize_db()


@app.route('/')
def home():
    return render_template('index.html')  # Ensure this file exists in your templates directory


# Route to generate OTP and QR code
@app.route('/generate_qr', methods=['POST'])
def generate_qr():
    user_id = request.form['user_id']

    # Generate a unique 6-digit code
    unique_code = str(random.randint(100000, 999999))  # Generate random 6-digit number

    # Set expiry time for the unique code (5 minutes from now)
    expiry_time = datetime.now() + timedelta(minutes=5)

    # Store the unique code and expiry time in the database
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("UPDATE users SET unique_code = ?, code_expiry = ? WHERE user_id = ?",
                (unique_code, expiry_time, user_id))
    conn.commit()
    conn.close()

    qr_data = f'{unique_code}'

    # Generate QR code
    qr_img = qrcode.make(qr_data)

    # Ensure the 'static' directory exists
    static_dir = 'static'
    if not os.path.exists(static_dir):
        os.makedirs(static_dir)

    qr_img_path = os.path.join(static_dir, f'{user_id}_qr.png')
    qr_img.save(qr_img_path)

    # Send the file to the user
    return send_file(qr_img_path, as_attachment=True)


# Function to check if the current time is within a specified range
def is_within_time_range(start_time, end_time):
    now = datetime.now().time()
    return start_time <= now <= end_time


# Define session timings in a dictionary for easier management and configurability


SESSION_TIMINGS = {
    'morning': (time(8, 0), time(12, 0)),
    'afternoon': (time(12, 0), time(14, 0)),
    'night': (time(18, 30), time(21, 0)),
}


@app.route('/mark_attendance', methods=['POST'])
def mark_attendance():
    user_id = request.form.get('user_id')
    entered_code = request.form.get('unique_code')
    current_date = datetime.now().date()
    current_time = datetime.now().time()

    # Connect to the database
    conn = get_db_connection()
    cur = conn.cursor()

    # Fetch user details based on user_id
    user = cur.execute("SELECT * FROM users WHERE user_id = ?", (user_id,)).fetchone()

    if not user:
        return render_template("result.html", message="User ID not found.")

    # OTP validation
    if not (user["unique_code"] == entered_code and user["code_expiry"] and datetime.now() < datetime.fromisoformat(
            user["code_expiry"])):
        return render_template("result.html", message="Invalid or expired OTP.")

    # Determine session based on time
    session = None
    for sess_name, (start, end) in SESSION_TIMINGS.items():
        if start <= current_time <= end:
            session = sess_name
            break

    if not session:
        return render_template("result.html", message="Attendance is not available at this time.")

    # Check if attendance is already marked for today in this session
    attendance = cur.execute("SELECT * FROM attendance WHERE user_id = ? AND date = ?",
                             (user_id, current_date)).fetchone()

    if attendance and attendance[f"{session}_status"] == 'present':
        message = f"Attendance for the {session} session has already been marked today."
    else:
        # Mark attendance for the user in the current session
        if attendance:
            cur.execute(f"UPDATE attendance SET {session}_status = 'present' WHERE user_id = ? AND date = ?",
                        (user_id, current_date))
        else:
            cur.execute(f"INSERT INTO attendance (user_id, date, {session}_status) VALUES (?, ?, 'present')",
                        (user_id, current_date))

        # Clear the unique_code and code_expiry after successful attendance marking
        cur.execute("UPDATE users SET unique_code = NULL, code_expiry = NULL WHERE user_id = ?", (user_id,))
        conn.commit()
        message = f"Attendance marked successfully for the {session} session."

    # Close the database connection
    conn.close()
    return render_template("result.html", message=message)


# Function to update session timings in the database
@app.route('/update_session_timings', methods=['POST'])
def update_session_timings():
    morning_start = request.form.get('morning_start')
    morning_end = request.form.get('morning_end')
    afternoon_start = request.form.get('afternoon_start')
    afternoon_end = request.form.get('afternoon_end')
    night_start = request.form.get('night_start')
    night_end = request.form.get('night_end')

    conn = get_db_connection()
    cur = conn.cursor()

    # Clear old timings
    cur.execute("DELETE FROM session_timings")

    # Insert new session timings with session_name
    cur.execute("INSERT INTO session_timings (session_name, start_time, end_time) VALUES (?, ?, ?)",
                ('morning', morning_start, morning_end))
    cur.execute("INSERT INTO session_timings (session_name, start_time, end_time) VALUES (?, ?, ?)",
                ('afternoon', afternoon_start, afternoon_end))
    cur.execute("INSERT INTO session_timings (session_name, start_time, end_time) VALUES (?, ?, ?)",
                ('night', night_start, night_end))

    conn.commit()
    conn.close()

    flash("Session timings updated successfully")
    return redirect(url_for('session_timings'))

@app.route('/session_timings', methods=['GET', 'POST'])
def session_timings():
    if request.method == 'POST':
        morning_start = request.form['morning_start']
        morning_end = request.form['morning_end']
        afternoon_start = request.form['afternoon_start']
        afternoon_end = request.form['afternoon_end']
        night_start = request.form['night_start']
        night_end = request.form['night_end']

        # Update session timings in the database
        update_session_timings(morning_start, morning_end, afternoon_start, afternoon_end, night_start, night_end)

    # Fetch session timings from the database
    sessions = fetch_session_timings()

    # Set default values if sessions list is empty
    if not sessions:
        sessions = [
            {'session_name': 'morning', 'start_time': '08:00', 'end_time': '12:00'},
            {'session_name': 'afternoon', 'start_time': '12:00', 'end_time': '14:00'},
            {'session_name': 'night', 'start_time': '18:30', 'end_time': '21:00'}
        ]

    return render_template('session_timings.html', sessions=sessions)

def fetch_session_timings():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT session_name, start_time, end_time FROM session_timings")
    sessions = cur.fetchall()
    conn.close()
    return [{'session_name': session['session_name'], 'start_time': session['start_time'], 'end_time': session['end_time']} for session in sessions]



# Admin panel to add users
@app.route('/admin_panel')
def admin_panel():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    conn = get_db_connection()
    cur = conn.cursor()

    # Fetch all users
    users = cur.execute("SELECT * FROM users").fetchall()

    # Fetch today's date in the correct format
    today = datetime.now().date()

    # Fetch all attendance records for today
    attendance_records = cur.execute(
        """
        SELECT a.*, u.name
        FROM attendance a
        JOIN users u ON a.user_id = u.user_id
        WHERE a.date = ?
        """, (today,)
    ).fetchall()

    # Create a dictionary of attendance statuses by user_id
    # This will map each user_id to their attendance status for today
    attendance_status = {
        record['user_id']: {
            'name': record['name'],  # Assuming you have a name field in attendance records
            'morning': record['morning_status'],
            'afternoon': record['afternoon_status'],
            'night': record['night_status'],
            'date': record['date']
        } for record in attendance_records
    }
    cur.close()
    return render_template('admin_panel.html', users=users, attendance_status=attendance_status, today=today)


@app.route('/users')
def users_page():
    conn = get_db_connection()
    cur = conn.cursor()

    # Fetch all users
    users = cur.execute("SELECT * FROM users").fetchall()

    cur.close()
    return render_template('users.html', users=users)


@app.route('/attendance_records')
def attendance_records_page():
    conn = get_db_connection()
    cur = conn.cursor()

    # Fetch today's date
    today = datetime.now().date()

    # Fetch all attendance records for today
    attendance_records = cur.execute(
        """
        SELECT a.*, u.name
        FROM attendance a
        JOIN users u ON a.user_id = u.user_id
        WHERE a.date = ?
        """, (today,)
    ).fetchall()

    cur.close()
    return render_template('attendance_records.html', attendance_records=attendance_records)


@app.route('/add_user', methods=['GET', 'POST'])
def add_user():
    if request.method == 'POST':
        user_id = request.form['user_id']
        name = request.form['name']
        room_number = request.form['room_number']

        conn = get_db_connection()
        cur = conn.cursor()

        # Insert new user into the database
        cur.execute("INSERT INTO users (user_id, name, room_number) VALUES (?, ?, ?)",
                    (user_id, name, room_number))
        conn.commit()
        cur.close()

        return redirect(url_for('users_page'))

    return render_template('add_user.html')


@app.route('/remove_user/<user_id>', methods=['POST'])
def remove_user(user_id):
    conn = get_db_connection()
    cur = conn.cursor()
    # Remove user and their attendance records
    cur.execute("DELETE FROM users WHERE user_id = ?", (user_id,))
    cur.execute("DELETE FROM attendance WHERE user_id = ?", (user_id,))
    conn.commit()
    conn.close()
    return redirect(url_for('admin_panel'))


if __name__ == '__main__':
    initialize_db()
    app.run(debug=True)
