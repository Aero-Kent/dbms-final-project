from flask import Flask, redirect, url_for, render_template, request, session, flash, get_flashed_messages
import sqlite3
import os
import subprocess

app = Flask(__name__)
app.secret_key = 'your_secret_key'

def turn_off_pc_windows(ip):
    try:
        subprocess.run(["powershell", "-Command", f"Stop-Computer -ComputerName {ip} -Force"], check=True)
    except subprocess.CalledProcessError as e:
        print(f"An error was caught during PC shutdown! Error Code : {e}")

@app.route('/turn_off_pc', methods=['POST'])
def turn_off_pc():
    ip_address = request.form.get('ip_address')

    if not ip_address:
        return "IP address required", 400
    
    turn_off_pc_windows(ip_address)
    flash("PC is being turned off.", "info")
    return redirect(url_for('user_items', username=session.get('username')))

def init_db():
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email_address TEXT NOT NULL UNIQUE,
            username TEXT NOT NULL UNIQUE,
            password TEXT NOT NULL
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            uid INTEGER NOT NULL,
            host_computers TEXT NOT NULL,
            time_start TEXT NOT NULL,
            time_end TEXT NOT NULL,
            status INTEGER NOT NULL,
            ip_address TEXT,
            FOREIGN KEY (uid) REFERENCES users(id)
        )
    ''')

    conn.commit()
    conn.close()
init_db()

@app.route('/')
def aaa(): return redirect(url_for('home_page'))

@app.route('/home')
def home_page(): return render_template("home_page.html")

@app.route('/home-<username>')
def user_home_page(username):
    logged_in_user = session.get('username')
    if logged_in_user != username:
        return redirect(url_for('login_page'))
    return render_template("auth_home_page.html", username=username)

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
            return redirect(url_for('user_home_page', username = user[2]))
        else: promt_message = "Invalid email address or password."

        conn.close()

    return render_template('login_page.html', promt_message = promt_message)


@app.route('/about')
def about_page(): return render_template("about_page.html")

@app.route('/<username>/items', methods=['GET', 'POST'])
def user_items(username):

    if session.get('username') != username:
        return redirect(url_for('login_page'))

    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()

    cursor.execute("SELECT id FROM users WHERE username = ?", (username,))
    user = cursor.fetchone()
    if not user: return "User not found", 404

    user_id = user[0]

    if request.method == 'POST' and 'host_computers' in request.form:
        host_computers = request.form['host_computers']
        time_start     = request.form['time_start']
        time_end       = request.form['time_end']
        status         = 1 if 'status' in request.form else 0
        ip_address     = request.form['ip_address']

        cursor.execute("INSERT INTO items (uid, host_computers, time_start, time_end, status, ip_address) VALUES (?, ?, ?, ?, ?, ?)",
                       (user_id, host_computers, time_start, time_end, status, ip_address))
        conn.commit()

    elif 'shutdown' in request.form:
        ip_address_to_shutdown = request.form['ip_address']
        turn_off_pc_windows(ip_address_to_shutdown)
        item_id = request.form['item_id']
        cursor.execute("UPDATE items SET status = 0 WHERE id = ?", (item_id,))
        conn.commit()
        flash("PC is being turned off.", "info")

    elif request.method == 'POST' and 'item_id' in request.form:
        item_id = request.form['item_id']
        status = request.form.get('status', 0)
        cursor.execute("UPDATE items SET status = ? WHERE id = ?", (status, item_id))
        conn.commit()

    cursor.execute("SELECT * FROM items WHERE uid = ?", (user_id,))
    user_items = cursor.fetchall()
    conn.close()

    return render_template('budget_page.html', username=username, items=user_items)

if __name__ == "__main__":
    app.run(debug=True)