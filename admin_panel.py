from flask import Flask, request, render_template_string, redirect, url_for
import sqlite3, datetime

app = Flask(__name__)
DB_FILE = 'gym_database.db'

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

def calculate_remaining_months(end_date_str):
    if not end_date_str: return "N/A"
    try:
        end_date = datetime.datetime.fromisoformat(end_date_str.replace('Z', '+00:00'))
        now = datetime.datetime.now()
        if end_date < now: return "Expired"
        remaining_days = (end_date - now).days
        remaining_months = remaining_days // 30
        if remaining_months == 0:
            remaining_weeks = remaining_days // 7
            return f"{remaining_weeks} weeks" if remaining_weeks > 0 else f"{remaining_days} days"
        return f"{remaining_months} months"
    except: return "N/A"

def calculate_time_since(start_date_str):
    if not start_date_str: return 0
    try:
        start_date = datetime.datetime.fromisoformat(start_date_str.replace('Z', '+00:00'))
        now = datetime.datetime.now()
        time_diff = now - start_date
        return int(time_diff.total_seconds() / 3600)  # Return hours
    except: return 0

@app.route('/')
def login():
    return render_template_string('''
    <html>
    <head><title>Admin Login</title>
    <style>
      body { font-family: Arial, sans-serif; background: #f4f7f8; padding: 50px;}
      .login-box { max-width: 300px; margin: auto; background: white; padding: 20px; border-radius: 8px; box-shadow: 0 0 10px #ccc;}
      input[type=text], input[type=password] { width: 100%; padding: 10px; margin: 8px 0; box-sizing: border-box;}
      input[type=submit] { background-color: #007bff; color: white; padding: 10px; border: none; border-radius: 4px; cursor: pointer; width: 100%;}
      input[type=submit]:hover { background-color: #0056b3; }
    </style>
    </head>
    <body>
      <div class="login-box">
      <h2>Admin Login</h2>
      <form method="post" action="/login">
        <input type="text" name="username" placeholder="Username" required>
        <input type="password" name="password" placeholder="Password" required>
        <input type="submit" value="Login">
      </form>
      </div>
    </body>
    </html>
    ''')

@app.route('/login', methods=['POST'])
def handle_login():
    username = request.form.get('username')
    password = request.form.get('password')
    if username == 'punit' and password == 'punit_2312':
        response = redirect('/dashboard')
        response.set_cookie('logged_in', 'true')
        return response
    return redirect('/')

@app.route('/dashboard')
def dashboard():
    if not request.cookies.get('logged_in'):
        return redirect('/')
    
    # Get all memberships with enhanced data
    memberships = db_execute('''
        SELECT m.id, u.username, u.email, m.plan_type, m.duration, m.start_date, m.end_date, m.status, m.user_id, m.price, m.payment_status, m.customer_name, m.customer_email, m.transaction_id
        FROM memberships m JOIN users u ON m.user_id = u.id ORDER BY m.start_date DESC
    ''', fetch=True)
    
    # Get payment statistics
    total_pending = len([m for m in memberships if m[7] == 'pending'])
    total_active = len([m for m in memberships if m[7] == 'active'])
    total_rejected = len([m for m in memberships if m[7] == 'rejected'])
    total_revenue = sum([m[9] for m in memberships if m[7] == 'active' and m[10] == 'paid'])
    
    users = db_execute('SELECT id, username, email FROM users ORDER BY username', fetch=True)
    
    memberships_html = ''
    pending_requests_html = ''
    
    for membership in memberships:
        remaining_months = calculate_remaining_months(membership[6])
        end_date_display = membership[6] if membership[6] else 'N/A'
        status_color = 'green' if membership[7] == 'active' else 'orange' if membership[7] == 'pending' else 'red'
        
        # Regular memberships table
        memberships_html += f'''
        <tr>
            <td>{membership[0]}</td>
            <td>{membership[8]}</td>
            <td>{membership[1]} ({membership[2]})</td>
            <td>{membership[3]}</td>
            <td>{membership[4] or 'N/A'}</td>
            <td>{membership[5]}</td>
            <td>{end_date_display}</td>
            <td>{remaining_months}</td>
            <td style="color: {status_color};">{membership[7]}</td>
            <td>₹{membership[9]:,}</td>
            <td>
                <p><strong>Amount Paid:</strong> ₹{membership[9]:,}</p>
                <a href="/edit_membership?id={membership[0]}">Edit</a> |
                <a href="/delete_membership?id={membership[0]}" onclick="return confirm('Are you sure to delete this membership?')">Delete</a>
            </td>
        </tr>'''
        
        # Pending payment requests with enhanced details
        if membership[7] == 'pending':
            time_since_request = calculate_time_since(membership[5])
            pending_requests_html += f'''
        <tr>
            <td><input type="checkbox" class="pending-checkbox" value="{membership[0]}" onchange="updateSelectedCount()"></td>
            <td>{membership[0]}</td>
            <td>{membership[1]}</td>
            <td>{membership[3]}</td>
            <td>{membership[4]}</td>
            <td>₹{membership[9]:,}</td>
            <td>{membership[11] or 'N/A'}</td>
            <td>{membership[12] or 'N/A'}</td>
            <td>{membership[13] or 'N/A'}</td>
            <td style="color: orange;">{membership[10]}</td>
            <td>{membership[5]}</td>
            <td style="color: {'red' if time_since_request > 24 else 'orange' if time_since_request > 12 else 'green'};">{time_since_request}h ago</td>
            <td>
                <p><strong>Price:</strong> ₹{membership[9]:,}</p>
                <a href="/approve_membership?id={membership[0]}" style="color: green; font-weight: bold;">✓ Approve</a> |
                <a href="/reject_membership?id={membership[0]}" style="color: red; font-weight: bold;">✗ Reject</a> |
                <a href="/view_payment_details?id={membership[0]}" style="color: blue;">View Details</a>
            </td>
        </tr>'''

    users_options = ''
    for user in users:
        users_options += f'<option value="{user[0]}">{user[1]} ({user[2]})</option>'

    return render_template_string('''
    <html>
    <head>
        <title>Admin Dashboard - Payment Management</title>
        <style>
          body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 20px; margin: 0; }
          .container { max-width: 1400px; margin: 0 auto; }
          h1 { color: white; text-align: center; margin-bottom: 30px; font-size: 2.5em; text-shadow: 2px 2px 4px rgba(0,0,0,0.3); }
          
          /* Statistics Cards */
          .stats-container { display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 20px; margin-bottom: 30px; }
          .stat-card { background: white; padding: 20px; border-radius: 15px; box-shadow: 0 8px 25px rgba(0,0,0,0.1); text-align: center; }
          .stat-number { font-size: 2.5em; font-weight: bold; margin-bottom: 10px; }
          .stat-label { color: #666; font-size: 1.1em; }
          .stat-pending { color: #ff6b35; }
          .stat-active { color: #28a745; }
          .stat-rejected { color: #dc3545; }
          .stat-revenue { color: #007bff; }
          
          /* Tables */
          .table-container { background: white; border-radius: 15px; padding: 20px; margin-bottom: 30px; box-shadow: 0 8px 25px rgba(0,0,0,0.1); }
          h2 { color: #333; margin-bottom: 20px; font-size: 1.8em; border-bottom: 3px solid #007bff; padding-bottom: 10px; }
          table { width: 100%; border-collapse: collapse; margin-bottom: 20px; }
          th, td { border: 1px solid #ddd; padding: 12px; text-align: left; }
          th { background: linear-gradient(135deg, #007bff, #0056b3); color: white; font-weight: bold; }
          tr:nth-child(even) { background-color: #f8f9fa; }
          tr:hover { background-color: #e3f2fd; }
          
          /* Form Styling */
          .form-container { background: white; padding: 25px; border-radius: 15px; box-shadow: 0 8px 25px rgba(0,0,0,0.1); max-width: 500px; margin-bottom: 30px; }
          input[type=text], input[type=number], select {
              width: 100%;
              padding: 12px;
              margin: 8px 0;
              box-sizing: border-box;
              border: 2px solid #ddd;
              border-radius: 8px;
              font-size: 1em;

          }
          input[type=text]:focus, input[type=number]:focus, select:focus {
              outline: none;
              border-color: #007bff;
              box-shadow: 0 0 0 3px rgba(0,123,255,0.1);
          }
          input[type=submit] {
              background: linear-gradient(135deg, #007bff, #0056b3);
              color: white;
              padding: 12px 24px;
              border: none;
              border-radius: 8px;
              cursor: pointer;
              width: 100%;
              font-size: 1.1em;
              font-weight: bold;

          }
          input[type=submit]:hover {

              box-shadow: 0 4px 15px rgba(0,123,255,0.3);
          }
          
          /* Action Links */
          a { color: #007bff; text-decoration: none; font-weight: 500; }
          a:hover { text-decoration: underline; }
          
          /* Priority Indicators */
          .priority-high { background-color: #ffebee; }
          .priority-medium { background-color: #fff3e0; }
          .priority-low { background-color: #e8f5e8; }
          
          /* Responsive */
          @media (max-width: 768px) {
              .stats-container { grid-template-columns: 1fr; }
              table { font-size: 0.9em; }
              th, td { padding: 8px; }
          }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>Advanced Payment Management Dashboard</h1>
            
            <!-- Statistics Overview -->
            <div class="stats-container">
                <div class="stat-card">
                    <div class="stat-number stat-pending">{{ total_pending }}</div>
                    <div class="stat-label">Pending Payments</div>
                </div>
                <div class="stat-card">
                    <div class="stat-number stat-active">{{ total_active }}</div>
                    <div class="stat-label">Active Memberships</div>
                </div>
                <div class="stat-card">
                    <div class="stat-number stat-rejected">{{ total_rejected }}</div>
                    <div class="stat-label">Rejected Payments</div>
                </div>
                <div class="stat-card">
                    <div class="stat-number stat-revenue">₹{{ "{0:,.2f}".format(total_revenue) }}</div>
                    <div class="stat-label">Total Revenue</div>
                </div>
            </div>

            <!-- Pending Payment Requests (Priority Section) -->
            <div class="table-container">
                <h2>⚠️ Pending Payment Requests ({{ total_pending }})</h2>
                {% if total_pending > 0 %}
                <div class="bulk-actions" style="margin-bottom: 15px; padding: 10px; background: #f8f9fa; border-radius: 8px;">
                    <button onclick="selectAllPending()" class="btn-select-all" style="background: #6c757d; color: white; border: none; padding: 8px 16px; border-radius: 4px; margin-right: 10px; cursor: pointer;">Select All</button>
                    <button onclick="bulkApprove()" class="btn-bulk-approve" style="background: #28a745; color: white; border: none; padding: 8px 16px; border-radius: 4px; margin-right: 10px; cursor: pointer;">✓ Bulk Approve</button>
                    <button onclick="bulkReject()" class="btn-bulk-reject" style="background: #dc3545; color: white; border: none; padding: 8px 16px; border-radius: 4px; cursor: pointer;">✗ Bulk Reject</button>
                    <span id="selectedCount" style="margin-left: 15px; color: #666;">0 selected</span>
                </div>
                {% endif %}
                <table>
                    <tr><th><input type="checkbox" id="selectAllCheckbox" onchange="toggleAllPending()"></th><th>ID</th><th>Username</th><th>Plan Type</th><th>Duration</th><th>Price</th><th>Customer Name</th><th>Customer Email</th><th>Transaction ID</th><th>Payment Status</th><th>Request Date</th><th>Time Since</th><th>Actions</th></tr>
                    {% if pending_requests_html %}{{ pending_requests_html | safe }}{% else %}<tr><td colspan="13" style="text-align: center; color: #666; padding: 20px;">🎉 No pending payment requests found!</td></tr>{% endif %}
                </table>
            </div>

            <!-- All Memberships -->
            <div class="table-container">
                <h2>All Memberships</h2>
                <table>
                    <tr><th>ID</th><th>User ID</th><th>Username (Email)</th><th>Plan Type</th><th>Duration</th><th>Start Date</th><th>End Date</th><th>Remaining</th><th>Status</th><th>Price</th><th>Actions</th></tr>
                    {% if memberships_html %}{{ memberships_html | safe }}{% else %}<tr><td colspan="11" style="text-align: center; color: #666; padding: 20px;">No memberships found.</td></tr>{% endif %}
                </table>
            </div>

            <!-- Add Membership Form -->
            <div class="form-container">
                <h2>Add New Membership</h2>
                <form method="post" action="/add_membership">
                    <select name="user_id" required>
                        <option value="">Select User</option>
                        {{ users_options | safe }}
                    </select>
                    <input type="text" name="plan_type" placeholder="Plan Type (e.g., basic, premium, vip)" required>
                    <input type="text" name="duration" placeholder="Duration (e.g., 1 month, 6 months, 1 year)">
                    <input type="submit" value="Add Membership">
                </form>
            </div>
        </div>
        
        <script>
        // Bulk action functions
        function selectAllPending() {
            const checkboxes = document.querySelectorAll('.pending-checkbox');
            const selectAllCheckbox = document.getElementById('selectAllCheckbox');
            const isChecked = selectAllCheckbox.checked;
            
            checkboxes.forEach(checkbox => {
                checkbox.checked = isChecked;
            });
            updateSelectedCount();
        }
        
        function toggleAllPending() {
            const checkboxes = document.querySelectorAll('.pending-checkbox');
            const selectAllCheckbox = document.getElementById('selectAllCheckbox');
            
            checkboxes.forEach(checkbox => {
                checkbox.checked = selectAllCheckbox.checked;
            });
            updateSelectedCount();
        }
        
        function updateSelectedCount() {
            const checkboxes = document.querySelectorAll('.pending-checkbox:checked');
            const count = checkboxes.length;
            document.getElementById('selectedCount').textContent = count + ' selected';
            
            // Update select all checkbox state
            const allCheckboxes = document.querySelectorAll('.pending-checkbox');
            const selectAllCheckbox = document.getElementById('selectAllCheckbox');
            selectAllCheckbox.checked = count === allCheckboxes.length && count > 0;
            selectAllCheckbox.indeterminate = count > 0 && count < allCheckboxes.length;
        }
        
        async function bulkApprove() {
            const checkboxes = document.querySelectorAll('.pending-checkbox:checked');
            if (checkboxes.length === 0) {
                alert('Please select at least one membership to approve.');
                return;
            }
            
            if (!confirm(`Are you sure you want to approve ${checkboxes.length} membership(s)?`)) {
                return;
            }
            
            const membershipIds = Array.from(checkboxes).map(cb => cb.value);
            
            try {
                const response = await fetch('http://localhost:8000/api/admin/bulk_approve', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({ membership_ids: membershipIds })
                });
                
                const data = await response.json();
                
                if (data.success) {
                    alert(data.message);
                    location.reload();
                } else {
                    alert('Error: ' + data.message);
                }
            } catch (error) {
                alert('Error connecting to server. Please try again.');
            }
        }
        
        async function bulkReject() {
            const checkboxes = document.querySelectorAll('.pending-checkbox:checked');
            if (checkboxes.length === 0) {
                alert('Please select at least one membership to reject.');
                return;
            }
            
            if (!confirm(`Are you sure you want to reject ${checkboxes.length} membership(s)?`)) {
                return;
            }
            
            const membershipIds = Array.from(checkboxes).map(cb => cb.value);
            
            try {
                const response = await fetch('http://localhost:8000/api/admin/bulk_reject', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({ membership_ids: membershipIds })
                });
                
                const data = await response.json();
                
                if (data.success) {
                    alert(data.message);
                    location.reload();
                } else {
                    alert('Error: ' + data.message);
                }
            } catch (error) {
                alert('Error connecting to server. Please try again.');
            }
        }
        </script>
    </body>
    </html>
    ''', memberships_html=memberships_html, pending_requests_html=pending_requests_html, users_options=users_options, total_pending=total_pending, total_active=total_active, total_rejected=total_rejected, total_revenue=total_revenue)

@app.route('/add_membership', methods=['POST'])
def add_membership():
    if not request.cookies.get('logged_in'):
        return redirect('/')
    
    user_id = request.form.get('user_id')
    plan_type = request.form.get('plan_type')
    duration = request.form.get('duration')
    
    if user_id and plan_type:
        end_date = get_end_date(duration)
        db_execute('''
            INSERT INTO memberships (user_id, plan_type, duration, start_date, end_date, status, price, payment_status)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (user_id, plan_type, duration, datetime.datetime.now(), end_date, 'active', 0.0, 'paid'))
    
    return redirect('/dashboard')

@app.route('/edit_membership')
def edit_membership():
    if not request.cookies.get('logged_in'):
        return redirect('/')
    
    membership_id = request.args.get('id')
    if not membership_id:
        return redirect('/dashboard')
    
    membership = db_execute('''
        SELECT m.id, u.username, u.email, m.plan_type, m.duration, m.start_date, m.end_date, m.status, m.user_id
        FROM memberships m JOIN users u ON m.user_id = u.id WHERE m.id=?
    ''', (membership_id,), fetch=True)
    
    if not membership:
        return redirect('/dashboard')
    
    membership = membership[0]
    users = db_execute('SELECT id, username, email FROM users ORDER BY username', fetch=True)
    
    users_options = ''
    for user in users:
        selected = 'selected' if user[0] == membership[8] else ''
        users_options += f'<option value="{user[0]}" {selected}>{user[1]} ({user[2]})</option>'

    return render_template_string('''
    <html>
    <head>
        <title>Edit Membership</title>
        <style>
          body { font-family: Arial, sans-serif; background: #f4f7f8; padding: 50px; }
          .form-container {
              max-width: 400px; background: white; padding: 20px;
              margin: auto; border-radius: 8px; box-shadow: 0 0 10px #ccc;
          }
          input[type=text], input[type=number], select {
              width: 100%;
              padding: 8px;
              margin: 8px 0;
              box-sizing: border-box;
              border: 1px solid #ccc;
              border-radius: 4px;
          }
          input[type=submit], .cancel-btn {
              background-color: #007bff;
              color: white;
              padding: 10px;
              border: none;
              border-radius: 4px;
              cursor: pointer;
              width: 100%;
              margin-top: 10px;
              text-align: center;
              display: inline-block;
              text-decoration: none;
          }
          input[type=submit]:hover, .cancel-btn:hover {
              background-color: #0056b3;
          }
        </style>
    </head>
    <body>
        <div class="form-container">
        <h2>Edit Membership ID {{ membership[0] }}</h2>
        <form method="post" action="/edit_membership">
            <input type="hidden" name="id" value="{{ membership[0] }}">
            <select name="user_id" required>
                {{ users_options | safe }}
            </select>
            <input type="text" name="plan_type" placeholder="Plan Type" value="{{ membership[3] }}" required>
            <input type="text" name="duration" placeholder="Duration" value="{{ membership[4] or '' }}">
            <input type="submit" value="Update Membership">
        </form>
        <a href="/dashboard" class="cancel-btn">Cancel</a>
        </div>
    </body>
    </html>
    ''', membership=membership, users_options=users_options)

@app.route('/edit_membership', methods=['POST'])
def handle_edit_membership():
    if not request.cookies.get('logged_in'):
        return redirect('/')
    
    membership_id = request.form.get('id')
    user_id = request.form.get('user_id')
    plan_type = request.form.get('plan_type')
    duration = request.form.get('duration')
    
    if membership_id and user_id and plan_type:
        end_date = get_end_date(duration)
        db_execute('''
            UPDATE memberships SET user_id=?, plan_type=?, duration=?, start_date=?, end_date=?, status=?, price=?, payment_status=? WHERE id=?
        ''', (user_id, plan_type, duration, datetime.datetime.now(), end_date, 'active', 0.0, 'paid', membership_id))
    
    return redirect('/dashboard')

@app.route('/delete_membership')
def delete_membership():
    if not request.cookies.get('logged_in'):
        return redirect('/')
    
    membership_id = request.args.get('id')
    if membership_id:
        db_execute('DELETE FROM memberships WHERE id=?', (membership_id,))
    
    return redirect('/dashboard')

@app.route('/approve_membership')
def approve_membership():
    if not request.cookies.get('logged_in'):
        return redirect('/')
    
    membership_id = request.args.get('id')
    if membership_id:
        # Get membership record
        membership = db_execute('''
            SELECT user_id, plan_type, duration, price, customer_name, customer_email, transaction_id
            FROM memberships WHERE id = ?
        ''', (membership_id,), fetch=True)
        
        if membership:
            membership = membership[0]
            # Update membership status to active and payment status to paid
            end_date = get_end_date(membership[2])
            db_execute('''
                UPDATE memberships SET status = ?, payment_status = ?, end_date = ? WHERE id = ?
            ''', ('active', 'paid', end_date, membership_id))
    
    return redirect('/dashboard')

@app.route('/reject_membership')
def reject_membership():
    if not request.cookies.get('logged_in'):
        return redirect('/')
    
    membership_id = request.args.get('id')
    if membership_id:
        db_execute('UPDATE memberships SET status = ?, payment_status = ? WHERE id = ?', ('rejected', 'rejected', membership_id))
    
    return redirect('/dashboard')

@app.route('/view_payment_details')
def view_payment_details():
    if not request.cookies.get('logged_in'):
        return redirect('/')
    
    membership_id = request.args.get('id')
    if not membership_id:
        return redirect('/dashboard')
    
    membership = db_execute('''
        SELECT m.id, u.username, u.email, u.full_name, u.phone, m.plan_type, m.duration, m.start_date, m.end_date, m.status, m.user_id, m.price, m.payment_status, m.customer_name, m.customer_email, m.transaction_id
        FROM memberships m JOIN users u ON m.user_id = u.id WHERE m.id = ?
    ''', (membership_id,), fetch=True)
    
    if not membership:
        return redirect('/dashboard')
    
    membership = membership[0]
    time_since_request = calculate_time_since(membership[7])
    
    return render_template_string('''
    <html>
    <head>
        <title>Payment Details - Membership #{{ membership[0] }}</title>
        <style>
          body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 20px; margin: 0; }
          .container { max-width: 800px; margin: 0 auto; }
          .card { background: white; border-radius: 15px; padding: 30px; box-shadow: 0 8px 25px rgba(0,0,0,0.1); margin-bottom: 20px; }
          h1 { color: white; text-align: center; margin-bottom: 30px; }
          h2 { color: #333; border-bottom: 2px solid #007bff; padding-bottom: 10px; }
          .detail-row { display: flex; justify-content: space-between; padding: 10px 0; border-bottom: 1px solid #eee; }
          .detail-label { font-weight: bold; color: #555; }
          .detail-value { color: #333; }
          .status-pending { color: #ff6b35; font-weight: bold; }
          .status-active { color: #28a745; font-weight: bold; }
          .status-rejected { color: #dc3545; font-weight: bold; }
          .action-buttons { text-align: center; margin-top: 30px; }
          .btn { display: inline-block; padding: 12px 24px; margin: 0 10px; text-decoration: none; border-radius: 8px; font-weight: bold; }
          .btn-approve { background: #28a745; color: white; }
          .btn-reject { background: #dc3545; color: white; }
          .btn-back { background: #6c757d; color: white; }
          .btn:hover { }
          .priority-indicator { padding: 5px 10px; border-radius: 20px; color: white; font-weight: bold; }
          .priority-high { background: #dc3545; }
          .priority-medium { background: #ffc107; color: #000; }
          .priority-low { background: #28a745; }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>Payment Details - Membership #{{ membership[0] }}</h1>
            
            <div class="card">
                <h2>Membership Information</h2>
                <div class="detail-row">
                    <span class="detail-label">Membership ID:</span>
                    <span class="detail-value">#{{ membership[0] }}</span>
                </div>
                <div class="detail-row">
                    <span class="detail-label">Plan Type:</span>
                    <span class="detail-value">{{ membership[5] }}</span>
                </div>
                <div class="detail-row">
                    <span class="detail-label">Duration:</span>
                    <span class="detail-value">{{ membership[6] }}</span>
                </div>
                <div class="detail-row">
                    <span class="detail-label">Price:</span>
                    <span class="detail-value">${{ membership[11] }}</span>
                </div>
                <div class="detail-row">
                    <span class="detail-label">Status:</span>
                    <span class="detail-value status-{{ membership[9] }}">{{ membership[9].upper() }}</span>
                </div>
                <div class="detail-row">
                    <span class="detail-label">Payment Status:</span>
                    <span class="detail-value status-{{ membership[12] }}">{{ membership[12].upper() }}</span>
                </div>
                <div class="detail-row">
                    <span class="detail-label">Request Date:</span>
                    <span class="detail-value">{{ membership[7] }}</span>
                </div>
                <div class="detail-row">
                    <span class="detail-label">Time Since Request:</span>
                    <span class="detail-value priority-indicator priority-{{ 'high' if time_since_request > 24 else 'medium' if time_since_request > 12 else 'low' }}">
                        {{ time_since_request }} hours ago
                    </span>
                </div>
            </div>
            
            <div class="card">
                <h2>Customer Information</h2>
                <div class="detail-row">
                    <span class="detail-label">Username:</span>
                    <span class="detail-value">{{ membership[1] }}</span>
                </div>
                <div class="detail-row">
                    <span class="detail-label">Full Name:</span>
                    <span class="detail-value">{{ membership[3] }}</span>
                </div>
                <div class="detail-row">
                    <span class="detail-label">Email:</span>
                    <span class="detail-value">{{ membership[2] }}</span>
                </div>
                <div class="detail-row">
                    <span class="detail-label">Phone:</span>
                    <span class="detail-value">{{ membership[4] or 'N/A' }}</span>
                </div>
                <div class="detail-row">
                    <span class="detail-label">Payment Name:</span>
                    <span class="detail-value">{{ membership[13] or 'N/A' }}</span>
                </div>
                <div class="detail-row">
                    <span class="detail-label">Payment Email:</span>
                    <span class="detail-value">{{ membership[14] or 'N/A' }}</span>
                </div>
            </div>
            
            <div class="card">
                <h2>Payment Information</h2>
                <div class="detail-row">
                    <span class="detail-label">Transaction ID:</span>
                    <span class="detail-value">{{ membership[15] or 'N/A' }}</span>
                </div>
                <div class="detail-row">
                    <span class="detail-label">Amount:</span>
                    <span class="detail-value">${{ membership[11] }}</span>
                </div>
                <div class="detail-row">
                    <span class="detail-label">Payment Method:</span>
                    <span class="detail-value">UPI Transfer</span>
                </div>
            </div>
            
            <div class="action-buttons">
                <a href="/approve_membership?id={{ membership[0] }}" class="btn btn-approve" onclick="return confirm('Are you sure you want to approve this payment?')">Approve Payment</a>
                <a href="/reject_membership?id={{ membership[0] }}" class="btn btn-reject" onclick="return confirm('Are you sure you want to reject this payment?')">Reject Payment</a>
                <a href="/dashboard" class="btn btn-back">Back to Dashboard</a>
            </div>
        </div>
        
        <script>
        // Bulk action functions
        function selectAllPending() {
            const checkboxes = document.querySelectorAll('.pending-checkbox');
            const selectAllCheckbox = document.getElementById('selectAllCheckbox');
            const isChecked = selectAllCheckbox.checked;
            
            checkboxes.forEach(checkbox => {
                checkbox.checked = isChecked;
            });
            updateSelectedCount();
        }
        
        function toggleAllPending() {
            const checkboxes = document.querySelectorAll('.pending-checkbox');
            const selectAllCheckbox = document.getElementById('selectAllCheckbox');
            
            checkboxes.forEach(checkbox => {
                checkbox.checked = selectAllCheckbox.checked;
            });
            updateSelectedCount();
        }
        
        function updateSelectedCount() {
            const checkboxes = document.querySelectorAll('.pending-checkbox:checked');
            const count = checkboxes.length;
            document.getElementById('selectedCount').textContent = count + ' selected';
            
            // Update select all checkbox state
            const allCheckboxes = document.querySelectorAll('.pending-checkbox');
            const selectAllCheckbox = document.getElementById('selectAllCheckbox');
            selectAllCheckbox.checked = count === allCheckboxes.length && count > 0;
            selectAllCheckbox.indeterminate = count > 0 && count < allCheckboxes.length;
        }
        
        async function bulkApprove() {
            const checkboxes = document.querySelectorAll('.pending-checkbox:checked');
            if (checkboxes.length === 0) {
                alert('Please select at least one membership to approve.');
                return;
            }
            
            if (!confirm(`Are you sure you want to approve ${checkboxes.length} membership(s)?`)) {
                return;
            }
            
            const membershipIds = Array.from(checkboxes).map(cb => cb.value);
            
            try {
                const response = await fetch('http://localhost:8000/api/admin/bulk_approve', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({ membership_ids: membershipIds })
                });
                
                const data = await response.json();
                
                if (data.success) {
                    alert(data.message);
                    location.reload();
                } else {
                    alert('Error: ' + data.message);
                }
            } catch (error) {
                alert('Error connecting to server. Please try again.');
            }
        }
        
        async function bulkReject() {
            const checkboxes = document.querySelectorAll('.pending-checkbox:checked');
            if (checkboxes.length === 0) {
                alert('Please select at least one membership to reject.');
                return;
            }
            
            if (!confirm(`Are you sure you want to reject ${checkboxes.length} membership(s)?`)) {
                return;
            }
            
            const membershipIds = Array.from(checkboxes).map(cb => cb.value);
            
            try {
                const response = await fetch('http://localhost:8000/api/admin/bulk_reject', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({ membership_ids: membershipIds })
                });
                
                const data = await response.json();
                
                if (data.success) {
                    alert(data.message);
                    location.reload();
                } else {
                    alert('Error: ' + data.message);
                }
            } catch (error) {
                alert('Error connecting to server. Please try again.');
            }
        }
        </script>
    </body>
    </html>
    ''', membership=membership, time_since_request=time_since_request)

if __name__ == '__main__':
    print("Admin Panel running on http://localhost:8081")
    print("Press Ctrl+C to stop")
    app.run(host='0.0.0.0', port=8081, debug=True)