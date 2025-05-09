from flask import Flask, redirect, url_for, render_template, request, session, flash, get_flashed_messages
import subprocess
import sqlite3
from datetime import datetime, timedelta

app = Flask(__name__)
app.secret_key = 'cheese_burger_footletuce'

# this function simply calls a function to turn of a specific ip-address.
# diko alam kung tama yung commands kaya baka dito yung mismong nasira na
# part lmao.

def turn_off_pc_windows(ip):
    try:
        result = subprocess.run(["powershell", "-Command", f"Stop-Computer -ComputerName {ip} -Force"], check=True, capture_output=True)
        print(result.stdout)  # Log the output for debugging
        return True
    except subprocess.CalledProcessError as e:
        print(f"An error was caught during PC shutdown! Error Code: {e}")
        return False
    
# pang gawa mismo lahat ng tables.

def init_db():
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            uid INTEGER PRIMARY KEY AUTOINCREMENT,
            email_address TEXT NOT NULL UNIQUE,
            username TEXT NOT NULL UNIQUE,
            password TEXT NOT NULL
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS pc_client (
            uid INTEGER NOT NULL,
            host_computers TEXT NOT NULL,
            time_start TEXT NOT NULL,
            time_end TEXT NOT NULL,
            status INTEGER NOT NULL,
            ip_address TEXT,
            FOREIGN KEY (uid) REFERENCES users(uid)
        )
    ''')

    cursor.execute('''
    CREATE TABLE IF NOT EXISTS profits (
        uid INTEGER NOT NULL,
        host_computers TEXT NOT NULL,
        earnings REAL NOT NULL,
        FOREIGN KEY (host_computers) REFERENCES pc_client(host_computers)
        FOREIGN KEY (uid) REFERENCES users(uid)
        )
    ''')

    conn.commit()
    conn.close()

init_db()


# reroute to main webpage.

@app.route('/')
def aaa(): return redirect(url_for('home_page'))

# main webpage.

@app.route('/home')
def home_page(): return render_template("home_page.html")

# main page pag naka-logged in ka.

@app.route('/home/<username>', methods=['GET', 'POST'])
def user_home_page(username):
    logged_in_user = session.get('username')
    if logged_in_user != username: return redirect(url_for('login_page'))

    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()

    cursor.execute("SELECT uid FROM users WHERE username = ?", (username,))
    user = cursor.fetchone()

    if not user: return "User not found", 404

    user_id = user[0]

    if request.method == 'POST':
        cursor.execute("DELETE FROM profits WHERE uid = ?", (user_id,))
        conn.commit()

    cursor.execute("""
        SELECT SUM(earnings)
        FROM profits
        WHERE uid = ?
    """, (user_id,))
    total_earnings = cursor.fetchone()[0] or 0.0

    cursor.execute("""
        SELECT pc.host_computers, p.earnings
        FROM pc_client pc
        LEFT JOIN profits p ON pc.host_computers = p.host_computers AND pc.uid = p.uid
        WHERE pc.uid = ?
    """, (user_id,))
    pc_client_manager = cursor.fetchall()

    conn.close()

    return render_template('auth_home_page.html', username=username, total_earnings=total_earnings, pc_client_manager=pc_client_manager)

# webpage for signup

@app.route('/signup', methods=['GET', 'POST'])
def signup_page():
    promt_message = None

    if request.method == 'POST':
        email_address = request.form['email_address']
        username      = request.form['username']
        password      = request.form['password']

        try:
            with sqlite3.connect('users.db', timeout = 10) as conn:
                cursor = conn.cursor()
                cursor.execute('INSERT INTO users (email_address, username, password) VALUES (?, ?, ?)', (email_address, username, password))
                conn.commit()

            promt_message = f'User {username} saved successfully!'

        except sqlite3.IntegrityError as e:
            if 'email_address' in str(e):
                promt_message = 'That email address is already registered.'
            elif 'username' in str(e):
                promt_message = 'That username is already taken.'
            else:
                promt_message = 'Something went wrong. Please try again.'

    return render_template('signup_page.html', promt_message = promt_message)

# webpage for login

@app.route('/login', methods=['GET', 'POST'])
def login_page():
    promt_message = None
    if request.method == 'POST':
        email_address = request.form['email_address']
        password      = request.form['password']
        conn          = sqlite3.connect('users.db')
        cursor        = conn.cursor()

        cursor.execute('SELECT * FROM users WHERE email_address = ? AND password = ?', (email_address, password))
        user = cursor.fetchone()

        if user:
            session['username'] = user[2]
            session['user_id'] = user[0]

            if user[2] == 'admin':
                return redirect(url_for('admin_home_page'))  # 👈 Redirect admin to /admin
            else:
                return redirect(url_for('user_home_page', username=user[2]))
        else:
            promt_message = "Invalid email address or password."

        conn.close()

    return render_template('login_page.html', promt_message=promt_message)

# main webpage para sa organize mismo ng mga pc

@app.route('/pc_client_manager/<username>', methods=['GET', 'POST'])
def pc_client_manager(username):
    if session.get('username') != username: return redirect(url_for('login_page'))

    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()

    cursor.execute("SELECT uid FROM users WHERE username = ?", (username,))
    user = cursor.fetchone()

    if not user: return "User not found", 404

    user_id = user[0]

    if request.method == 'POST' and 'host_computers' in request.form and 'update_time' not in request.form:
        host_computers = request.form['host_computers']
        ip_address = request.form['ip_address']

        cursor.execute("SELECT * FROM pc_client WHERE host_computers = ? AND uid = ?", (host_computers, user_id))
        existing_pc = cursor.fetchone()

        if existing_pc:
            flash(f"PC with host computer '{host_computers}' already exists.", "error")
        else:
            time_start = ""
            time_end = ""

            cursor.execute("""
                INSERT INTO pc_client (host_computers, time_start, time_end, status, ip_address, uid)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (host_computers, time_start, time_end, 0, ip_address, user_id))

            conn.commit()
            flash(f"PC '{host_computers}' added successfully.", "info")

    if request.method == 'POST' and 'update_time' in request.form:
        host_computers = request.form['host_computers_to_update']
        new_time_start = request.form['new_time_start']
        new_time_end   = request.form['new_time_end']
        earnings       = request.form['earnings']

        cursor.execute("SELECT * FROM pc_client WHERE host_computers = ? AND uid = ?", (host_computers, user_id))
        existing_pc = cursor.fetchone()

        if existing_pc:
            pc_id = existing_pc[0]

            cursor.execute("""
                UPDATE pc_client 
                SET time_start = ?, time_end = ?, status = 1 
                WHERE host_computers = ? AND uid = ?
            """, (new_time_start, new_time_end, host_computers, user_id))

            cursor.execute("""
                INSERT INTO profits (uid, host_computers, earnings)
                VALUES (?, ?, ?)
            """, (user_id, host_computers, earnings))

            conn.commit()
            flash(f"PC '{host_computers}' updated and earnings recorded.", "info")
        else: flash(f"PC '{host_computers}' not found for update.", "error")

    if request.method == 'POST' and 'remove_host_computers' in request.form:
        host_to_remove = request.form['remove_host_computers']

        cursor.execute("SELECT * FROM pc_client WHERE host_computers = ? AND uid = ?", (host_to_remove, user_id))
        pc_to_remove = cursor.fetchone()

        if pc_to_remove:
            cursor.execute("DELETE FROM pc_client WHERE host_computers = ? AND uid = ?", (host_to_remove, user_id))
            conn.commit()
            flash(f"PC '{host_to_remove}' has been removed.", "info")
        else: flash(f"PC '{host_to_remove}' not found.", "error")

    cursor.execute("SELECT * FROM pc_client WHERE uid = ?", (user_id,))
    pc_client_manager = cursor.fetchall()
    conn.close()

    now_time = datetime.now().strftime('%H:%M')
    return render_template('budget_page.html', username=username, pc_clients=pc_client_manager, now_time=now_time)

# this part yung logic behind nung shutdown button, bali both sinasara
# tapos inaupdate lang yung table sa part nato.

@app.route('/turn_off_pc', methods=['POST'])
def turn_off_pc():
    if 'user_id' not in session: return "User not logged in", 401

    host_computers = request.form.get('host_computers')

    if not host_computers: return "Missing data", 400

    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()

    cursor.execute("""
        UPDATE pc_client 
        SET status = 0,
            time_start = '',
            time_end = ''
        WHERE uid = ? AND host_computers = ?
    """, (session['user_id'], host_computers))

    conn.commit()
    conn.close()

    return redirect(url_for('pc_client_manager', username=session.get('username')))

# admin page, ability to either individually remove a specific data or entire user lang dito...
@app.route('/admin', methods=['GET', 'POST'])
def admin_home_page():
    if session.get('username') != 'admin': return redirect(url_for('login_page'))

    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()

    if request.method == 'POST':
        user_id_to_remove = request.form.get('user_id')
        if user_id_to_remove:
            try:
                user_id_to_remove = int(user_id_to_remove)

                cursor.execute("DELETE FROM profits WHERE uid = ?", (user_id_to_remove,))
                cursor.execute("DELETE FROM pc_client WHERE uid = ?", (user_id_to_remove,))
                cursor.execute("DELETE FROM users WHERE uid = ?", (user_id_to_remove,))

                conn.commit()
                flash(f"User with ID {user_id_to_remove} and all of its data have been deleted.", "info")
            except ValueError:
                flash("Invalid User ID entered. Please try again.", "error")
            except Exception as e:
                flash(f"An error occurred: {e}", "error")

    cursor.execute("""
        SELECT u.uid, u.email_address, u.username, pc.host_computers, pc.time_start, pc.time_end, pc.status, pc.ip_address, p.earnings
        FROM users u
        LEFT JOIN pc_client pc ON u.uid = pc.uid
        LEFT JOIN profits p ON pc.host_computers = p.host_computers AND u.uid = p.uid
    """)
    overall_database = cursor.fetchall()
    conn.close()

    return render_template('admin_home_page.html', overall_database=overall_database)

if __name__ == "__main__": app.run(debug=True)