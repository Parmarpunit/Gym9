from flask import Flask, request, jsonify
import sqlite3, hashlib, datetime

app = Flask(__name__)
DB_FILE = "gym_database.db"

def init_db():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    tables = [
        'CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY, username TEXT UNIQUE, email TEXT UNIQUE, password_hash TEXT, full_name TEXT, phone TEXT, membership_type TEXT DEFAULT "basic", created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)',
        'CREATE TABLE IF NOT EXISTS memberships (id INTEGER PRIMARY KEY, user_id INTEGER, plan_type TEXT, duration TEXT, start_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP, end_date TIMESTAMP, status TEXT DEFAULT "pending", price REAL, payment_status TEXT DEFAULT "pending", customer_name TEXT, customer_email TEXT, transaction_id TEXT, FOREIGN KEY (user_id) REFERENCES users (id))',
        'CREATE TABLE IF NOT EXISTS bmi_records (id INTEGER PRIMARY KEY, user_id INTEGER, height REAL, weight REAL, bmi REAL, category TEXT, recorded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, FOREIGN KEY (user_id) REFERENCES users (id))',
        'CREATE TABLE IF NOT EXISTS contact_messages (id INTEGER PRIMARY KEY, name TEXT, email TEXT, message TEXT, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)'
    ]
    for table in tables:
        cursor.execute(table)
    conn.commit()
    conn.close()

def db_execute(query, params=(), fetch=False):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute(query, params)
    if fetch:
        result = cursor.fetchall()
    else:
        conn.commit()
        result = cursor.lastrowid
    conn.close()
    return result

def get_price(plan, duration):
    prices = {"BASIC": {"1 month": 2400, "3 months": 6900, "6 months": 13800, "1 year": 24200},
              "PREMIUM": {"1 month": 4100, "3 months": 11900, "6 months": 23000, "1 year": 41000},
              "VIP": {"1 month": 8300, "3 months": 24900, "6 months": 47200, "1 year": 83000}}
    return prices.get(plan.upper(), prices["BASIC"]).get(duration, 2400)

def get_end_date(duration):
    if not duration: return None
    start = datetime.datetime.now()
    if 'month' in duration.lower():
        months = int(duration.split()[0])
        return start + datetime.timedelta(days=months * 30)
    elif 'year' in duration.lower():
        years = int(duration.split()[0])
        return start + datetime.timedelta(days=years * 365)
    elif 'day' in duration.lower():
        days = int(duration.split()[0])
        return start + datetime.timedelta(days=days)
    return None

@app.after_request
def cors(response):
    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['Access-Control-Allow-Methods'] = 'GET, POST, OPTIONS'
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type'
    return response

@app.route('/api/health')
def health():
    return jsonify({"status": "healthy"})

@app.route('/api/register', methods=['POST'])
def register():
    data = request.get_json()
    try:
        user_id = db_execute('INSERT INTO users (username, email, password_hash, full_name, phone) VALUES (?, ?, ?, ?, ?)', 
                           (data['username'], data['email'], hashlib.sha256(data['password'].encode()).hexdigest(), data['full_name'], data.get('phone', '')))
        return jsonify({"success": True, "user_id": user_id, "message": "Registration successful"})
    except sqlite3.IntegrityError:
        return jsonify({"success": False, "message": "Username or email already exists"})

@app.route('/api/login', methods=['POST'])
def login():
    data = request.get_json()
    users = db_execute('SELECT id, username, email, full_name, membership_type FROM users WHERE (username = ? OR email = ?) AND password_hash = ?', 
                      (data['username'], data['username'], hashlib.sha256(data['password'].encode()).hexdigest()), fetch=True)
    if users:
        user = users[0]
        return jsonify({"success": True, "user": {"id": user[0], "username": user[1], "email": user[2], "full_name": user[3], "membership_type": user[4]}, "message": "Login successful"})
    return jsonify({"success": False, "message": "Invalid credentials"})

@app.route('/api/bmi', methods=['POST'])
def save_bmi():
    data = request.get_json()
    db_execute('INSERT INTO bmi_records (user_id, height, weight, bmi, category) VALUES (?, ?, ?, ?, ?)', 
              (data['user_id'], data['height'], data['weight'], data['bmi'], data['category']))
    return jsonify({"success": True, "message": "BMI record saved successfully"})

@app.route('/api/contact', methods=['POST'])
def contact():
    data = request.get_json()
    db_execute('INSERT INTO contact_messages (name, email, message) VALUES (?, ?, ?)', 
              (data['name'], data['email'], data['message']))
    return jsonify({"success": True, "message": "Message sent successfully"})

@app.route('/api/user/bmi-history')
def bmi_history():
    user_id = request.args['user_id']
    records = db_execute('SELECT height, weight, bmi, category, recorded_at FROM bmi_records WHERE user_id = ? ORDER BY recorded_at DESC LIMIT 10', (user_id,), fetch=True)
    return jsonify({"success": True, "records": [{"height": r[0], "weight": r[1], "bmi": r[2], "category": r[3], "recorded_at": r[4]} for r in records]})

@app.route('/api/user/membership')
def membership():
    user_id = request.args['user_id']
    records = db_execute('SELECT plan_type, start_date, end_date, status, duration, price, payment_status FROM memberships WHERE user_id = ? ORDER BY start_date DESC, id DESC LIMIT 1', (user_id,), fetch=True)
    if records:
        r = records[0]
        return jsonify({"success": True, "membership": {"plan_type": r[0], "start_date": r[1], "end_date": r[2], "status": r[3], "duration": r[4], "price": r[5], "payment_status": r[6]}})
    return jsonify({"success": True, "membership": None})

@app.route('/api/user/memberships')
def memberships():
    user_id = request.args['user_id']
    records = db_execute('SELECT id, plan_type, duration, start_date, end_date, status, price, payment_status FROM memberships WHERE user_id = ? ORDER BY start_date DESC', (user_id,), fetch=True)
    return jsonify({"success": True, "memberships": [{"id": r[0], "plan_type": r[1], "duration": r[2], "start_date": r[3], "end_date": r[4], "status": r[5], "price": r[6], "payment_status": r[7]} for r in records]})

@app.route('/api/buy_membership', methods=['POST'])
def buy_membership():
    data = request.get_json()
    users = db_execute('SELECT id FROM users WHERE username = ?', (data['username'],), fetch=True)
    if not users:
        return jsonify({"success": False, "message": "User not found"}), 404
    user_id = users[0][0]
    price = get_price(data['plan'], data['duration'])
    end_date = get_end_date(data['duration'])
    db_execute('INSERT INTO memberships (user_id, plan_type, duration, start_date, end_date, status, price, payment_status) VALUES (?, ?, ?, ?, ?, ?, ?, ?)', 
              (user_id, data['plan'], data['duration'], datetime.datetime.now(), end_date, 'active', price, 'paid'))
    return jsonify({"success": True, "message": "Membership purchased successfully"})

@app.route('/api/submit_payment', methods=['POST'])
def submit_payment():
    data = request.get_json()
    try:
        # Get user_id from username
        users = db_execute('SELECT id FROM users WHERE username = ?', (data['username'],), fetch=True)
        if not users:
            return jsonify({"success": False, "message": "User not found"}), 404
        user_id = users[0][0]
        
        # Calculate price
        price = get_price(data['plan_type'], data['duration'])
        
        # Insert membership record with pending status
        membership_id = db_execute('INSERT INTO memberships (user_id, plan_type, duration, start_date, end_date, status, price, payment_status, customer_name, customer_email, transaction_id) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)', 
                              (user_id, data['plan_type'], data['duration'], datetime.datetime.now(), None, 'pending', price, 'pending', data['customer_name'], data['customer_email'], data['transaction_id']))
        
        return jsonify({"success": True, "message": "Payment details submitted successfully", "membership_id": membership_id})
    except Exception as e:
        return jsonify({"success": False, "message": f"Error submitting payment: {str(e)}"}), 500

@app.route('/api/membership', methods=['POST'])
def save_membership():
    data = request.get_json()
    end_date = get_end_date(data.get('duration'))
    db_execute('INSERT INTO memberships (user_id, plan_type, duration, start_date, end_date, status, price, payment_status) VALUES (?, ?, ?, ?, ?, ?, ?, ?)', 
              (data['user_id'], data['plan_type'], data.get('duration'), datetime.datetime.now(), end_date, 'active', 0.0, 'pending'))
    return jsonify({"success": True, "message": "Membership saved successfully"})

@app.route('/api/admin/payment_analytics')
def payment_analytics():
    # Get payment statistics
    total_pending = len(db_execute('SELECT id FROM memberships WHERE status = "pending"', fetch=True))
    total_active = len(db_execute('SELECT id FROM memberships WHERE status = "active"', fetch=True))
    total_rejected = len(db_execute('SELECT id FROM memberships WHERE status = "rejected"', fetch=True))
    
    # Get revenue data
    total_revenue = sum([row[0] for row in db_execute('SELECT price FROM memberships WHERE status = "active" AND payment_status = "paid"', fetch=True)])
    
    # Get recent payments (last 7 days)
    recent_payments = db_execute('''
        SELECT m.id, u.username, m.plan_type, m.price, m.start_date, m.status, m.payment_status
        FROM memberships m JOIN users u ON m.user_id = u.id 
        WHERE m.start_date >= datetime("now", "-7 days")
        ORDER BY m.start_date DESC
    ''', fetch=True)
    
    # Get plan distribution
    plan_distribution = db_execute('''
        SELECT plan_type, COUNT(*) as count, SUM(price) as revenue
        FROM memberships WHERE status = "active" AND payment_status = "paid"
        GROUP BY plan_type
    ''', fetch=True)
    
    return jsonify({
        "success": True,
        "analytics": {
            "total_pending": total_pending,
            "total_active": total_active,
            "total_rejected": total_rejected,
            "total_revenue": total_revenue,
            "recent_payments": [{"id": p[0], "username": p[1], "plan_type": p[2], "price": p[3], "start_date": p[4], "status": p[5], "payment_status": p[6]} for p in recent_payments],
            "plan_distribution": [{"plan_type": p[0], "count": p[1], "revenue": p[2]} for p in plan_distribution]
        }
    })

@app.route('/api/admin/bulk_approve', methods=['POST'])
def bulk_approve():
    data = request.get_json()
    membership_ids = data.get('membership_ids', [])
    
    if not membership_ids:
        return jsonify({"success": False, "message": "No memberships selected"})
    
    approved_count = 0
    for membership_id in membership_ids:
        # Get membership details
        membership = db_execute('SELECT user_id, plan_type, duration FROM memberships WHERE id = ?', (membership_id,), fetch=True)
        if membership:
            membership = membership[0]
            end_date = get_end_date(membership[2])
            db_execute('UPDATE memberships SET status = ?, payment_status = ?, end_date = ? WHERE id = ?', 
                      ('active', 'paid', end_date, membership_id))
            approved_count += 1
    
    return jsonify({"success": True, "message": f"Successfully approved {approved_count} memberships"})

@app.route('/api/admin/bulk_reject', methods=['POST'])
def bulk_reject():
    data = request.get_json()
    membership_ids = data.get('membership_ids', [])
    
    if not membership_ids:
        return jsonify({"success": False, "message": "No memberships selected"})
    
    rejected_count = 0
    for membership_id in membership_ids:
        db_execute('UPDATE memberships SET status = ?, payment_status = ? WHERE id = ?', 
                  ('rejected', 'rejected', membership_id))
        rejected_count += 1
    
    return jsonify({"success": True, "message": f"Successfully rejected {rejected_count} memberships"})



if __name__ == '__main__':
    init_db()
    app.run(host='0.0.0.0', port=8000, debug=True)