from flask import Blueprint, render_template, request, redirect, url_for, session, flash

auth_bp = Blueprint('auth', __name__)

# Hard-coded demo credentials
DEMO_USERNAME = 'admin'
DEMO_PASSWORD = 'admin'


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if session.get('logged_in'):
        return redirect(url_for('dashboard.dashboard'))

    if request.method == 'POST':
        username = request.form.get('username', '')
        password = request.form.get('password', '')

        if username == DEMO_USERNAME and password == DEMO_PASSWORD:
            session['logged_in'] = True
            session['username'] = username
            return redirect(url_for('dashboard.dashboard'))
        else:
            flash('Invalid username or password.', 'error')

    return render_template('login.html')


@auth_bp.route('/logout', methods=['POST'])
def logout():
    session.clear()
    return redirect(url_for('auth.login'))
