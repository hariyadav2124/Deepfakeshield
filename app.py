import os
from flask import Flask, render_template, request, redirect, url_for, session, flash, send_file
import mysql.connector as c
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from config import Config
from api.deepfake_api import analyze_media
from fpdf import FPDF
import datetime

app = Flask(__name__)
app.config.from_object(Config)
 
# Ensure required directories exist
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(app.config['REPORTS_FOLDER'], exist_ok=True)

# Database connection helper
def get_db_connection():
    try:
        return c.connect(
            host=app.config['DB_HOST'],
            user=app.config['DB_USER'],
            password=app.config['DB_PASSWORD'],
            database=app.config['DB_NAME']
        )
    except c.Error as err:
        print(f"Error connecting to MySQL: {err}")
        return None

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

@app.route('/')
def index():
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        
        db = get_db_connection()
        if db is None:
            flash("Database connection error. Please try again later.", "danger")
            return redirect(url_for('register'))
            
        cursor = db.cursor()
        
        # Check if username or email exists
        cursor.execute("SELECT id FROM users WHERE username = %s OR email = %s", (username, email))
        if cursor.fetchone():
            flash("Username or Email already exists", "danger")
            cursor.close()
            db.close()
            return redirect(url_for('register'))
            
        # Hash password and insert
        hashed_pw = generate_password_hash(password)
        cursor.execute("INSERT INTO users (username, email, password_hash) VALUES (%s, %s, %s)", 
                       (username, email, hashed_pw))
        db.commit()
        cursor.close()
        db.close()
        
        flash("Registration successful. Please log in.", "success")
        return redirect(url_for('login'))
        
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        
        db = get_db_connection()
        if db is None:
            flash("Database connection error.", "danger")
            return redirect(url_for('login'))
            
        cursor = db.cursor(dictionary=True)
        cursor.execute("SELECT * FROM users WHERE email = %s", (email,))
        user = cursor.fetchone()
        cursor.close()
        db.close()
        
        if user and check_password_hash(user['password_hash'], password):
            session['user_id'] = user['id']
            session['username'] = user['username']
            session['role'] = user['role']
            return redirect(url_for('dashboard'))
        else:
            flash("Invalid email or password", "danger")
            
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect(url_for('login'))
        
    db = get_db_connection()
    scans = []
    if db:
        cursor = db.cursor(dictionary=True)
        cursor.execute("SELECT * FROM scans WHERE user_id = %s ORDER BY scan_date DESC", (session['user_id'],))
        scans = cursor.fetchall()
        cursor.close()
        db.close()
        
    return render_template('dashboard.html', scans=scans)

@app.route('/upload', methods=['GET', 'POST'])
def upload():
    if 'user_id' not in session:
        return redirect(url_for('login'))
        
    if request.method == 'POST':
        if 'file' not in request.files:
            flash('No file part', 'danger')
            return redirect(request.url)
            
        file = request.files['file']
        if file.filename == '':
            flash('No selected file', 'danger')
            return redirect(request.url)
            
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            # Create a unique filename to prevent overwrites
            unique_filename = f"{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}_{filename}"
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
            file.save(filepath)
            
            # Analyze media
            result = analyze_media(filepath)
            
            if result['status'] == 'success':
                # Save to DB
                db = get_db_connection()
                if db:
                    cursor = db.cursor()
                    file_type = unique_filename.rsplit('.', 1)[1].lower() if '.' in unique_filename else 'unknown'
                    query = """
                        INSERT INTO scans (user_id, filename, file_type, result_label, confidence_score, processing_time) 
                        VALUES (%s, %s, %s, %s, %s, %s)
                    """
                    values = (
                        session['user_id'], 
                        unique_filename, 
                        file_type, 
                        result['label'], 
                        result['confidence'], 
                        result['processing_time']
                    )
                    cursor.execute(query, values)
                    db.commit()
                    scan_id = cursor.lastrowid
                    cursor.close()
                    db.close()
                    
                    return redirect(url_for('result', scan_id=scan_id))
            else:
                flash(f"API Analysis failed: {result.get('message', 'Unknown error')}", 'danger')
                
    return render_template('upload.html')

@app.route('/result/<int:scan_id>')
def result(scan_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
        
    db = get_db_connection()
    if not db:
        return "Database error", 500
        
    cursor = db.cursor(dictionary=True)
    # Ensure current user owns the scan OR is admin
    if session.get('role') == 'admin':
        cursor.execute("SELECT * FROM scans WHERE id = %s", (scan_id,))
    else:
        cursor.execute("SELECT * FROM scans WHERE id = %s AND user_id = %s", (scan_id, session['user_id']))
        
    scan = cursor.fetchone()
    cursor.close()
    db.close()
    
    if not scan:
        flash("Result not found or unauthorized.", "danger")
        return redirect(url_for('dashboard'))
        
    return render_template('result.html', scan=scan)

@app.route('/admin')
def admin():
    if 'user_id' not in session or session.get('role') != 'admin':
        flash("Access Denied.", "danger")
        return redirect(url_for('dashboard'))
        
    db = get_db_connection()
    scans = []
    if db:
        cursor = db.cursor(dictionary=True)
        # Fetch all scans with usernames
        query = """
            SELECT s.*, u.username 
            FROM scans s
            JOIN users u ON s.user_id = u.id
            ORDER BY s.scan_date DESC
        """
        cursor.execute(query)
        scans = cursor.fetchall()
        cursor.close()
        db.close()
        
    return render_template('admin.html', scans=scans)

@app.route('/download_report/<int:scan_id>')
def download_report(scan_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
        
    db = get_db_connection()
    cursor = db.cursor(dictionary=True)
    cursor.execute("""
        SELECT s.*, u.username, u.email 
        FROM scans s 
        JOIN users u ON s.user_id = u.id 
        WHERE s.id = %s
    """, (scan_id,))
    scan = cursor.fetchone()
    cursor.close()
    db.close()
    
    if not scan:
        flash("Scan not found", "danger")
        return redirect(url_for('dashboard'))

    if scan['user_id'] != session['user_id'] and session.get('role') != 'admin':
        flash("Unauthorized", "danger")
        return redirect(url_for('dashboard'))

    try:
        pdf = FPDF()
        pdf.add_page()

        # ==================== PAGE 1 ====================
        # Header
        pdf.set_font("Arial", 'B', 18)
        pdf.cell(200, 15, txt="DEEPFAKESHIELD", ln=True, align='C')
        pdf.set_font("Arial", 'B', 14)
        pdf.cell(200, 10, txt="Deepfake & AI-Generated Detection Report", ln=True, align='C')
        pdf.ln(10)

        # Report Information
        pdf.set_font("Arial", size=11)
        pdf.cell(200, 8, txt=f"Report ID: #{scan['id']}", ln=True)
        pdf.cell(200, 8, txt=f"Date & Time: {scan['scan_date'].strftime('%d %B %Y, %H:%M')}", ln=True)
        pdf.cell(200, 8, txt=f"User: {scan['username']} ({scan['email']})", ln=True)
        pdf.ln(12)

        # Analysis Result Section
        pdf.set_font("Arial", 'B', 14)
        pdf.cell(200, 12, txt="Analysis Result", ln=True)
        
        # Big Verdict
        if scan['result_label'].lower() == 'fake':
            pdf.set_text_color(200, 0, 0)
            verdict_text = "FAKE / AI-GENERATED"
        else:
            pdf.set_text_color(0, 128, 0)
            verdict_text = "REAL"

        pdf.set_font("Arial", 'B', 22)
        pdf.cell(200, 18, txt=verdict_text, ln=True, align='C')
        
        pdf.set_text_color(0, 0, 0)
        pdf.set_font("Arial", size=13)
        pdf.cell(200, 10, txt=f"Confidence: {scan['confidence_score']}%", ln=True, align='C')
        pdf.ln(15)

        # Additional Info
        pdf.set_font("Arial", size=11)
        pdf.cell(200, 8, txt=f"File Name: {scan['filename']}", ln=True)
        pdf.cell(200, 8, txt=f"File Type: {scan['file_type'].upper()}", ln=True)
        
        pdf.ln(20)
        pdf.set_font("Arial", size=10)
        pdf.multi_cell(0, 6, txt="This report is generated automatically using AI-powered detection system. "
                                "Results should be used as a reference only.")

        # ==================== PAGE 2 (Image Page) ====================
        pdf.add_page()   # ← Image ko next page pe bheja

        pdf.set_font("Arial", 'B', 14)
        pdf.cell(200, 12, txt="Uploaded Media", ln=True, align='C')
        pdf.ln(10)

        upload_path = os.path.join(app.config['UPLOAD_FOLDER'], scan['filename'])
        
        if os.path.exists(upload_path):
            try:
                # Badi aur centered image on new page
                pdf.image(upload_path, x=20, y=pdf.get_y(), w=170)
            except Exception as e:
                pdf.cell(200, 10, txt="[Image could not be loaded]", ln=True)
                print(f"Image load error: {e}")
        else:
            pdf.cell(200, 10, txt="[Uploaded file not found]", ln=True)

        # Footer on every page
        pdf.set_y(-25)
        pdf.set_font("Arial", 'I', 9)
        pdf.cell(200, 10, txt=f"Generated on {datetime.datetime.now().strftime('%d %B %Y at %H:%M')}", align='C')

        # Save PDF
        report_filename = f"Deepfake_Report_{scan['id']}.pdf"
        report_path = os.path.join(app.config['REPORTS_FOLDER'], report_filename)
        
        pdf.output(report_path)

        return send_file(report_path, as_attachment=True, download_name=report_filename)

    except Exception as e:
        print(f"PDF Error: {e}")
        flash("Failed to generate PDF report. Please try again.", "danger")
        return redirect(url_for('result', scan_id=scan_id))

if __name__ == '__main__':
    app.run(debug=True, port=5000)

