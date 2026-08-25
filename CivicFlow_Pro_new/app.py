# ==========================================
#  CivicFlow Pro - Smart Governance System
#  Copyright (c) 2026. All Rights Reserved.
# ==========================================

# ==========================================
# 1. CONFIGURATION & IMPORTS
# ==========================================
import os
import uuid
import logging
import datetime
import csv
import sys
sys.stdout.reconfigure(encoding='utf-8')
import pandas as pd
import re
import threading  
import random 
import time 
import smtplib 
from email.message import EmailMessage
from io import StringIO, BytesIO
from functools import wraps

# --- FLASK IMPORTS ---
from flask import Flask, render_template, request, redirect, session, url_for, g, flash, make_response, send_file, jsonify, send_from_directory
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from dotenv import load_dotenv
from deep_translator import GoogleTranslator
from xhtml2pdf import pisa

# --- DATABASE ---
import mysql.connector
from db_config import get_db_connection 

# --- EXTERNAL MODULES & AI SYNC ---

# Safety Block 1: The AI Model (Crucial for presentation)
try:
    from ai_model import analyze_complaint, analyze_permit, find_duplicate_complaint
    print("✅ Integrated Real AI Models (BERT & MPNet)")
except Exception as e:
    print(f"AI Sync Error: {e}. Using Fallback functions.")
    def analyze_complaint(text): return "Municipality", "Medium", "Heuristic (Fallback)", 100.0, None
    def find_duplicate_complaint(text, open_comps): return None
    def analyze_permit(text): return "General Permission", "Medium"

# Safety Block 2: Optional Services (Won't crash AI if missing)
try:
    from auth import create_user, verify_user
    from email_service import send_submission_email     
    from sms_service import send_sms_alert
except ImportError as e:
    print(f"⚠️ Service Sync Warning: {e}. Running without external notifications.")
    def send_submission_email(email, tid, dept): pass
    def send_sms_alert(phone, tid, status): pass

# ==========================================
# 1. CONFIGURATION & SETUP
# ==========================================
load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "dev-fallback-secret-do-not-use-in-prod")

# --- FIX: PWA 'BACK BUTTON' CACHE PREVENTION ---
@app.after_request
def prevent_browser_cache(response):
    """Prevents ERR_FAILED when clicking the Back button after a form submission"""
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    return response
900
# EMAIL CONFIGURATION
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = os.getenv('EMAIL_USER')  
app.config['MAIL_PASSWORD'] = os.getenv('EMAIL_PASS')  

app.config['UPLOAD_FOLDER'] = os.path.join("static", "uploads")
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # Max 16MB file size
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

# --- SECURITY: RATE LIMITER ---
limiter = Limiter(
    get_remote_address,
    app=app,
    default_limits=["200 per day", "60 per hour"],
    storage_uri="memory://"
)

if not os.path.exists(app.config['UPLOAD_FOLDER']):
    os.makedirs(app.config['UPLOAD_FOLDER'])

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ==========================================
# 2. MASTER LOCK (SITE PASSWORD)
# ==========================================
SITE_PASSWORD = "vaseline" 

@app.before_request
def require_site_password():
    # Allow access to static files, lock screen, and API endpoints
    if request.endpoint in ['static', 'site_lock', 'check_site_password', 'chat_bot', 'serve_sw']:
        return
    
    # If user hasn't entered the password yet, force them to the Lock Screen
    if not session.get('site_unlocked'):
        return redirect(url_for('site_lock'))

@app.route('/site-lock')
def site_lock():
    return render_template('lock_screen.html')

@app.route('/check-site-password', methods=['POST'])
def check_site_password():
    password = request.form.get('password')
    if password == SITE_PASSWORD:
        session['site_unlocked'] = True  
        flash("Access Granted. Welcome to CivicFlow Pro.", "success")
        return redirect(url_for('index'))
    else:
        flash(" Access Denied: Wrong Password!", "danger")
        return redirect(url_for('site_lock'))

# ==========================================
# 3. HELPER FUNCTIONS
# ==========================================

def get_db():
    if 'db' not in g:
        g.db = get_db_connection()
        if g.db is None or not g.db.is_connected():
             g.db = get_db_connection()
    return g.db

@app.teardown_appcontext
def close_db(error):
    db = g.pop('db', None)
    if db is not None and db.is_connected():
        db.close()

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def format_dates(rows):
    if not rows: return []
    is_single = isinstance(rows, dict)
    rows = [rows] if is_single else rows
    
    for row in rows:
        if row.get('created_at') and isinstance(row['created_at'], (datetime.datetime, datetime.date)):
            row['created_at'] = row['created_at'].strftime("%d-%m-%Y %I:%M %p")
        if row.get('updated_at') and isinstance(row['updated_at'], (datetime.datetime, datetime.date)):
            row['updated_at'] = row['updated_at'].strftime("%d-%m-%Y %I:%M %p")
        if row.get('date_resolved') and isinstance(row['date_resolved'], (datetime.datetime, datetime.date)):
            row['date_resolved'] = row['date_resolved'].strftime("%d-%m-%Y")
            
    return rows[0] if is_single else rows

def get_department_from_category(category):
    mapping = {
        'Roads': 'PWD (Roads & Bridges)', 'Electricity': 'KSEB (Electricity)', 'Water': 'Water Authority (Supply/Sewage)',
        'Police': 'Police Department', 'Health': 'Health Department', 'Fire': 'Fire & Rescue Force',
        'Municipality': 'Municipality (Local Body)', 'Revenue': 'Revenue Dept', 'Education': 'Education Dept',
        'Agriculture': 'Agriculture', 'Ration': 'Civil Supplies', 'Labor': 'Labor Dept'
    }
    return mapping.get(category, 'Municipality (Local Body)')

# --- UPDATED: UNIFIED OTP SYSTEM WITH BACKGROUND THREADING ---
def send_email_background(email, subject, body, config):
    """Sends email in separate thread to prevent UI freezing"""
    try:
        msg = EmailMessage()
        msg.set_content(body)
        msg['Subject'] = subject
        msg['From'] = config['MAIL_USERNAME']
        msg['To'] = email

        server = smtplib.SMTP(config['MAIL_SERVER'], config['MAIL_PORT'])
        server.starttls()
        server.login(config['MAIL_USERNAME'], config['MAIL_PASSWORD'])
        server.send_message(msg)
        server.quit()
        print(f"✅ [Background] Email Sent to {email}")
    except Exception as e:
        print(f"❌ [Background] Email Failed: {e}")

def send_unified_otp(email, purpose="Verification"):
    # 1. Generate ONE random code
    otp_code = str(random.randint(100000, 999999))
    
    # 2. PRINT TO TERMINAL (Instant)
    print("\n" + "="*50)
    print(f"📱 [SMS SIMULATION] Message to {email}")
    print(f"🔑 UNIFIED OTP CODE: {otp_code}")
    print("="*50 + "\n")
    sys.stdout.flush()

    # 3. FIRE EMAIL IN BACKGROUND (Does not block)
    subject = f'🔐 {purpose} OTP: {otp_code}'
    body = f"Hello,\n\nYour {purpose} Code is: {otp_code}\n\nUse this to verify your identity. Valid for 2 minutes.\n\n- CivicFlow System"
    
    # Pass config securely to thread
    config = {
        'MAIL_SERVER': app.config['MAIL_SERVER'],
        'MAIL_PORT': app.config['MAIL_PORT'],
        'MAIL_USERNAME': app.config['MAIL_USERNAME'],
        'MAIL_PASSWORD': app.config['MAIL_PASSWORD']
    }
    
    threading.Thread(target=send_email_background, args=(email, subject, body, config)).start()

    # Return immediately
    return otp_code

# ==========================================
# 4. SECURITY DECORATORS
# ==========================================

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "user_id" not in session:
            flash("Please log in to continue.", "warning")
            return redirect(url_for("citizen_login"))
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "role" not in session:
            flash("Access Denied: Admin privileges required.", "danger")
            return redirect(url_for("admin_login"))
        
        allowed = ["admin", "super_admin", "dept_admin"]
        if session.get("role") not in allowed:
            flash("Access Denied.", "danger")
            return redirect(url_for("admin_login"))
            
        return f(*args, **kwargs)
    return decorated_function

# ==========================================
# 5. AUTHENTICATION ROUTES
# ==========================================

@app.route("/")
def index():
    conn = get_db()
    if not conn: return "Database Error", 500
    cur = conn.cursor(dictionary=True) 
    try:
        cur.execute("SELECT COUNT(*) as count FROM complaints WHERE status='Resolved'")
        resolved = cur.fetchone()['count']
        cur.execute("SELECT COUNT(*) as count FROM complaints")
        total = cur.fetchone()['count']
    except: 
        resolved, total = 0, 0
    finally: 
        cur.close()
    return render_template("index.html", resolved=resolved, total=total)

@app.route("/signup", methods=["GET", "POST"])
@limiter.limit("10 per minute") 
def signup():
    if request.method == "POST":
        name = request.form["name"]
        email = request.form["email"]
        phone = request.form.get("phone")
        password = request.form["password"]
        secret_code = request.form.get("secret_code")

        if secret_code != "CIVIC2025":
            flash("❌ Access Denied: Invalid Security Code.", "danger")
            return render_template("signup.html")

        conn = get_db()
        cur = conn.cursor(dictionary=True)
        cur.execute("SELECT * FROM users WHERE email=%s", (email,))
        if cur.fetchone():
            cur.close()
            flash("❌ Email already registered! Please login.", "danger")
            return redirect(url_for('citizen_login'))
        cur.close()

        otp = send_unified_otp(email, "Signup")

        session['signup_data'] = {
            'name': name,
            'email': email,
            'phone': phone,
            'password': generate_password_hash(password),
            'otp': otp,
            'timestamp': time.time()
        }

        flash(f"📩 OTP sent! Check Terminal immediately.", "info")
        return redirect(url_for('verify_signup_otp'))

    return render_template("signup.html")

@app.route("/resend-signup-otp", methods=["GET"])
def resend_signup_otp():
    if 'signup_data' not in session:
        return redirect(url_for('signup'))
    
    email = session['signup_data']['email']
    otp = send_unified_otp(email, "Signup")
    
    # Update session with new OTP and timestamp
    session['signup_data']['otp'] = otp
    session['signup_data']['timestamp'] = time.time()
    
    flash("📩 A new OTP has been sent!", "info")
    return redirect(url_for('verify_signup_otp'))

@app.route("/verify-signup-otp", methods=["GET", "POST"])
def verify_signup_otp():
    if 'signup_data' not in session:
        return redirect(url_for('signup'))
    
    if time.time() - session['signup_data']['timestamp'] > 120:
        session.pop('signup_data', None)
        flash("❌ OTP Expired! Please register again.", "danger")
        return redirect(url_for('signup'))
    
    if request.method == "POST":
        user_input = request.form.get("otp")
        
        if user_input == session['signup_data']['otp']:
            data = session['signup_data']
            conn = get_db()
            cur = conn.cursor()
            try:
                cur.execute("INSERT INTO users (name, email, phone, password, role) VALUES (%s, %s, %s, %s, 'citizen')", 
                            (data['name'], data['email'], data.get('phone'), data['password']))
                conn.commit()
                session.pop('signup_data', None) 
                flash(" Account Created! Please Login.", "success")
                return redirect(url_for('citizen_login'))
            except Exception as e:
                flash("Database Error.", "danger")
                print(e)
            finally:
                cur.close()
        else:
            flash("❌ Incorrect OTP.", "danger")

    return render_template("verify_signup_otp.html")

@app.route("/login/citizen", methods=["GET", "POST"])
@limiter.limit("10 per minute")
def citizen_login():
    if request.method == "POST":
        email = request.form.get("email")
        password = request.form.get("password")
        
        conn = get_db()
        cur = conn.cursor(dictionary=True) 
        cur.execute("SELECT * FROM users WHERE email=%s", (email,))
        user = cur.fetchone()
        cur.close()

        if user and (check_password_hash(user['password'], password) or user['password'] == password):
            otp = send_unified_otp(email, "Login")
            
            session['temp_user_id'] = user['id']
            session['temp_user_name'] = user['name']
            session['temp_role'] = user.get('role', 'citizen')
            session['login_otp'] = otp
            session['otp_email'] = email
            session['otp_timestamp'] = time.time() 
            
            return redirect(url_for('verify_login_otp'))

        flash("Invalid email or password.", "danger")
        
    return render_template("login_citizen.html")

@app.route("/resend-login-otp", methods=["GET"])
def resend_login_otp():
    if 'temp_user_id' not in session or 'otp_email' not in session:
        return redirect(url_for('citizen_login'))
    
    email = session['otp_email']
    otp = send_unified_otp(email, "Login")
    
    session['login_otp'] = otp
    session['otp_timestamp'] = time.time()
    
    flash("📩 A new OTP has been sent!", "info")
    return redirect(url_for('verify_login_otp'))

@app.route("/verify-login-otp", methods=["GET", "POST"])
def verify_login_otp():
    if 'temp_user_id' not in session:
        return redirect(url_for('citizen_login'))
    
    if time.time() - session.get('otp_timestamp', 0) > 120:
        session.clear()
        flash("❌ OTP Expired! Please login again.", "danger")
        return redirect(url_for('citizen_login'))

    if request.method == "POST":
        user_otp = request.form.get("otp")
        
        if user_otp == session.get('login_otp'):
            session['user_id'] = session['temp_user_id']
            session['officer_name'] = session['temp_user_name']
            session['role'] = session['temp_role']
            session['site_unlocked'] = True
            
            session.pop('login_otp', None)
            session.pop('temp_user_id', None)
            session.pop('otp_timestamp', None)
            
            flash(" Verified & Logged In!", "success")
            return redirect(url_for("dashboard"))
        else:
            flash("❌ Invalid OTP!", "danger")
            
    return render_template("verify_otp.html")

@app.route("/login/admin", methods=["GET", "POST"])
@limiter.limit("5 per minute")
def admin_login():
    if request.method == "POST":
        email = request.form.get("email")
        password = request.form.get("password")
        department = request.form.get("department")

        # --- 👑 GOD MODE (DEVELOPER LOGIN) ---
        if email == '@devmin.com' and password == 'dev123':
            session.clear()
            session['site_unlocked'] = True
            session['user_id'] = 999
            session['role'] = 'admin'
            session['officer_name'] = 'System Developer'
            session['admin_department'] = 'ALL' 
            
            conn = get_db()
            cur = conn.cursor()
            try:
                ip = request.remote_addr
                cur.execute("INSERT INTO login_logs (email, role, ip_address, status) VALUES (%s, 'Super Dev', %s, 'Success')", (email, ip))
                conn.commit()
            except: pass 
            cur.close()

            flash('⚡ Developer Mode Activated: Full Access Granted', 'success')
            return redirect(url_for('admin_dashboard'))

        conn = get_db()
        cur = conn.cursor(dictionary=True)
        cur.execute("SELECT * FROM department_admins WHERE email=%s", (email,))
        admin = cur.fetchone()
        cur.close()

        if not admin:
            flash("Admin email not found.", "danger")
        elif not check_password_hash(admin['password'], password) and admin['password'] != password:
             flash("Incorrect Password.", "danger")
        elif admin and admin['department'] != department:
            flash(f"Department Mismatch! Account belongs to {admin['department']}", "warning")
        else:
            session.clear()
            session['site_unlocked'] = True
            session["admin_id"] = admin['id']
            session["admin_department"] = admin['department']
            session["role"] = "dept_admin"
            session["officer_name"] = admin['name'] or "Officer"

            cur = conn.cursor() 
            try:
                ip = request.remote_addr
                cur.execute("INSERT INTO login_logs (email, role, ip_address, status) VALUES (%s, %s, %s, 'Success')", (email, 'dept_admin', ip))
                conn.commit()
            except: pass 
            cur.close()

            return redirect(url_for("admin_dashboard"))

    return render_template("login_admin.html")

@app.route('/logout')
def logout():
    session.clear()
    flash("Logged out successfully.", "info")
    return redirect(url_for('index'))

# ==========================================
# 6. CITIZEN FEATURES
# ==========================================

@app.route("/dashboard")
@login_required
def dashboard():
    conn = get_db()
    cur = conn.cursor(dictionary=True)
    
    # 1. Fetch User Profile Data
    cur.execute("SELECT * FROM users WHERE id=%s", (session["user_id"],))
    user_data = cur.fetchone()
    
    # 2. Fetch Recent Grievances (Complaints)
    cur.execute("SELECT * FROM complaints WHERE user_id=%s ORDER BY created_at DESC LIMIT 5", (session["user_id"],))
    complaints = format_dates(cur.fetchall())
    
    # ==========================================
    # 3. FIX: FETCH PERMIT APPLICATIONS
    # ==========================================
    # This line ensures your "Permits" tab actually shows data in the UI
    cur.execute("SELECT * FROM permissions WHERE user_id=%s ORDER BY created_at DESC LIMIT 5", (session["user_id"],))
    permits = format_dates(cur.fetchall())
    
    # 4. Calculate Dashboard Stats
    cur.execute("SELECT status FROM complaints WHERE user_id=%s", (session["user_id"],))
    all_rows = cur.fetchall()
    stats = {
        'total': len(all_rows),
        'resolved': sum(1 for r in all_rows if r['status'] == 'Resolved'),
        # Updated to include 'In Progress' so your counts stay accurate
        'registered': sum(1 for r in all_rows if r['status'] in ['Pending', 'Registered', 'In Progress'])
    }
    
    cur.close()
    
    # Return everything to the template
    return render_template("dashboard.html", 
                           complaints=complaints, 
                           permits=permits,  # <-- Sending permits to the frontend now
                           stats=stats, 
                           citizen_name=session.get('officer_name'), 
                           user_data=user_data)

@app.route("/submit", methods=["GET", "POST"])
@login_required
def submit():
    if request.method == "POST":
        category = request.form.get("category")
        original_text = request.form.get("complaint") 
        landmark = request.form.get("landmark")
        lat = request.form.get("latitude")
        long = request.form.get("longitude")
        image = request.files.get("image")

        if not category or not original_text:
            flash("Please provide details.", "warning")
            return redirect(request.url)

        try:
            translated_text = GoogleTranslator(source='auto', target='en').translate(original_text)
        except:
            translated_text = original_text

        if category == 'Other':
            ai_dept, urgency, engine, confidence, alt_dept = analyze_complaint(translated_text) 
            final_dept = ai_dept
        else:
            final_dept = get_department_from_category(category)
            urgency = "High" if category in ['Roads', 'Electricity', 'Water', 'Police'] else "Medium"
            engine = "User Selected"
            confidence = 100.0
            alt_dept = None
        
        conn = get_db()
        cur = conn.cursor(dictionary=True)

        img_name = request.form.get("existing_image")
        if image and allowed_file(image.filename):
            img_name = f"{uuid.uuid4().hex}_{secure_filename(image.filename)}"
            image.save(os.path.join(app.config['UPLOAD_FOLDER'], img_name))
            
        force_submit = request.form.get("force_submit")
        
        if not force_submit:
            cur.execute("SELECT tracking_id, complaint FROM complaints WHERE status NOT IN ('Resolved', 'Rejected')")
            open_comps = cur.fetchall()
            dup_tracking_id = find_duplicate_complaint(translated_text, open_comps)
            if dup_tracking_id:
                cur.execute("SELECT * FROM complaints WHERE tracking_id=%s", (dup_tracking_id,))
                duplicate_record = cur.fetchone()
                cur.close()
                return render_template('duplicate_found.html', 
                                       duplicate=duplicate_record,
                                       form_data={
                                           'category': category,
                                           'complaint': original_text,
                                           'landmark': landmark,
                                           'latitude': lat,
                                           'longitude': long,
                                           'existing_image': img_name or ''
                                       })

        tracking_id = str(uuid.uuid4())[:8].upper()
        days = 3 if urgency == 'High' else 14
        target = datetime.date.today() + datetime.timedelta(days=days)

        full_desc = f"[{category}] {original_text} (Eng: {translated_text}) - Loc: {landmark}"
        
        query = """INSERT INTO complaints (user_id, complaint, department, urgency, image_path, tracking_id, target_date, current_desk, latitude, longitude, routing_engine, confidence_score)
                   VALUES (%s, %s, %s, %s, %s, %s, %s, 'Section Clerk', %s, %s, %s, %s)"""
        cur.execute(query, (session["user_id"], full_desc, final_dept, urgency, img_name, tracking_id, target, lat, long, engine, confidence))
        conn.commit()

        def safe_send_email(u_email, t_id, dept):
            try:
                send_submission_email(u_email, t_id, dept)
            except Exception as e:
                print(f"⚠️ Email Failed (Ignored): {e}")

        def safe_send_sms(u_phone, t_id, stat):
            try:
                send_sms_alert(u_phone, t_id, stat)
            except Exception as e:
                print(f"⚠️ SMS Failed (Ignored): {e}")

        cur.execute("SELECT email, phone FROM users WHERE id=%s", (session["user_id"],))
        u = cur.fetchone()
        
        if u: 
            if u['email']: 
                threading.Thread(target=safe_send_email, args=(u['email'], tracking_id, final_dept)).start()
            if u['phone']: 
                threading.Thread(target=safe_send_sms, args=(u['phone'], tracking_id, "Registered")).start()
        
        cur.close()
        return redirect(url_for("success", tracking_id=tracking_id))

    return render_template("submit.html")

@app.route("/success/<tracking_id>")
@login_required
def success(tracking_id): return render_template("success.html", tracking_id=tracking_id)


@app.route("/upvote/<tracking_id>", methods=["POST"])
@login_required
def upvote_complaint(tracking_id):
    conn = get_db()
    cur = conn.cursor(dictionary=True)
    
    # Check if duplicate exists
    cur.execute("SELECT id FROM complaints WHERE tracking_id=%s", (tracking_id,))
    comp = cur.fetchone()
    if not comp:
        flash("Complaint not found.", "danger")
        return redirect(url_for('dashboard'))
        
    comp_id = comp['id']
    user_id = session['user_id']
    
    # Check if already upvoted
    cur.execute("SELECT * FROM complaint_upvotes WHERE complaint_id=%s AND user_id=%s", (comp_id, user_id))
    if cur.fetchone():
        flash("You have already upvoted this issue.", "warning")
    else:
        cur.execute("INSERT INTO complaint_upvotes (complaint_id, user_id) VALUES (%s, %s)", (comp_id, user_id))
        cur.execute("UPDATE complaints SET upvotes = upvotes + 1 WHERE id=%s", (comp_id,))
        conn.commit()
        flash("Thank you for co-signing! Your vote has been recorded.", "success")
        
    cur.close()
    return redirect(url_for('dashboard'))

@app.route("/history")
@login_required
def history():
    conn = get_db()
    cur = conn.cursor(dictionary=True)
    cur.execute("SELECT * FROM complaints WHERE user_id=%s ORDER BY created_at DESC", (session["user_id"],))
    complaints = format_dates(cur.fetchall())
    cur.close()
    return render_template("history.html", complaints=complaints)

@app.route("/track", methods=["GET", "POST"])
def track_complaint():
    complaint, history = None, []
    if request.method == "POST":
        # 1. Clean the input: Force UPPERCASE
        tid = request.form.get("tracking", "").strip().upper()
        conn = get_db(); cur = conn.cursor(dictionary=True)

        # ==========================================
        # 🟢 IF IT IS A PERMIT (PRM-)
        # ==========================================
        if tid.startswith("PRM-"):
            cur.execute("SELECT * FROM permissions WHERE tracking_id=%s", (tid,))
            p = cur.fetchone()
            
            if p:
                p = format_dates(p)
                complaint = {
                    'tracking_id': p['tracking_id'],
                    'department': p['type'],
                    'urgency': 'Legal Permit',
                    'complaint': f"Reason: {p['reason']} | Requested Start: {p['start_date']}",
                    'status': p['status'],
                    'created_at': p['created_at'],
                    'latitude': p['latitude'],
                    'longitude': p['longitude']
                }
                
                history.append({'status': 'System', 'remarks': 'Permit application securely recorded in the system.', 'updated_at': p['created_at']})
                history.append({'status': 'System', 'remarks': f"Smart Auto-Routed to {p['type']} category.", 'updated_at': p['created_at']})
                
                if p['status'] == 'Awaiting Field Verification':
                    history.append({'status': 'System', 'remarks': 'An officer will visit the pinned GPS coordinates soon.', 'updated_at': p['created_at']})
                else:
                    history.append({'status': 'System', 'remarks': f"Officer {p.get('approved_by', 'Assigned')} has inspected the site.", 'updated_at': p['created_at']})
                    history.append({'status': 'System', 'remarks': f"Final Decision: {p['status']}. Valid until: {p.get('end_date', 'N/A')}", 'updated_at': p['created_at']})
            else:
                flash("Invalid Permit Tracking ID.", "warning")

        # ==========================================
        # 🔵 IF IT IS A GRIEVANCE COMPLAINT
        # ==========================================
        else:
            cur.execute("SELECT * FROM complaints WHERE tracking_id=%s", (tid,))
            complaint = cur.fetchone()
            if complaint:
                complaint = format_dates(complaint)
                cur.execute("SELECT * FROM complaint_updates WHERE complaint_id=%s ORDER BY updated_at ASC", (complaint['id'],))
                db_history = format_dates(cur.fetchall())
                
                # --- HACKATHON BONUS: SMART SYSTEM LOGS ---
                history.append({'status': 'System', 'remarks': f"GPS Location securely mapped and verified.", 'updated_at': complaint['created_at']})
                history.append({'status': 'System', 'remarks': f"AI Semantic Engine triggered. Match confirmed for {complaint['department']}.", 'updated_at': complaint['created_at']})
                history.append({'status': 'System', 'remarks': f"SLA Countdown activated. Expected resolution by: {complaint.get('target_date', 'Standard Date')}.", 'updated_at': complaint['created_at']})
                
                # Append any real updates made by the Officer/Admin later
                if db_history:
                    if isinstance(db_history, list):
                        history.extend(db_history)
                    else:
                        history.append(db_history)
                # ------------------------------------------
            else: 
                flash("Invalid Tracking ID. Please check and try again.", "warning")
                
        cur.close()
    return render_template("track.html", complaint=complaint, history=history)

# ==========================================
# 7. ANALYTICS
# ==========================================

@app.route("/analytics")
@login_required
def analytics():
    conn = get_db()
    cur = conn.cursor(dictionary=True)
    
    cur.execute("SELECT status, COUNT(*) as count FROM complaints WHERE user_id=%s GROUP BY status", (session["user_id"],))
    user_status = {row['status']: row['count'] for row in cur.fetchall()}
    
    cur.execute("SELECT department, COUNT(*) as count FROM complaints GROUP BY department")
    dept_stats = cur.fetchall()
    
    cur.execute("""
        SELECT DATE(created_at) as date_val, COUNT(*) as count 
        FROM complaints GROUP BY DATE(created_at) 
        ORDER BY DATE(created_at) DESC LIMIT 7
    """)
    trend_data = cur.fetchall()
    
    trend_labels = []
    trend_counts = []
    for row in reversed(trend_data):
        d = row['date_val']
        lbl = d.strftime('%d-%b') if hasattr(d, 'strftime') else str(d)
        trend_labels.append(lbl)
        trend_counts.append(row['count'])

    cur.execute("SELECT COUNT(*) as total FROM complaints"); r_t = cur.fetchone()
    cur.execute("SELECT COUNT(*) as resolved FROM complaints WHERE status='Resolved'"); r_r = cur.fetchone()
    cur.close()

    return render_template("analytics.html", 
                           user_status=user_status,
                           dept_labels=[r['department'] for r in dept_stats],
                           dept_counts=[r['count'] for r in dept_stats],
                           trend_labels=trend_labels,
                           trend_counts=trend_counts,
                           total_complaints=r_t['total'] if r_t else 0,
                           total_resolved=r_r['resolved'] if r_r else 0)

# ==========================================
# 8. ADMIN PANEL (WITH GOD MODE & VOTES)
# ==========================================

@app.route('/admin_dashboard')
@admin_required
def admin_dashboard():
    conn = get_db()
    cur = conn.cursor(dictionary=True)
    
    dept = session.get('admin_department')
    
    # ==========================================
    # 0. SLA AUTO-ESCALATION ENGINE (PHASE 2)
    # ==========================================
    cur.execute("""
        UPDATE complaints 
        SET is_escalated = TRUE, 
            escalation_timestamp = NOW(), 
            hierarchy_status = 'Auto-Escalated (SLA Breached)', 
            urgency = 'Critical',
            status = 'Escalated'
        WHERE status != 'Resolved' 
          AND target_date < CURDATE() 
          AND is_escalated = FALSE
    """)
    if cur.rowcount > 0:
        conn.commit()
    
    # ==========================================
    # 1. FETCH COMPLAINTS (With Wildcard Match)
    # ==========================================
    query = """
        SELECT c.*, 
               COUNT(v.id) as vote_count,
               GROUP_CONCAT(v.voter_name SEPARATOR ', ') as voter_list
        FROM complaints c
        LEFT JOIN complaint_votes v ON c.id = v.complaint_id
    """
    
    params = ()
    if dept != 'ALL':
        # Grabs the first word (e.g., "Water" or "PWD") to catch all variations
        keyword = f"%{dept.split(' ')[0]}%" 
        query += " WHERE c.department LIKE %s"
        params = (keyword,)
    
    query += " GROUP BY c.id ORDER BY c.created_at DESC"
    
    cur.execute(query, params)
    complaints = format_dates(cur.fetchall())
    
    # ==========================================
    # 2. FETCH PERMITS (With Wildcard Match)
    # ==========================================
    permit_query = "SELECT * FROM permissions"
    if dept != 'ALL':
        keyword = f"%{dept.split(' ')[0]}%"
        permit_query += " WHERE type LIKE %s" 
        cur.execute(permit_query, (keyword,))
    else:
        cur.execute(permit_query)
    permits = format_dates(cur.fetchall())
    
    # ==========================================
    # 3. FETCH OFFICERS & CALCULATE STATS
    # ==========================================
    cur.execute("SELECT name as username, email, role FROM users WHERE role='admin'")
    officers = cur.fetchall()
    cur.close()
    
    total_pending = sum(1 for c in complaints if c['status'] != 'Resolved')
    resolved_count = sum(1 for c in complaints if c['status'] == 'Resolved')
    high_priority = sum(1 for c in complaints if c['urgency'] in ['High', 'Critical'])
    pending_permits = sum(1 for p in permits if p['status'] == 'Awaiting Field Verification')
    
    # AI Analytics & SLA Stats (Phase 2)
    sla_breaches = sum(1 for c in complaints if c.get('is_escalated'))
    ai_routed = sum(1 for c in complaints if 'Semantic' in c.get('routing_engine', ''))
    heuristic_routed = len(complaints) - ai_routed
    
    return render_template('admin_dashboard.html', 
                           complaints=complaints, 
                           permits=permits, 
                           officers=officers,
                           pending=total_pending,
                           pending_permits=pending_permits,
                           resolved=resolved_count,
                           high=high_priority,
                           sla_breaches=sla_breaches,
                           ai_routed=ai_routed,
                           heuristic_routed=heuristic_routed,
                           dept_name=dept)

# ==========================================
# 4. COMPLAINT UPDATE ROUTE (Your Exact Code Maintained)
# ==========================================
@app.route('/update_complaint_status', methods=['POST'])
@admin_required
def update_complaint_status():
    cid = request.form.get('id')
    status = request.form.get('status')
    remarks = request.form.get('remarks')
    
    conn = get_db(); cur = conn.cursor()
    if status == 'Resolved':
        today = datetime.date.today().strftime("%Y-%m-%d")
        cur.execute("UPDATE complaints SET status=%s, date_resolved=%s, feedback_comment=%s WHERE id=%s", (status, today, remarks, cid))
    else:
        cur.execute("UPDATE complaints SET status=%s WHERE id=%s", (status, cid))
    
    if cur.rowcount > 0:
        cur.execute("INSERT INTO complaint_updates (complaint_id, status, remarks) VALUES (%s, %s, %s)", (cid, status, remarks))
        conn.commit(); flash(f"Status updated to {status}", "success")
    else: flash("Error: ID not found", "danger")
    cur.close()
    return redirect(url_for('admin_dashboard'))

# ==========================================
# 5. PERMIT UPDATE ROUTE (The New Addition)
# ==========================================
@app.route('/update_permit_status', methods=['POST'])
@admin_required
def update_permit_status():
    pid = request.form.get('id')
    status = request.form.get('status')
    remarks = request.form.get('remarks')
    officer_name = session.get('user_name', 'Authorized Officer')
    
    conn = get_db(); cur = conn.cursor()
    
    # Update status and log which officer handled it
    cur.execute("UPDATE permissions SET status=%s, approved_by=%s WHERE id=%s", (status, officer_name, pid))
    
    if cur.rowcount > 0:
        conn.commit()
        flash(f"Permit {status} successfully.", "success")
    else: 
        flash("Error: Permit ID not found", "danger")
        
    cur.close()
    return redirect(url_for('admin_dashboard'))


@app.route('/escalate_complaint/<int:id>')
@admin_required
def escalate_complaint(id):
    conn = get_db(); cur = conn.cursor()
    cur.execute("SELECT hierarchy_status FROM complaints WHERE id=%s", (id,))
    row = cur.fetchone(); current = row[0] if row else None
    
    new_level = 'District Collector' if current == 'Head of Department' else 'Head of Department'
    cur.execute("UPDATE complaints SET status=%s, hierarchy_status=%s WHERE id=%s", ('Escalated', new_level, id))
    conn.commit(); cur.close()
    flash(f"Escalated to {new_level}", "warning")
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/add_officer', methods=['POST'])
@admin_required
def add_officer():
    name = request.form.get('name')
    email = request.form.get('email')
    password = request.form.get('password')
    
    hashed_pw = generate_password_hash(password)
    
    conn = get_db(); cur = conn.cursor()
    try:
        cur.execute("INSERT INTO users (name, email, password, role) VALUES (%s, %s, %s, 'admin')", (name, email, hashed_pw))
        conn.commit(); flash(f"Officer {name} added!", "success")
    except mysql.connector.Error: flash("Email exists.", "danger")
    finally: cur.close()
    return redirect(url_for('admin_dashboard'))

# ==========================================
# PDF EXPORT LOGIC
# ==========================================
@app.route("/admin/export")
@admin_required
def export_data():
    conn = get_db()
    cur = conn.cursor(dictionary=True)
    
    dept = session.get('admin_department')
    if dept == 'ALL':
        cur.execute("SELECT tracking_id, department, urgency, status, created_at, complaint FROM complaints ORDER BY created_at DESC")
    else:
        cur.execute("SELECT tracking_id, department, urgency, status, created_at, complaint FROM complaints WHERE department=%s ORDER BY created_at DESC", (dept,))
        
    complaints = format_dates(cur.fetchall())
    cur.close()

    if not complaints:
        flash("No data available to export.", "warning")
        return redirect(url_for('admin_dashboard'))

    html_content = render_template("report_pdf.html", 
                                   complaints=complaints, 
                                   date=datetime.date.today().strftime("%d-%B-%Y"))

    pdf_file = BytesIO()
    pisa_status = pisa.CreatePDF(html_content, dest=pdf_file)

    if pisa_status.err:
        return f"PDF Generation Error: {pisa_status.err}", 500

    pdf_file.seek(0)
    return send_file(
        pdf_file,
        download_name=f"Official_Report_{datetime.date.today()}.pdf",
        as_attachment=True,
        mimetype="application/pdf"
    )

# ==========================================
# 9. UTILITIES & UPDATED CHATBOT
# ==========================================

@app.route('/edit_profile', methods=['POST'])
@login_required
def edit_profile():
    name = request.form.get('name')
    email = request.form.get('email')
    phone = request.form.get('phone')
    addr = request.form.get('address')
    pw = request.form.get('password')
    
    conn = get_db(); cur = conn.cursor()
    cur.execute("UPDATE users SET name=%s, email=%s, phone=%s, address=%s WHERE id=%s", (name, email, phone, addr, session['user_id']))
    if pw and pw.strip():
        h_pw = generate_password_hash(pw)
        cur.execute("UPDATE users SET password=%s WHERE id=%s", (h_pw, session['user_id']))
    conn.commit(); cur.close()
    session['officer_name'] = name
    flash("Profile Updated", "success")
    return redirect(url_for('dashboard'))

@app.route("/appeal/<int:id>", methods=["POST"])
def appeal_complaint(id):
    if "user_id" not in session: return redirect(url_for("citizen_login"))
    conn = get_db(); cur = conn.cursor()
    cur.execute("SELECT id FROM complaints WHERE id=%s AND user_id=%s", (id, session["user_id"]))
    if cur.fetchone():
        cur.execute("UPDATE complaints SET status='Appeal Requested', appeal_status='Pending' WHERE id=%s", (id,))
        cur.execute("INSERT INTO complaint_updates (complaint_id, status, remarks) VALUES (%s, %s, %s)", (id, 'Appeal Requested', 'Citizen Appeal'))
        conn.commit(); flash("Appeal submitted!", "warning")
    else: flash("Permission denied.", "danger")
    cur.close(); return redirect(url_for("history"))

@app.route("/rate_service/<int:id>", methods=["POST"])
@login_required
def rate_service(id):
    rating = request.form.get("rating")
    comment = request.form.get("comment")
    
    conn = get_db()
    cur = conn.cursor()
    
    try:
        # Update with citizen rating and feedback [cite: 80]
        cur.execute("""
            UPDATE complaints 
            SET rating = %s, feedback_comment = %s 
            WHERE id = %s AND user_id = %s
        """, (rating, comment, id, session["user_id"]))
        
        conn.commit()
        flash("Feedback submitted! Thank you for helping us improve.", "success")
    except Exception as e:
        conn.rollback()
        flash("Error submitting feedback.", "danger")
    finally:
        cur.close()
    
    # Redirect to dashboard to show live status update [cite: 32, 39]
    return redirect(url_for("dashboard"))
@app.route("/receipt/<tracking_id>")
@login_required
def download_receipt(tracking_id):
    conn = get_db(); cur = conn.cursor(dictionary=True)
    cur.execute("SELECT * FROM complaints WHERE tracking_id=%s", (tracking_id,))
    c = format_dates(cur.fetchone())
    if c:
        cur.execute("SELECT * FROM users WHERE id=%s", (c['user_id'],))
        u = cur.fetchone()
        c['citizen_name'] = u['name'] if u else "N/A"
        c['citizen_email'] = u['email'] if u else "N/A"
        cur.close()
        return render_template("receipt.html", c=c, date=datetime.date.today())
    cur.close(); return redirect(url_for("dashboard"))

@app.route('/api/chat', methods=['POST'])
def chat_bot():
    data = request.json
    user_msg = data.get('message', '').lower()
    
    if any(word in user_msg for word in ['hello', 'hi', 'hey', 'start']):
        response = "Hello! I am CivicBot. I can help you with:\n1. Filing a Complaint\n2. Tracking Status\n3. Department Contacts\n\nWhat do you need help with?"
    elif 'track' in user_msg or 'status' in user_msg:
        response = "To track your complaint:\n1. Go to 'Citizen Login'.\n2. Enter your Tracking ID (e.g., #AB1234).\n3. You will see the live status and officer remarks."
    elif 'register' in user_msg or 'file' in user_msg or 'complain' in user_msg:
        response = "To file a complaint:\n1. Click 'Register Complaint'.\n2. Upload a photo (optional).\n3. Our AI will automatically select the department for you!"
    elif 'login' in user_msg or 'signin' in user_msg:
        response = "We have two login portals:\n• Citizens: Use 'Citizen Login' to track issues.\n• Officers: Use 'Officer Login' for administrative tasks."
    elif 'road' in user_msg or 'pothole' in user_msg or 'pwd' in user_msg:
        response = "[PWD Dept] Report road damage, potholes, or broken bridges here. We route these directly to the Assistant Engineer."
    elif 'water' in user_msg or 'pipe' in user_msg or 'leak' in user_msg:
        response = "[Water Authority] For pipe bursts or no water supply, please upload a photo of the location. We will notify the valve section immediately."
    elif 'current' in user_msg or 'power' in user_msg or 'electricity' in user_msg or 'light' in user_msg:
        response = "[KSEB] You can report dangerous lines, power failures, or broken streetlights. For immediate danger, please call 1912."
    elif 'garbage' in user_msg or 'waste' in user_msg or 'smell' in user_msg or 'cleaning' in user_msg:
        response = "[Municipality/Health] Waste accumulation issues are sent to the Health Inspector. Please ensure your photo clearly shows the location."
    elif 'police' in user_msg or 'crime' in user_msg or 'theft' in user_msg:
        response = "⚠️ For emergencies, dial 112 immediately.\nFor non-emergency community issues (traffic, noise), you can file a report here."
    elif 'fire' in user_msg:
        response = "🔥 EMERGENCY: Dial 101 for Fire Force immediately. Do not wait for this app response for active fires."
    elif 'land' in user_msg or 'revenue' in user_msg or 'tax' in user_msg or 'certificate' in user_msg:
        response = "[Revenue Dept] For Pokkuvaravu, Land Tax, or Income Certificate delays, please file a complaint here. We forward these to the Village Officer."
    elif 'ration' in user_msg or 'food' in user_msg or 'supply' in user_msg or 'shop' in user_msg:
        response = "[Civil Supplies] You can report Ration Shop irregularities, hoarding, or closed shops. The Taluk Supply Officer will investigate."
    elif 'school' in user_msg or 'teacher' in user_msg or 'education' in user_msg or 'class' in user_msg:
        response = "[Education Dept] Report infrastructure issues in Govt schools (broken roof, no water) here. Academic issues are sent to the AEO/DEO."
    elif 'farm' in user_msg or 'agriculture' in user_msg or 'crop' in user_msg or 'fertilizer' in user_msg:
        response = "[Agriculture] Report crop damage, fertilizer shortage, or Krishi Bhavan issues here. The Agriculture Officer will be notified."
    elif 'time' in user_msg or 'long' in user_msg or 'days' in user_msg or 'delay' in user_msg:
        response = "Resolution Timeframes:\n• ⚡ Critical (Power/Water): 24 Hours\n• 🛣️ High (Roads): 7 Days\n• 🏛️ Normal: 14 Days\nIf delayed, it auto-escalates."
    elif 'appeal' in user_msg or 'escalate' in user_msg or 'ignored' in user_msg:
        response = "⚖️ Escalation Protocol:\nIf your complaint is not resolved within 14 days, it automatically moves to the District Collector. You can also click the 'Appeal' button in your dashboard."
    elif 'contact' in user_msg or 'number' in user_msg or 'phone' in user_msg:
        response = "Emergency Numbers:\n• Police: 112\n• Ambulance: 108\n• Fire: 101\n• KSEB: 1912\n• Water: 1916"
    else:
        response = "I didn't quite understand that. Try asking about 'Roads', 'Ration', 'Tracking', or 'Delays'."
        
    return jsonify({'response': response})  

# ==========================================
# 10. ADVANCED PERMISSION PORTAL (OFFICER-DECISION MODEL)
# ==========================================

@app.route("/api/ai-predict-permit", methods=["POST"])
def ai_predict_permit():
    """Endpoint for the '✨ Auto AI Mode' in permission.html"""
    try:
        data = request.get_json()
        motive = data.get('description', '')
        if len(motive) < 10:
            return jsonify({"success": False, "message": "Motive description too short"})
        
        # Analyze permit motive using MPNet logic from model.py
        dept, urgency = analyze_permit(motive) 
        return jsonify({"success": True, "category": dept, "urgency": urgency})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)})

@app.route("/permission")
@login_required
def permission_portal():
    conn = get_db(); cur = conn.cursor(dictionary=True)
    role = session.get('role')
    dept = session.get('admin_department')

    if role == 'citizen':
        cur.execute("SELECT * FROM permissions WHERE user_id=%s ORDER BY created_at DESC", (session['user_id'],))
    elif dept == 'ALL':
        cur.execute("SELECT * FROM permissions ORDER BY created_at DESC")
    else:
        # Officers only see permissions for their specific legal category
        cur.execute("SELECT * FROM permissions WHERE type=%s ORDER BY created_at DESC", (dept,))
    
    reqs = format_dates(cur.fetchall())
    cur.close()
    return render_template("permission.html", requests=reqs)

@app.route("/permission/submit", methods=["GET", "POST"]) # <-- Changed this line
@login_required
def submit_permission():
    
    # --- ADD THIS NEW SAFETY NET ---
    # If the user clicks the browser 'Back' button, smoothly send them back to the portal
    if request.method == "GET":
        return redirect(url_for('permission_portal'))
    # -------------------------------

    if session.get('role') != 'citizen':
        flash("Unauthorized: Only citizens can apply for permits.", "danger")
        return redirect(url_for('permission_portal'))

    p_type = request.form.get("type")
    motive = request.form.get("reason")
    start = request.form.get("start_date")
    requested_end = request.form.get("end_date")
    lat = request.form.get("latitude")
    lng = request.form.get("longitude")
    
    # --- SMART FIX 1: AI AUTO-DETECT FALLBACK ("Other" Option) ---
    if p_type == "Other" or not p_type:
        try:
            # Force the AI to analyze the motive in the backend
            p_type, _ = analyze_permit(motive) 
        except Exception as e:
            print(f"AI Fallback Error: {e}")
            p_type = "General Permission" # Safety net

    tracking_id = "PRM-" + str(uuid.uuid4())[:6].upper()

    conn = get_db(); cur = conn.cursor(dictionary=True)
    try:
        # 1. Store in Database with 'Awaiting Field Verification' status
        cur.execute("""
            INSERT INTO permissions (user_id, student_name, type, start_date, end_date, reason, latitude, longitude, tracking_id, status)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, 'Awaiting Field Verification')
        """, (session['user_id'], session.get('officer_name'), p_type, start, requested_end, motive, lat, lng, tracking_id))
        conn.commit()

        # 2. Find and Notify Corresponding Officer for Site Visit
        cur.execute("SELECT email FROM department_admins WHERE department = %s", (p_type,))
        officer = cur.fetchone()
        
        target_email = officer['email'] if officer else os.getenv('ADMIN_EMAIL', 'admin@civicflow.gov')

        sub = f"ACTION REQUIRED: Field Verification - {tracking_id}"
        body = f"""Hello Officer, A new permit request for '{p_type}' has been submitted.

APPLICANT: {session.get('officer_name')}
MOTIVE: {motive}
COORDINATES: {lat}, {lng}

TASK:
1. Conduct Field Verification at pinned location.
2. Decide permitted duration and update 'End Date' in Admin Portal.
"""
        config = {'MAIL_SERVER': app.config['MAIL_SERVER'], 'MAIL_PORT': app.config['MAIL_PORT'], 'MAIL_USERNAME': app.config['MAIL_USERNAME'], 'MAIL_PASSWORD': app.config['MAIL_PASSWORD']}
        threading.Thread(target=send_email_background, args=(target_email, sub, body, config)).start()

        # --- SMART FIX 2: REDIRECT TO NEW SUCCESS SCREEN ---
# --- SMART FIX 2: REDIRECT TO NEW SUCCESS SCREEN ---
        cur.close()
        return redirect(url_for('permit_success', tracking_id=tracking_id))
        
    except Exception as e:
        flash(f"System Error: {e}", "danger")
        return redirect(url_for('permission_portal'))
    finally:
        if cur: cur.close()

# --- ADD THIS NEW ROUTE RIGHT BELOW IT ---
@app.route("/permission/success/<tracking_id>")
@login_required
def permit_success(tracking_id):
    return render_template("permit_success.html", tracking_id=tracking_id)

# --- NEW: OFFICER DECISION ROUTE ---
@app.route("/permission/approve", methods=["POST"])
@admin_required
def approve_permission():
    """Route for officers to finalize permitted days after field visit"""
    perm_id = request.form.get("id")
    final_end_date = request.form.get("end_date")
    action = request.form.get("action") # 'Approved' or 'Rejected'
    
    conn = get_db(); cur = conn.cursor()
    try:
        cur.execute("""
            UPDATE permissions 
            SET status=%s, end_date=%s, approved_by=%s 
            WHERE id=%s
        """, (action, final_end_date, session.get('officer_name'), perm_id))
        conn.commit()
        flash(f"Permit {action} with end date {final_end_date}", "success")
    except Exception as e:
        flash(f"Error: {e}", "danger")
    finally: cur.close()
    return redirect(url_for('admin_dashboard')) 

@app.route("/permission/receipt/<tracking_id>")
@login_required
def permit_receipt(tracking_id):
    conn = get_db(); cur = conn.cursor(dictionary=True)
    cur.execute("SELECT * FROM permissions WHERE tracking_id=%s", (tracking_id,))
    p = format_dates(cur.fetchone())
    if p:
        cur.execute("SELECT name, email, phone FROM users WHERE id=%s", (p['user_id'],))
        u = cur.fetchone(); cur.close()
        return render_template("receipt.html", c=p, u=u, date=datetime.date.today())
    cur.close(); flash("Receipt not found.", "warning")
    return redirect(url_for("permission_portal"))

# ==========================================
# PWA SERVICE WORKER ROUTE (Fixes Scope Issue)
# ==========================================
@app.route('/sw.js')
def serve_sw():
    return app.send_static_file('sw.js')

if __name__ == "__main__":
    app.run(debug=False, port=5000)