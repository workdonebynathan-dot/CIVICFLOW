import re

with open('app.py', 'r', encoding='utf-8') as f:
    app_code = f.read()

# 1. Update imports
app_code = app_code.replace(
    'from ai_model import analyze_complaint, analyze_permit',
    'from ai_model import analyze_complaint, analyze_permit, find_duplicate_complaint'
)
app_code = app_code.replace(
    'def analyze_complaint(text): return "Municipality", "Medium"',
    'def analyze_complaint(text): return "Municipality", "Medium", "Heuristic (Fallback)", 100.0, None\n    def find_duplicate_complaint(text, open_comps): return None'
)

# 2. Patch /submit
old_submit = """        if category == 'Other':
            ai_dept, urgency = analyze_complaint(translated_text) 
            final_dept = ai_dept
        else:
            final_dept = get_department_from_category(category)
            urgency = "High" if category in ['Roads', 'Electricity', 'Water', 'Police'] else "Medium"
        
        conn = get_db()
        cur = conn.cursor(dictionary=True)

        img_name = None
        if image and allowed_file(image.filename):
            img_name = f"{uuid.uuid4().hex}_{secure_filename(image.filename)}"
            image.save(os.path.join(app.config['UPLOAD_FOLDER'], img_name))

        tracking_id = str(uuid.uuid4())[:8].upper()
        days = 3 if urgency == 'High' else 14
        target = datetime.date.today() + datetime.timedelta(days=days)

        full_desc = f"[{category}] {original_text} (Eng: {translated_text}) - Loc: {landmark}"
        
        query = \"\"\"INSERT INTO complaints (user_id, complaint, department, urgency, image_path, tracking_id, target_date, current_desk, latitude, longitude)
                   VALUES (%s, %s, %s, %s, %s, %s, %s, 'Section Clerk', %s, %s)\"\"\"
        cur.execute(query, (session["user_id"], full_desc, final_dept, urgency, img_name, tracking_id, target, lat, long))
        conn.commit()"""

new_submit = """        if category == 'Other':
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
        
        query = \"\"\"INSERT INTO complaints (user_id, complaint, department, urgency, image_path, tracking_id, target_date, current_desk, latitude, longitude, routing_engine, confidence_score)
                   VALUES (%s, %s, %s, %s, %s, %s, %s, 'Section Clerk', %s, %s, %s, %s)\"\"\"
        cur.execute(query, (session["user_id"], full_desc, final_dept, urgency, img_name, tracking_id, target, lat, long, engine, confidence))
        conn.commit()"""

app_code = app_code.replace(old_submit, new_submit)

# 3. Add /upvote route before the end of the file or somewhere safe.
# Let's add it right before `@app.route("/history")` which is around line 590.
upvote_route = """
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

"""

app_code = app_code.replace('@app.route("/history")', upvote_route + '@app.route("/history")')

with open('app.py', 'w', encoding='utf-8') as f:
    f.write(app_code)
    
print("app.py patched successfully!")
