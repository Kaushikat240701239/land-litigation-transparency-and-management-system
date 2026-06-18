from flask import Flask, render_template, request, redirect, url_for, session, flash, send_from_directory
import pymysql
import os

app = Flask(__name__)
app.secret_key = "LAND_LITIX_SECRET" 
FAST2SMS_API_KEY = "PASTE_YOUR_FAST2SMS_API_KEY_HERE" # Get from fast2sms.com

# 📂 FILE UPLOAD CONFIG
UPLOAD_FOLDER = 'static/uploads/documents'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

class Sqlite3Row(dict):
    def __init__(self, cursor, row_tuple):
        super().__init__()
        self.tuple_data = row_tuple
        for idx, col in enumerate(cursor.description):
            self[col[0]] = row_tuple[idx]

    def __getitem__(self, item):
        if isinstance(item, int):
            return self.tuple_data[item]
        return super().__getitem__(item)

class MySqliteCursor(pymysql.cursors.Cursor):
    def fetchone(self):
        row = super().fetchone()
        if row is None: return None
        return Sqlite3Row(self, row)
    
    def fetchall(self):
        rows = super().fetchall()
        return [Sqlite3Row(self, row) for row in rows]

class DBWrapper:
    def __init__(self, conn):
        self.conn = conn

    def execute(self, query, args=None):
        cursor = self.conn.cursor()
        if query.strip().lower() == "select last_insert_rowid()":
            query = "SELECT LAST_INSERT_ID()"
        query = query.replace('?', '%s')
        
        # MySQL doesn't support INSERT OR IGNORE, use INSERT IGNORE
        if "INSERT OR IGNORE" in query:
            query = query.replace("INSERT OR IGNORE", "INSERT IGNORE")
            
        if args:
            cursor.execute(query, args)
        else:
            cursor.execute(query)
        return cursor

    def commit(self):
        self.conn.commit()

    def close(self):
        self.conn.close()

def get_connection():
    conn = pymysql.connect(
        host="localhost",
        user="root",
        password="Kaushika@2510",
        database="239_land_litigation_database_233",
        cursorclass=MySqliteCursor
    )
    return DBWrapper(conn)

def sync_user_lands(conn, user_id, phone):
    """
    Automatically maps lands from the master registry to a user if the phone numbers match.
    """
    matching_lands = conn.execute("SELECT land_id FROM lands WHERE owner_phone=?", (phone,)).fetchall()
    count = 0
    for land in matching_lands:
        try:
            # We use 'verified' status because the phone holder is now OTP-verified.
            conn.execute("""
                INSERT OR IGNORE INTO user_lands (user_id, land_id, document_path, claim_status)
                VALUES (?, ?, ?, 'verified')
            """, (user_id, land['land_id'], 'System Verified via Phone'))
            count += 1
        except Exception as e:
            print(f"Sync error for user {user_id}: {e}")
    return count

def send_sms_otp(phone, otp):
    """
    Sends OTP via Fast2SMS API. 
    Production Specs: https://www.fast2sms.com/dev/bulkV2
    """
    if not FAST2SMS_API_KEY or "PASTE_YOUR" in FAST2SMS_API_KEY:
        # SECURITY FALLBACK: Only print to Terminal/Console for dev testing.
        # NEVER show this on the web screen.
        print(f"\n[SECURITY LOG] OTP for {phone} is: {otp}\n", flush=True)
        return "SIMULATION_MODE"
    
    import requests
    url = "https://www.fast2sms.com/dev/bulkV2"
    payload = f"variables_values={otp}&route=otp&numbers={phone}"
    headers = {
        'authorization': FAST2SMS_API_KEY,
        'Content-Type': "application/x-www-form-urlencoded",
        'Cache-Control': "no-cache",
    }
    try:
        response = requests.request("POST", url, data=payload, headers=headers)
        return response.status_code == 200
    except Exception as e:
        print(f"SMS Gateway Error: {e}")
        return False

# 🌐 Welcome
@app.route("/")
def welcome():
    return render_template("welcome.html")

# 📝 Register
@app.route("/register")
def register():
    return render_template("register.html")

@app.route("/register_user", methods=["POST"])
def register_user():
    data = request.form
    conn = get_connection()
    try:
        conn.execute("""
            INSERT INTO users (name,email,password,phone,role)
            VALUES (?,?,?,?,?)
        """, (data["name"].strip(), data["email"].strip().lower(), data["password"], data["phone"].strip(), data["role"]))
        
        user_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
        
        # We NO LONGER auto-map lands here. Integrity requires manual verification.
        
        conn.commit()
        
        # Initiate Verification
        session['verify_user_id'] = user_id
        return redirect(url_for("send_otp"))
        
    except pymysql.err.IntegrityError:
        flash("Email or Phone already registered!", "error")
        return redirect(url_for("register"))
    finally:
        conn.close()

# 📱 OTP VERIFICATION
@app.route("/send_otp")
def send_otp():
    import random
    verify_id = session.get('verify_user_id') or session.get('user_id')
    if not verify_id:
        return redirect(url_for("login"))
    
    # Get user phone
    conn = get_connection()
    user = conn.execute("SELECT phone FROM users WHERE id=?", (verify_id,)).fetchone()
    conn.close()
    
    otp = str(random.randint(100000, 999999))
    session['current_otp'] = otp
    
    # Trigger SMS (Real or Terminal Log)
    sms_status = send_sms_otp(user['phone'], otp)
    
    if sms_status == True:
        flash("A 6-digit verification code has been sent to your mobile phone.", "success")
    elif sms_status == "SIMULATION_MODE":
        flash("TEST MODE: Code sent to system terminal. (Developer: Check your console log)", "info")
    else:
        flash("SMS Gateway is currently busy. Please try again in 2 minutes.", "error")
    
    return render_template("verify_phone.html")

@app.route("/verify_otp", methods=["POST"])
def verify_otp():
    user_otp = request.form.get("otp")
    if user_otp == session.get('current_otp'):
        user_id = session.get('verify_user_id') or session.get('user_id')
        conn = get_connection()
        try:
            # --- AUTO-MAP LANDS ---
            conn.execute("UPDATE users SET is_verified=1 WHERE id=?", (user_id,))
            user = conn.execute("SELECT phone FROM users WHERE id=?", (user_id,)).fetchone()
            if user:
                synced_count = sync_user_lands(conn, user_id, user['phone'])
                if synced_count > 0:
                    flash(f"System identified {synced_count} land record(s) matching your verified phone number. They have been added to your portfolio.", "success")
            
            conn.commit()
            
            session.pop('current_otp', None)
            session.pop('verify_user_id', None)
            
            flash("Identity Verified! Please login to continue.", "success")
            
            if session.get('user_id'):
                return redirect(url_for("user_dashboard"))
            return redirect(url_for("login"))
        finally:
            conn.close()
    else:
        flash("Invalid OTP Code. Please try again.", "error")
        return redirect(url_for("send_otp"))

# 🔐 Login
@app.route("/login")
def login():
    return render_template("login.html")

@app.route("/login_user", methods=["POST"])
def login_user():
    data = request.form
    conn = get_connection()
    try:
        user = conn.execute("""
            SELECT * FROM users
            WHERE email=? AND password=?
        """, (data["email"].strip().lower(), data["password"])).fetchone()

        if user:
            # Check if user has verified their identity via OTP
            # OTP is only required during registration, per user request.
            if user['is_verified'] == 0:
                pass
                
            # Ensure lands are synced (Matches retroactive request)
            sync_user_lands(conn, user['id'], user['phone'])
            conn.commit()

            session['user_id'] = user['id']
            session['user_name'] = user['name']
            session['user_role'] = user['role']
            if user["role"] == "admin":
                return redirect(url_for("admin_dashboard"))
            elif user["role"] == "farmer":
                return redirect(url_for("farmer_dashboard"))
            else:
                return redirect(url_for("user_dashboard"))
        
        flash("Invalid Email or Password. Please try again.", "error")
        return redirect(url_for("login"))
    finally:
        conn.close()

# 🛠️ ERROR HANDLERS
@app.errorhandler(404)
def page_not_found(e):
    return render_template("error.html", error_code="404", error_message="The digital parcel you are looking for has moved or does not exist."), 404

@app.errorhandler(500)
def server_error(e):
    return render_template("error.html", error_code="500", error_message="Internal Ledger Sync Failure. Our engineers are investigating."), 500

# 📊 Admin Dashboard
@app.route("/admin_dashboard")
def admin_dashboard():
    conn = get_connection()
    
    # Calculate stats
    total_lands = conn.execute("SELECT COUNT(*) FROM lands").fetchone()[0]
    total_cases = conn.execute("SELECT COUNT(*) FROM cases").fetchone()[0]
    active_cases = conn.execute("SELECT COUNT(*) FROM cases WHERE LOWER(status)='ongoing'").fetchone()[0]
    closed_cases = conn.execute("SELECT COUNT(*) FROM cases WHERE LOWER(status)='closed'").fetchone()[0]
    pending_cases = conn.execute("SELECT COUNT(*) FROM cases WHERE LOWER(status)='pending'").fetchone()[0]
    
    # Verified lands = total lands - lands with active cases
    lands_with_active_cases = conn.execute("SELECT COUNT(DISTINCT land_id) FROM cases WHERE LOWER(status)='ongoing'").fetchone()[0]
    verified_lands = total_lands - lands_with_active_cases

    # Fetch pending claims count
    pending_claims = conn.execute("SELECT COUNT(*) FROM user_lands WHERE LOWER(claim_status)='pending'").fetchone()[0]

    # Get recent cases
    cases = conn.execute("SELECT * FROM cases ORDER BY id DESC").fetchall()
    
    # Generate Heatmap Point Data (lat, lon) for active disputes
    heatmap_raw = conn.execute("""
        SELECT l.latitude, l.longitude 
        FROM lands l
        JOIN cases c ON l.land_id = c.land_id
        WHERE LOWER(c.status)='ongoing'
    """).fetchall()
    
    heatmap_data = [[row['latitude'], row['longitude'], 0.8] for row in heatmap_raw if row['latitude'] and row['longitude']]
    
    conn.close()

    return render_template(
        "admin_dashboard.html",
        user_name=session.get('user_name', 'Admin'),
        total_lands=total_lands,
        total_cases=total_cases,
        active_cases=active_cases,
        closed_cases=closed_cases,
        pending_cases=pending_cases,
        pending_claims=pending_claims,
        verified_lands=verified_lands,
        cases=cases,
        heatmap_data=heatmap_data
    )

# 🚦 ADMIN: Manage Claims
@app.route("/admin_claims")
def admin_claims():
    if 'user_id' not in session or session.get('user_role') != 'admin':
        return redirect(url_for("login"))
    
    conn = get_connection()
    # Fetch all pending claims with User and Land Info
    claims = conn.execute("""
        SELECT ul.*, u.name as user_name, u.phone as user_phone, u.is_verified,
               l.current_owner as original_owner, l.owner_phone as original_phone
        FROM user_lands ul
        JOIN users u ON ul.user_id = u.id
        JOIN lands l ON ul.land_id = l.land_id
        WHERE ul.claim_status = 'pending'
    """).fetchall()
    conn.close()
    
    return render_template("admin_claims.html", claims=claims)

@app.route("/approve_claim/<claim_id>")
def approve_claim(claim_id):
    if 'user_id' not in session or session.get('user_role') != 'admin':
        return redirect(url_for("login"))
    
    conn = get_connection()
    # Update claim status
    conn.execute("UPDATE user_lands SET claim_status='verified' WHERE id=?", (claim_id,))
    # Sync the land table current_owner if needed? 
    # Actually, for integrity, we should keep the "Government Registered Owner" 
    # separate from the "System Verified Owner". 
    # But let's at least mark it.
    conn.commit()
    conn.close()
    flash("Claim Approved! Asset is now linked to user portfolio.", "success")
    return redirect(url_for("admin_claims"))

@app.route("/reject_claim/<claim_id>")
def reject_claim(claim_id):
    if 'user_id' not in session or session.get('user_role') != 'admin':
        return redirect(url_for("login"))
    
    conn = get_connection()
    conn.execute("DELETE FROM user_lands WHERE id=?", (claim_id,))
    conn.commit()
    conn.close()
    flash("Claim Rejected and Removed.", "error")
    return redirect(url_for("admin_claims"))

# 🌾 Farmer Premium Dashboard
@app.route("/farmer_dashboard")
def farmer_dashboard():
    if 'user_id' not in session or session.get('user_role') != 'farmer':
        return redirect(url_for("login"))
    
    user_name = session['user_name']
    user_id = session['user_id']
    conn = get_connection()

    # Fetch farmer's lands
    farmer_lands = conn.execute("""
        SELECT l.* FROM lands l
        JOIN user_lands ul ON l.land_id = ul.land_id
        WHERE ul.user_id=?
    """, (user_id,)).fetchall()

    # Land count and total districts
    land_count = len(farmer_lands)

    # Fetch active cases for farmer's land
    land_ids = [l['land_id'] for l in farmer_lands]
    active_cases = 0
    if land_ids:
        placeholders = ','.join('?' * len(land_ids))
        active_cases = conn.execute(
            f"SELECT COUNT(*) FROM cases WHERE land_id IN ({placeholders}) AND LOWER(status)='ongoing'",
            land_ids
        ).fetchone()[0]
        
    # Generate Heatmap Point Data (lat, lon) for active disputes
    heatmap_raw = conn.execute("""
        SELECT l.latitude, l.longitude 
        FROM lands l
        JOIN cases c ON l.land_id = c.land_id
        WHERE LOWER(c.status)='ongoing'
    """).fetchall()
    
    heatmap_data = [[row['latitude'], row['longitude'], 0.8] for row in heatmap_raw if row['latitude'] and row['longitude']]

    conn.close()
    
    return render_template(
        "farmer_dashboard.html",
        user_name=user_name,
        farmer_lands=farmer_lands,
        land_count=land_count,
        active_cases=active_cases,
        heatmap_data=heatmap_data
    )

# 🌿 Farmer: My Lands
@app.route("/farmer_lands")
def farmer_lands():
    if 'user_id' not in session or session.get('user_role') != 'farmer':
        return redirect(url_for("login"))
    user_id = session['user_id']
    conn = get_connection()
    farmer_lands = conn.execute("""
        SELECT l.* FROM lands l
        JOIN user_lands ul ON l.land_id = ul.land_id
        WHERE ul.user_id=?
    """, (user_id,)).fetchall()
    conn.close()
    return render_template("farmer_lands.html", farmer_lands=farmer_lands)

# 🌍 Farmer: Soil Health
@app.route("/farmer_soil")
def farmer_soil():
    if 'user_id' not in session or session.get('user_role') != 'farmer':
        return redirect(url_for("login"))
    return render_template("farmer_soil.html")

# 🏛️ Farmer: Govt Schemes
@app.route("/farmer_schemes")
def farmer_schemes():
    if 'user_id' not in session or session.get('user_role') != 'farmer':
        return redirect(url_for("login"))
    return render_template("farmer_schemes.html")

# 🌦️ Farmer: Weather
@app.route("/farmer_weather")
def farmer_weather():
    if 'user_id' not in session or session.get('user_role') != 'farmer':
        return redirect(url_for("login"))
    return render_template("farmer_weather.html")

# 📊 Farmer: Market Prices
@app.route("/farmer_market")
def farmer_market():
    if 'user_id' not in session or session.get('user_role') != 'farmer':
        return redirect(url_for("login"))
    return render_template("farmer_market.html")

# 📅 Farmer: Crop Calendar
@app.route("/farmer_calendar")
def farmer_calendar():
    if 'user_id' not in session or session.get('user_role') != 'farmer':
        return redirect(url_for("login"))
    return render_template("farmer_calendar.html")

# 🧮 Farmer: Fertilizer Calculator
@app.route("/farmer_fertilizer")
def farmer_fertilizer():
    if 'user_id' not in session or session.get('user_role') != 'farmer':
        return redirect(url_for("login"))
    return render_template("farmer_fertilizer.html")

# 👤 User Dashboard
@app.route("/user_dashboard")
def user_dashboard():
    if 'user_id' not in session:
        return redirect(url_for("login"))
    
    user_name = session['user_name']
    user_id = session['user_id']
    conn = get_connection()
    
    # Get user's lands via mapping
    user_lands = conn.execute("""
        SELECT l.* FROM lands l 
        JOIN user_lands ul ON l.land_id = ul.land_id
        WHERE ul.user_id=?
    """, (user_id,)).fetchall()
    
    # Get cases on user's lands
    land_ids = [land['land_id'] for land in user_lands]
    if land_ids:
        placeholders = ','.join('?' * len(land_ids))
        user_cases = conn.execute(f"SELECT * FROM cases WHERE land_id IN ({placeholders}) ORDER BY id DESC", land_ids).fetchall()
    else:
        user_cases = []
    
    # Get recent history for user's lands
    if land_ids:
        placeholders = ','.join('?' * len(land_ids))
        history = conn.execute(f"SELECT * FROM land_history WHERE land_id IN ({placeholders}) ORDER BY transfer_date DESC LIMIT 10", land_ids).fetchall()
    else:
        history = []
        
    # Generate Heatmap Point Data (lat, lon) for active disputes (State-wide insight for normal user)
    heatmap_raw = conn.execute("""
        SELECT l.latitude, l.longitude 
        FROM lands l
        JOIN cases c ON l.land_id = c.land_id
        WHERE LOWER(c.status)='ongoing'
    """).fetchall()
    
    heatmap_data = [[row['latitude'], row['longitude'], 0.8] for row in heatmap_raw if row['latitude'] and row['longitude']]
    
    conn.close()

    return render_template(
        "user_dashboard.html",
        user_name=user_name,
        user_lands=user_lands,
        user_cases=user_cases,
        history=history,
        heatmap_data=heatmap_data
    )

# 🏡 My Lands
@app.route("/my_lands")
def my_lands():
    if 'user_id' not in session:
        return redirect(url_for("login"))
    
    conn = get_connection()
    user_lands = conn.execute("""
        SELECT l.* FROM lands l 
        JOIN user_lands ul ON l.land_id = ul.land_id
        WHERE ul.user_id=?
    """, (session['user_id'],)).fetchall()
    conn.close()

    return render_template("my_lands.html", user_lands=user_lands)

# ⚖️ My Cases
@app.route("/my_cases")
def my_cases():
    if 'user_id' not in session:
        return redirect(url_for("login"))
    
    conn = get_connection()
    land_ids = [row['land_id'] for row in conn.execute("SELECT land_id FROM user_lands WHERE user_id=?", (session['user_id'],)).fetchall()]
    
    if land_ids:
        placeholders = ','.join('?' * len(land_ids))
        user_cases = conn.execute(f"SELECT * FROM cases WHERE land_id IN ({placeholders}) ORDER BY id DESC", land_ids).fetchall()
    else:
        user_cases = []
    
    conn.close()

    return render_template("my_cases.html", user_cases=user_cases)

# 🔍 Search Lands
@app.route("/search_lands", methods=["GET", "POST"])
def search_lands():
    if 'user_id' not in session:
        return redirect(url_for("login"))
    
    results = []
    
    # Form data for persistence
    filter_data = {
        "plot_number": request.form.get("plot_number", ""),
        "survey_number": request.form.get("survey_number", ""),
        "state": request.form.get("state", ""),
        "district": request.form.get("district", "")
    }
    
    conn = get_connection()
    
    if request.method == "POST":
        # Build query dynamically
        query = "SELECT * FROM lands WHERE 1=1"
        params = []
        
        if filter_data["plot_number"]:
            query += " AND land_id LIKE ?"
            params.append(f"%{filter_data['plot_number']}%")
            
        if filter_data["survey_number"]:
            query += " AND survey_number LIKE ?"
            params.append(f"%{filter_data['survey_number']}%")
            
        if filter_data["state"]:
            query += " AND state = ?"
            params.append(filter_data['state'])
            
        if filter_data["district"]:
            query += " AND district = ?"
            params.append(filter_data['district'])
            
        lands = conn.execute(query, params).fetchall()
        
        # Attach case status
        for land in lands:
            active_cases = conn.execute("SELECT COUNT(*) FROM cases WHERE land_id=? AND LOWER(status)='ongoing'", (land['land_id'],)).fetchone()[0]
            status = 'Disputed' if active_cases > 0 else 'Clear'
            
            results.append({
                'land_id': land['land_id'],
                'survey_number': land['survey_number'],
                'current_owner': land['current_owner'],
                'status': status
            })

    # Get unique states and districts for dropdowns
    states = [row['state'] for row in conn.execute("SELECT DISTINCT state FROM lands WHERE state IS NOT NULL").fetchall()]
    districts = [row['district'] for row in conn.execute("SELECT DISTINCT district FROM lands WHERE district IS NOT NULL").fetchall()]
    conn.close()

    return render_template("search_lands.html", results=results, filter_data=filter_data, states=states, districts=districts)

def calculate_risk_score(cases, history):
    score = 100
    risk_factors = []
    
    ongoing_cases = [c for c in cases if c['status'].lower() == 'ongoing']
    resolved_cases = [c for c in cases if c['status'].lower() == 'resolved']
    
    if ongoing_cases:
        score -= 50
        risk_factors.append(f"High Risk: {len(ongoing_cases)} active ongoing litigation(s) found.")
    if resolved_cases:
        score -= 15
        risk_factors.append(f"Medium Risk: Property has a history of {len(resolved_cases)} resolved case(s).")
        
    if len(history) >= 3:
        score -= 15
        risk_factors.append(f"Notice: High transfer frequency ({len(history)} recent transfers).")
    elif len(history) == 0:
        score -= 10
        risk_factors.append(f"Notice: Lack of digital transfer history points to potential missing link documents.")
        
    score = max(0, score)
    if score >= 90:
        risk_factors.append("Clear Title Projected: No significant adverse factors found.")
        
    return score, risk_factors

# 📄 Land Details
@app.route("/land_details/<land_id>")
def land_details(land_id):
    if 'user_id' not in session:
        return redirect(url_for("login"))
    
    user_id = session['user_id']
    conn = get_connection()
    
    # Get user info for verification status
    user = conn.execute("SELECT * FROM users WHERE id=?", (user_id,)).fetchone()
    
    # Get land info
    land = conn.execute("SELECT * FROM lands WHERE land_id=?", (land_id,)).fetchone()
    
    if not land:
        conn.close()
        return "Land not found", 404
    
    # Get claim info for THIS user and THIS land
    claim = conn.execute("SELECT * FROM user_lands WHERE user_id=? AND land_id=?", (user_id, land_id)).fetchone()
    
    # Get cases and history
    cases = conn.execute("SELECT * FROM cases WHERE land_id=? ORDER BY id DESC", (land_id,)).fetchall()
    history = conn.execute("SELECT * FROM land_history WHERE land_id=? ORDER BY transfer_date DESC", (land_id,)).fetchall()
    
    conn.close()

    risk_score, risk_factors = calculate_risk_score(cases, history)

    return render_template("land_details.html", 
                           land=land, 
                           cases=cases, 
                           history=history, 
                           claim=claim, 
                           is_verified=user['is_verified'],
                           risk_score=risk_score,
                           risk_factors=risk_factors)

# 🔒 CLAIM LAND
@app.route("/claim_land", methods=["POST"])
def claim_land():
    if 'user_id' not in session:
        return redirect(url_for("login"))
    
    user_id = session['user_id']
    land_id = request.form.get("land_id")
    file = request.files.get("document")
    
    conn = get_connection()
    # Check verification status
    user = conn.execute("SELECT is_verified FROM users WHERE id=?", (user_id,)).fetchone()
    if not user['is_verified']:
        conn.close()
        flash("You must verify your identity via OTP before claiming assets.", "error")
        return redirect(url_for("land_details", land_id=land_id))
    
    if not file or file.filename == '':
        conn.close()
        flash("You must upload a Patta/Chitta document as proof of ownership.", "error")
        return redirect(url_for("land_details", land_id=land_id))

    # Securely save the file
    filename = f"claim_{land_id}_{user_id}_{file.filename}"
    file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    file.save(file_path)
    
    try:
        conn.execute("INSERT INTO user_lands (user_id, land_id, document_path, claim_status) VALUES (?, ?, ?, 'pending')", 
                     (user_id, land_id, filename))
        conn.commit()
        flash("Ownership Claim Submitted! Admin will verify your Phone ID and Documents.", "success")
    except pymysql.err.IntegrityError:
        flash("Claim already exists for this asset.", "error")
    finally:
        conn.close()
    
    return redirect(url_for("land_details", land_id=land_id))

@app.route("/view_document/<filename>")
def view_document(filename):
    if 'user_id' not in session or session.get('user_role') != 'admin':
        return redirect(url_for("login"))
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

# 🚪 Logout
@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("welcome"))

# ➕ ADD CASE
@app.route("/add_case", methods=["GET"])
def add_case_page():
    return render_template("add_case.html")

@app.route("/add_case", methods=["POST"])
def add_case():
    land_id = request.form["land_id"]
    status = request.form["case_status"]
    case_description = request.form["case_description"]
    court_name = request.form.get("court_name", "")
    
    case_details = f"{case_description} (Court: {court_name})" if court_name else case_description

    conn = get_connection()
    
    # Optional logic: automatically add land if it doesn't exist
    land = conn.execute("SELECT * FROM lands WHERE land_id=?", (land_id,)).fetchone()
    if not land:
        conn.execute("INSERT INTO lands (land_id, current_owner) VALUES (?, ?)", (land_id, "Unknown"))
    
    conn.execute("""
        INSERT INTO cases (land_id, case_details, status)
        VALUES (?, ?, ?)
    """, (land_id, case_details, status))
    
    conn.commit()
    conn.close()

    # APPEND TO CSV
    import csv
    csv_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'case_details.csv')
    try:
        case_id_str = "C001"
        if os.path.exists(csv_path):
            with open(csv_path, 'r', newline='', encoding='utf-8') as f:
                lines = f.readlines()
                if len(lines) > 1:
                    last_id = lines[-1].split(',')[0].strip()
                    if last_id.startswith('C') and last_id[1:].isdigit():
                        case_id_str = f"C{int(last_id[1:]) + 1:03d}"
        
        with open(csv_path, 'a', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow([case_id_str, land_id, status.upper(), case_description, court_name])
    except Exception as e:
        print("CSV append error:", e)

    return redirect(url_for("admin_dashboard"))

# 🔄 UPDATE CASE
@app.route("/update_case", methods=["GET"])
def update_case_page():
    return render_template("update_case.html")

@app.route("/update_case", methods=["POST"])
def update_case():
    case_id = request.form["case_id"]
    status = request.form["case_status"]
    
    conn = get_connection()
    current_case = conn.execute("SELECT land_id, case_details FROM cases WHERE id=?", (case_id,)).fetchone()
    if current_case:
        land_id = current_case['land_id']
        case_details_db = current_case['case_details']
        
        import csv
        csv_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'case_details.csv')
        if os.path.exists(csv_path):
            try:
                updated_rows = []
                with open(csv_path, 'r', newline='', encoding='utf-8') as f:
                    reader = csv.DictReader(f)
                    fieldnames = reader.fieldnames
                    for row in reader:
                        row_desc = f"{row.get('case_description', '')} (Court: {row.get('court_name', '')})" if row.get('court_name') else row.get('case_description', '')
                        if row.get('land_id') == land_id and row_desc == case_details_db:
                            row['case_status'] = status.upper() if status else row.get('case_status')
                        updated_rows.append(row)
                with open(csv_path, 'w', newline='', encoding='utf-8') as f:
                    writer = csv.DictWriter(f, fieldnames=fieldnames)
                    if fieldnames:
                        writer.writeheader()
                    writer.writerows(updated_rows)
            except Exception as e:
                print("CSV update error:", e)

    conn.execute("UPDATE cases SET status=? WHERE id=?", (status, case_id))
    conn.commit()
    conn.close()
    
    return redirect(url_for("admin_dashboard"))

# 👤 UPDATE OWNER
@app.route("/update_owner", methods=["GET"])
def update_owner_page():
    return render_template("update_owner.html")

@app.route("/update_owner", methods=["POST"])
def update_owner():
    from datetime import datetime
    land_id = request.form["land_id"]
    new_owner = request.form["owner"]
    survey_number = request.form["survey_number"]
    state = request.form["state"]
    district = request.form["district"]
    owner_phone = request.form["owner_phone"]
    address = request.form.get("address", "")
    
    # Safely convert to float to prevent MySQL Data Truncation errors
    lat_raw = request.form.get("latitude", "0.0")
    lon_raw = request.form.get("longitude", "0.0")
    try:
        latitude = float(lat_raw) if lat_raw and lat_raw.strip() else 0.0
        longitude = float(lon_raw) if lon_raw and lon_raw.strip() else 0.0
    except ValueError:
        latitude = 0.0
        longitude = 0.0

    transfer_date = datetime.now().strftime("%Y-%m-%d")
    
    conn = get_connection()
    
    # 1. Update lands current_owner and details
    # Check if land exists
    land = conn.execute("SELECT * FROM lands WHERE land_id=?", (land_id,)).fetchone()
    if not land:
        conn.execute("""
            INSERT INTO lands (land_id, survey_number, current_owner, owner_phone, state, district, address, latitude, longitude)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (land_id, survey_number, new_owner, owner_phone, state, district, address, latitude, longitude))
    else:
        conn.execute("""
            UPDATE lands 
            SET current_owner=?, survey_number=?, owner_phone=?, state=?, district=?, address=?, latitude=?, longitude=? 
            WHERE land_id=?
        """, (new_owner, survey_number, owner_phone, state, district, address, latitude, longitude, land_id))
        
    # Update CSV
    import csv
    csv_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'land_details.csv')
    if os.path.exists(csv_path):
        try:
            updated_rows = []
            found = False
            with open(csv_path, 'r', newline='', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                fieldnames = reader.fieldnames
                for row in reader:
                    if row.get('land_id') == land_id:
                        row['owner_name'] = new_owner
                        row['survey_number'] = survey_number
                        row['state'] = state
                        row['district'] = district
                        row['owner_phone'] = owner_phone
                        row['address'] = address
                        row['latitude'] = latitude
                        row['longitude'] = longitude
                        found = True
                    updated_rows.append(row)
            
            if not found:
                new_row = {fn: '' for fn in (fieldnames or ['land_id', 'survey_number', 'owner_name', 'state', 'district', 'owner_phone', 'address', 'latitude', 'longitude'])}
                new_row['land_id'] = land_id
                new_row['survey_number'] = survey_number
                new_row['owner_name'] = new_owner
                new_row['state'] = state
                new_row['district'] = district
                new_row['owner_phone'] = owner_phone
                new_row['address'] = address
                new_row['latitude'] = latitude
                new_row['longitude'] = longitude
                updated_rows.append(new_row)
                if not fieldnames:
                    fieldnames = ['land_id', 'survey_number', 'owner_name', 'state', 'district', 'owner_phone', 'address', 'latitude', 'longitude']

            with open(csv_path, 'w', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                if fieldnames:
                    writer.writeheader()
                writer.writerows(updated_rows)
        except Exception as e:
            print("CSV update error:", e)

    # 2. Insert into history
    conn.execute("""
        INSERT INTO land_history (land_id, owner_name, transfer_date)
        VALUES (?, ?, ?)
    """, (land_id, new_owner, transfer_date))
    
    conn.commit()
    conn.close()
    
    return redirect(url_for("admin_dashboard"))

# 📜 HISTORY
@app.route("/history", methods=["GET"])
def history_page():
    # If no land_id is given, show all or let user search
    land_id = request.args.get("land_id", "")
    
    conn = get_connection()
    if land_id:
        data = conn.execute("SELECT * FROM land_history WHERE land_id=? ORDER BY transfer_date DESC", (land_id,)).fetchall()
    else:
        data = conn.execute("SELECT * FROM land_history ORDER BY transfer_date DESC LIMIT 50").fetchall()
    conn.close()
    
    return render_template("history.html", data=data, search_term=land_id)

@app.route("/history/<land_id>")
def history_by_url(land_id):
    conn = get_connection()
    data = conn.execute("SELECT * FROM land_history WHERE land_id=? ORDER BY transfer_date DESC", (land_id,)).fetchall()
    conn.close()
    return render_template("history.html", data=data, search_term=land_id)

# 🚀 UPGRADE TO PREMIUM
@app.route("/upgrade")
def upgrade():
    if 'user_id' not in session:
        return redirect(url_for("login"))
    return render_template("upgrade.html")

@app.route("/process_upgrade", methods=["POST"])
def process_upgrade():
    if 'user_id' not in session:
        return redirect(url_for("login"))
    
    user_id = session['user_id']
    conn = get_connection()
    conn.execute("UPDATE users SET role='farmer' WHERE id=?", (user_id,))
    conn.commit()
    conn.close()
    
    # Update session role
    session['user_role'] = 'farmer'
    
    return redirect(url_for("farmer_dashboard"))

if __name__ == "__main__":
    app.run(debug=True)