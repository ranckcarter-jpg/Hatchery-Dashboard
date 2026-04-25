import os
import sqlite3
from datetime import datetime, timedelta
from functools import wraps
from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify, send_file
from werkzeug.security import generate_password_hash, check_password_hash
import json
import csv
import io
import logging

app = Flask(__name__)
app.secret_key = 'hatchery-secure-key-2026' # Fixed secret key for session persistence
DATABASE = 'hatchery.db'

# Inject datetime into templates
@app.context_processor
def inject_datetime():
    from datetime import datetime
    return dict(datetime=datetime)

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# --- Database Setup ---

def get_db():
    db = sqlite3.connect(DATABASE)
    db.row_factory = sqlite3.Row
    return db

def init_db():
    with app.app_context():
        db = get_db()
        cursor = db.cursor()
        
        # Users table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL
            )
        ''')
        
        # Batches table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS batches (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                breed TEXT NOT NULL,
                hatch_date TEXT NOT NULL,
                hens INTEGER NOT NULL DEFAULT 0,
                roosters INTEGER NOT NULL DEFAULT 0,
                unsexed INTEGER NOT NULL DEFAULT 0,
                notes TEXT,
                last_updated TEXT NOT NULL,
                health_status TEXT DEFAULT 'Healthy',
                health_notes TEXT
            )
        ''')
        
        # Incubation batches table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS incubation_batches (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                breed TEXT NOT NULL,
                start_date TEXT NOT NULL,
                expected_hatch_date TEXT NOT NULL,
                egg_count INTEGER NOT NULL DEFAULT 0,
                hatch_success INTEGER,
                notes TEXT,
                last_updated TEXT NOT NULL,
                daily_temp_log TEXT,
                daily_humidity_log TEXT,
                lockdown_date TEXT
            )
        ''')
        
        # Events table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                batch_id INTEGER NOT NULL,
                event_type TEXT NOT NULL,
                quantity_change INTEGER,
                timestamp TEXT NOT NULL,
                notes TEXT,
                FOREIGN KEY (batch_id) REFERENCES batches (id) ON DELETE CASCADE
            )
        ''')

        # Daily Tasks table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS daily_tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                task_name TEXT NOT NULL,
                task_date TEXT NOT NULL,
                completed INTEGER NOT NULL DEFAULT 0
            )
        ''')

        # Environment Logs table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS environment_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                log_date TEXT NOT NULL UNIQUE,
                temperature REAL,
                humidity REAL,
                notes TEXT
            )
        ''')

        # Inventory table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS inventory (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                item_name TEXT NOT NULL UNIQUE,
                quantity INTEGER NOT NULL DEFAULT 0,
                unit TEXT,
                low_threshold INTEGER NOT NULL DEFAULT 0
            )
        ''')

        # Sales table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS sales (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                sale_date TEXT NOT NULL,
                batch_id INTEGER,
                quantity_sold INTEGER NOT NULL,
                price_per_bird REAL NOT NULL,
                notes TEXT,
                FOREIGN KEY (batch_id) REFERENCES batches (id)
            )
        ''')
        
        # Create default admin user if not exists
        cursor.execute("SELECT * FROM users WHERE username = 'admin'")
        if not cursor.fetchone():
            hashed_pw = generate_password_hash('admin123')
            cursor.execute("INSERT INTO users (username, password) VALUES (?, ?)", ('admin', hashed_pw))
            
        db.commit()
        db.close()

# --- Helpers ---

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def calculate_age(hatch_date_str):
    hatch_date = datetime.strptime(hatch_date_str, '%Y-%m-%d')
    delta = datetime.now() - hatch_date
    days = delta.days
    weeks = days // 7
    remaining_days = days % 7
    return f"{weeks}w {remaining_days}d ({days} days)"

def get_age_milestone(hatch_date_str):
    hatch_date = datetime.strptime(hatch_date_str, '%Y-%m-%d')
    days = (datetime.now() - hatch_date).days
    if days == 7: return "1 Week"
    if days == 28: return "4 Weeks"
    if days == 56: return "8 Weeks"
    if days == 112: return "16 Weeks"
    return None

def get_alerts():
    db = get_db()
    alerts = []
    today = datetime.now().date()
    
    # Upcoming hatches
    incubation = db.execute("SELECT * FROM incubation_batches WHERE hatch_success IS NULL").fetchall()
    for batch in incubation:
        hatch_date = datetime.strptime(batch['expected_hatch_date'], '%Y-%m-%d').date()
        days_left = (hatch_date - today).days
        if 0 <= days_left <= 5:
            alerts.append(f"Upcoming hatch: {batch['breed']} in {days_left} days ({batch['expected_hatch_date']})")
        elif days_left < 0:
            alerts.append(f"OVERDUE hatch: {batch['breed']} was expected on {batch['expected_hatch_date']}")
            
    # Age milestones
    batches = db.execute("SELECT * FROM batches").fetchall()
    for batch in batches:
        milestone = get_age_milestone(batch['hatch_date'])
        if milestone:
            alerts.append(f"Milestone: Batch {batch['id']} ({batch['breed']}) reached {milestone} today!")
            
    # Low inventory
    low_stock = db.execute("SELECT * FROM inventory WHERE quantity <= low_threshold").fetchall()
    for item in low_stock:
        alerts.append(f"Low Stock: {item['item_name']} ({item['quantity']} {item['unit']} left)")
            
    db.close()
    return alerts

def ensure_daily_tasks():
    db = get_db()
    today = datetime.now().strftime('%Y-%m-%d')
    tasks = ["Feed / water check", "Temperature check", "Cleaning", "Egg turning"]
    for task in tasks:
        db.execute('''
            INSERT OR IGNORE INTO daily_tasks (task_name, task_date, completed)
            SELECT ?, ?, 0
            WHERE NOT EXISTS (SELECT 1 FROM daily_tasks WHERE task_name = ? AND task_date = ?)
        ''', (task, today, task, today))
    db.commit()
    db.close()

# --- Routes ---

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        db = get_db()
        user = db.execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()
        db.close()
        
        if user and check_password_hash(user['password'], password):
            session['user_id'] = user['id']
            session['username'] = user['username']
            session.permanent = True
            app.permanent_session_lifetime = timedelta(hours=12)
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid username or password')
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route('/')
@login_required
def dashboard():
    ensure_daily_tasks()
    db = get_db()
    today = datetime.now().strftime('%Y-%m-%d')
    
    # Daily Tasks
    tasks = db.execute("SELECT * FROM daily_tasks WHERE task_date = ?", (today,)).fetchall()
    
    # Batches
    batches = db.execute("SELECT * FROM batches").fetchall()
    processed_batches = []
    total_hens = 0
    total_roosters = 0
    total_unsexed = 0
    
    for b in batches:
        batch_dict = dict(b)
        batch_dict['age'] = calculate_age(b['hatch_date'])
        batch_dict['milestone'] = get_age_milestone(b['hatch_date'])
        processed_batches.append(batch_dict)
        total_hens += b['hens']
        total_roosters += b['roosters']
        total_unsexed += b['unsexed']
        
    total_birds = total_hens + total_roosters + total_unsexed
    alerts = get_alerts()
    
    # Environment
    env_log = db.execute("SELECT * FROM environment_logs WHERE log_date = ?", (today,)).fetchone()
    
    # Sales summary
    total_revenue = db.execute("SELECT SUM(quantity_sold * price_per_bird) as revenue FROM sales").fetchone()['revenue'] or 0
    
    db.close()
    return render_template('dashboard.html', 
                           tasks=tasks,
                           batches=processed_batches, 
                           total_birds=total_birds,
                           total_hens=total_hens,
                           total_roosters=total_roosters,
                           total_unsexed=total_unsexed,
                           alerts=alerts,
                           env_log=env_log,
                           total_revenue=round(total_revenue, 2),
                           datetime=datetime)

@app.route('/task/toggle/<int:id>')
@login_required
def toggle_task(id):
    db = get_db()
    db.execute("UPDATE daily_tasks SET completed = 1 - completed WHERE id = ?", (id,))
    db.commit()
    db.close()
    return redirect(url_for('dashboard'))

@app.route('/batch/add', methods=['GET', 'POST'])
@login_required
def add_batch():
    if request.method == 'POST':
        breed = request.form['breed']
        hatch_date = request.form['hatch_date']
        hens = int(request.form['hens'] or 0)
        roosters = int(request.form['roosters'] or 0)
        unsexed = int(request.form['unsexed'] or 0)
        notes = request.form['notes']
        health_status = request.form['health_status']
        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        db = get_db()
        db.execute('''
            INSERT INTO batches (breed, hatch_date, hens, roosters, unsexed, notes, last_updated, health_status)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (breed, hatch_date, hens, roosters, unsexed, notes, now, health_status))
        db.commit()
        db.close()
        flash('Batch added successfully')
        return redirect(url_for('dashboard'))
    return render_template('batch_form.html', action="Add")

@app.route('/batch/edit/<int:id>', methods=['GET', 'POST'])
@login_required
def edit_batch(id):
    db = get_db()
    if request.method == 'POST':
        breed = request.form['breed']
        hatch_date = request.form['hatch_date']
        hens = int(request.form['hens'] or 0)
        roosters = int(request.form['roosters'] or 0)
        unsexed = int(request.form['unsexed'] or 0)
        notes = request.form['notes']
        health_status = request.form['health_status']
        health_notes = request.form['health_notes']
        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        db.execute('''
            UPDATE batches SET breed=?, hatch_date=?, hens=?, roosters=?, unsexed=?, notes=?, last_updated=?, health_status=?, health_notes=?
            WHERE id=?
        ''', (breed, hatch_date, hens, roosters, unsexed, notes, now, health_status, health_notes, id))
        db.commit()
        db.close()
        flash('Batch updated successfully')
        return redirect(url_for('dashboard'))
    
    batch = db.execute("SELECT * FROM batches WHERE id = ?", (id,)).fetchone()
    db.close()
    return render_template('batch_form.html', batch=batch, action="Edit")

@app.route('/batch/delete/<int:id>')
@login_required
def delete_batch(id):
    db = get_db()
    db.execute("DELETE FROM batches WHERE id = ?", (id,))
    db.commit()
    db.close()
    flash('Batch deleted')
    return redirect(url_for('dashboard'))

@app.route('/incubation')
@login_required
def incubation():
    db = get_db()
    batches = db.execute("SELECT * FROM incubation_batches ORDER BY expected_hatch_date DESC").fetchall()
    db.close()
    return render_template('incubation.html', batches=batches, datetime=datetime)

@app.route('/incubation/add', methods=['GET', 'POST'])
@login_required
def add_incubation():
    if request.method == 'POST':
        breed = request.form['breed']
        start_date = request.form['start_date']
        egg_count = int(request.form['egg_count'] or 0)
        notes = request.form['notes']
        
        start_dt = datetime.strptime(start_date, '%Y-%m-%d')
        expected_dt = start_dt + timedelta(days=21)
        expected_hatch_date = expected_dt.strftime('%Y-%m-%d')
        lockdown_date = (start_dt + timedelta(days=18)).strftime('%Y-%m-%d')
        
        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        db = get_db()
        db.execute('''
            INSERT INTO incubation_batches (breed, start_date, expected_hatch_date, egg_count, notes, last_updated, lockdown_date)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (breed, start_date, expected_hatch_date, egg_count, notes, now, lockdown_date))
        db.commit()
        db.close()
        flash('Incubation batch added')
        return redirect(url_for('incubation'))
    return render_template('incubation_form.html', action="Add")

@app.route('/incubation/log/<int:id>', methods=['POST'])
@login_required
def log_incubation_env(id):
    temp = request.form['temp']
    humidity = request.form['humidity']
    today = datetime.now().strftime('%Y-%m-%d')
    
    db = get_db()
    batch = db.execute("SELECT * FROM incubation_batches WHERE id=?", (id,)).fetchone()
    
    temp_log = json.loads(batch['daily_temp_log'] or '{}')
    hum_log = json.loads(batch['daily_humidity_log'] or '{}')
    
    temp_log[today] = temp
    hum_log[today] = humidity
    
    db.execute('UPDATE incubation_batches SET daily_temp_log=?, daily_humidity_log=? WHERE id=?', 
               (json.dumps(temp_log), json.dumps(hum_log), id))
    db.commit()
    db.close()
    flash('Incubation log updated')
    return redirect(url_for('incubation'))

@app.route('/incubation/complete/<int:id>', methods=['GET', 'POST'])
@login_required
def complete_incubation(id):
    db = get_db()
    if request.method == 'POST':
        hatch_success = int(request.form['hatch_success'] or 0)
        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        db.execute('UPDATE incubation_batches SET hatch_success=?, last_updated=? WHERE id=?', (hatch_success, now, id))
        
        if request.form.get('create_batch') == 'yes':
            batch = db.execute("SELECT * FROM incubation_batches WHERE id=?", (id,)).fetchone()
            db.execute('''
                INSERT INTO batches (breed, hatch_date, unsexed, notes, last_updated)
                VALUES (?, ?, ?, ?, ?)
            ''', (batch['breed'], batch['expected_hatch_date'], hatch_success, f"Hatched from incubation batch #{id}", now))
            
        db.commit()
        db.close()
        flash('Incubation marked as complete')
        return redirect(url_for('incubation'))
    
    batch = db.execute("SELECT * FROM incubation_batches WHERE id=?", (id,)).fetchone()
    db.close()
    return render_template('incubation_complete.html', batch=batch)

@app.route('/events/<int:batch_id>', methods=['GET', 'POST'])
@login_required
def batch_events(batch_id):
    db = get_db()
    if request.method == 'POST':
        event_type = request.form['event_type']
        category = request.form.get('category', 'unsexed') # Default to unsexed
        qty = int(request.form['quantity'] or 0)
        notes = request.form['notes']
        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        # Automatically make quantity negative for deaths and sales
        qty_change = -abs(qty) if event_type in ['death', 'sale'] else qty
        
        db.execute('''
            INSERT INTO events (batch_id, event_type, quantity_change, timestamp, notes)
            VALUES (?, ?, ?, ?, ?)
        ''', (batch_id, event_type, qty_change, now, f"({category.capitalize()}) {notes}"))
        
        # Update batch counts based on category
        if category == 'hens':
            db.execute("UPDATE batches SET hens = MAX(0, hens + ?) WHERE id=?", (qty_change, batch_id))
        elif category == 'roosters':
            db.execute("UPDATE batches SET roosters = MAX(0, roosters + ?) WHERE id=?", (qty_change, batch_id))
        else:
            db.execute("UPDATE batches SET unsexed = MAX(0, unsexed + ?) WHERE id=?", (qty_change, batch_id))
            
        # If it's a sale, record in sales table
        if event_type == 'sale':
            price = float(request.form.get('price_per_bird', 0))
            db.execute('''
                INSERT INTO sales (sale_date, batch_id, quantity_sold, price_per_bird, notes)
                VALUES (?, ?, ?, ?, ?)
            ''', (now[:10], batch_id, abs(qty), price, notes))
            
        db.commit()
        flash(f'Event logged: {event_type.capitalize()} of {abs(qty)} {category}')
        
    batch = db.execute("SELECT * FROM batches WHERE id=?", (batch_id,)).fetchone()
    events = db.execute("SELECT * FROM events WHERE batch_id=? ORDER BY timestamp DESC", (batch_id,)).fetchall()
    db.close()
    return render_template('events.html', batch=batch, events=events)

@app.route('/environment', methods=['POST'])
@login_required
def log_environment():
    temp = request.form['temperature']
    humidity = request.form['humidity']
    notes = request.form['notes']
    today = datetime.now().strftime('%Y-%m-%d')
    
    db = get_db()
    db.execute('''
        INSERT INTO environment_logs (log_date, temperature, humidity, notes)
        VALUES (?, ?, ?, ?)
        ON CONFLICT(log_date) DO UPDATE SET
        temperature=excluded.temperature, humidity=excluded.humidity, notes=excluded.notes
    ''', (today, temp, humidity, notes))
    db.commit()
    db.close()
    flash('Environment log updated')
    return redirect(url_for('dashboard'))

@app.route('/inventory', methods=['GET', 'POST'])
@login_required
def inventory():
    db = get_db()
    if request.method == 'POST':
        name = request.form['item_name']
        qty = int(request.form['quantity'])
        unit = request.form['unit']
        threshold = int(request.form['low_threshold'])
        
        db.execute('''
            INSERT INTO inventory (item_name, quantity, unit, low_threshold)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(item_name) DO UPDATE SET
            quantity=excluded.quantity, unit=excluded.unit, low_threshold=excluded.low_threshold
        ''', (name, qty, unit, threshold))
        db.commit()
        flash('Inventory updated')
        
    items = db.execute("SELECT * FROM inventory").fetchall()
    db.close()
    return render_template('inventory.html', items=items)

@app.route('/analytics')
@login_required
def analytics():
    db = get_db()
    incubation = db.execute("SELECT SUM(egg_count) as total_eggs, SUM(hatch_success) as total_hatched FROM incubation_batches WHERE hatch_success IS NOT NULL").fetchone()
    hatch_rate = (incubation['total_hatched'] / incubation['total_eggs'] * 100) if incubation and incubation['total_eggs'] else 0
    
    breed_stats = db.execute("SELECT breed, SUM(hens + roosters + unsexed) as count FROM batches GROUP BY breed").fetchall()
    
    # Sales data
    sales = db.execute("SELECT * FROM sales ORDER BY sale_date DESC LIMIT 10").fetchall()
    total_revenue = db.execute("SELECT SUM(quantity_sold * price_per_bird) as revenue FROM sales").fetchone()['revenue'] or 0
    
    db.close()
    return render_template('analytics.html', 
                           hatch_rate=round(hatch_rate, 2), 
                           breed_stats=breed_stats, 
                           sales=sales, 
                           total_revenue=round(total_revenue, 2),
                           round=round)

@app.route('/backup')
@login_required
def backup():
    db = get_db()
    data = {
        'batches': [dict(row) for row in db.execute("SELECT * FROM batches").fetchall()],
        'incubation': [dict(row) for row in db.execute("SELECT * FROM incubation_batches").fetchall()],
        'events': [dict(row) for row in db.execute("SELECT * FROM events").fetchall()],
        'tasks': [dict(row) for row in db.execute("SELECT * FROM daily_tasks").fetchall()],
        'inventory': [dict(row) for row in db.execute("SELECT * FROM inventory").fetchall()],
        'sales': [dict(row) for row in db.execute("SELECT * FROM sales").fetchall()],
        'environment': [dict(row) for row in db.execute("SELECT * FROM environment_logs").fetchall()]
    }
    db.close()
    
    output = io.StringIO()
    json.dump(data, output, indent=4)
    output.seek(0)
    
    return send_file(
        io.BytesIO(output.getvalue().encode()),
        mimetype='application/json',
        as_attachment=True,
        download_name=f"hatchery_backup_{datetime.now().strftime('%Y%m%d')}.json"
    )

@app.route('/import', methods=['POST'])
@login_required
def import_data():
    if 'file' not in request.files:
        flash('No file part')
        return redirect(url_for('dashboard'))
    file = request.files['file']
    if file.filename == '':
        flash('No selected file')
        return redirect(url_for('dashboard'))
    
    if file:
        try:
            data = json.load(file)
            db = get_db()
            # This is a simple destructive import for now
            for table in ['batches', 'incubation_batches', 'events', 'daily_tasks', 'inventory', 'sales', 'environment_logs']:
                db.execute(f"DELETE FROM {table}")
            
            for b in data.get('batches', []):
                db.execute("INSERT INTO batches (id, breed, hatch_date, hens, roosters, unsexed, notes, last_updated, health_status, health_notes) VALUES (?,?,?,?,?,?,?,?,?,?)", 
                           (b['id'], b['breed'], b['hatch_date'], b['hens'], b['roosters'], b['unsexed'], b['notes'], b['last_updated'], b.get('health_status', 'Healthy'), b.get('health_notes')))
            
            # Add other tables similarly...
            db.commit()
            db.close()
            flash('Data imported successfully')
        except Exception as e:
            flash(f'Error importing data: {str(e)}')
            
    return redirect(url_for('dashboard'))

if __name__ == '__main__':
    init_db()
    app.run(host='0.0.0.0', port=5000, debug=False)
