from flask import Flask, render_template, request, jsonify, session, redirect, url_for, send_file,flash
from dotenv import load_dotenv
import pymysql
import os
from werkzeug.utils import secure_filename

load_dotenv()

from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    Image
)

from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.colors import darkblue, gold, black, white
from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.lib.pagesizes import A4, landscape 
from reportlab.pdfgen import canvas



from datetime import datetime
import random



BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

app = Flask(
    __name__,
    template_folder=os.path.join(BASE_DIR, "templates"),
    static_folder=os.path.join(BASE_DIR, "static")
)

app.secret_key = "smartquiz_secret_key_123"

db = pymysql.connect(
    host=os.getenv("MYSQLHOST"),
    user=os.getenv("MYSQLUSER"),
    password=os.getenv("MYSQLPASSWORD"),
    database=os.getenv("MYSQLDATABASE"),
    port=int(os.getenv("MYSQLPORT")),
    autocommit=True,
    cursorclass=pymysql.cursors.Cursor,
    connect_timeout=10
)

def get_db():
    global db
    try:
        db.ping(reconnect=True)
    except:
        db = pymysql.connect(
            host=os.getenv("MYSQLHOST"),
            user=os.getenv("MYSQLUSER"),
            password=os.getenv("MYSQLPASSWORD"),
            database=os.getenv("MYSQLDATABASE"),
            port=int(os.getenv("MYSQLPORT")),
            autocommit=True,
            cursorclass=pymysql.cursors.Cursor,
            connect_timeout=10
        )
    return db

# ---------------- HOME ----------------
@app.route("/")
def home():
    return render_template("index.html")


# ---------------- SIGNUP ----------------
@app.route("/signup")
def signup():
    return render_template("signup.html")


@app.route("/register", methods=["POST"])
def register():

    name = request.form["name"]
    email = request.form["email"]
    password = request.form["password"]
    phone = request.form["phone"]

    file = request.files.get("profile_pic")

    filename = "default.jpg"

    if file and file.filename != "":
        filename = secure_filename(file.filename)
        upload_folder = os.path.join(app.root_path, "..", "static", "uploads")
        upload_folder = os.path.abspath(upload_folder)

        os.makedirs(upload_folder, exist_ok=True)

        file.save(os.path.join(upload_folder, filename))
    cursor = get_db().cursor()

    cursor.execute("""
        INSERT INTO users
        (name,email,password,phone,profile_pic)
        VALUES(%s,%s,%s,%s,%s)
    """, (
        name,
        email,
        password,
        phone,
        filename
    ))

    get_db().commit()

    return jsonify({
        "message":"Registration Successful"
    })

# ---------------- LOGIN ----------------
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "GET":
        return render_template("login.html")

    try:
        data = request.get_json()

        email = data.get("email", "").strip()
        password = data.get("password", "").strip()

        cursor = get_db().cursor()
        cursor.execute(
            "SELECT * FROM users WHERE email=%s AND password=%s",
            (email, password)
        )

        user = cursor.fetchone()

        if user:
            session["user_id"] = user[0]
            session["user_name"] = user[1]
            session["role"] = user[4]

            # Profile photo session me save hogi
            session["profile_pic"] = user[7]

            flash(f"Welcome, {user[1]}!", "success")

            return jsonify({
                "message": "Login Successful",
                "redirect": "/dashboard"
            })

        return jsonify({"message": "Invalid Email or Password"})

    except Exception as e:
        print("LOGIN ERROR:", e)
        return jsonify({"message": "Server Error"}), 500
                
@app.route("/forgot_password", methods=["GET", "POST"])
def forgot_password():

    if request.method == "POST":

        email = request.form["email"]
        new_password = request.form["new_password"]

        cursor = get_db().cursor()

        cursor.execute(
            "SELECT id FROM users WHERE email=%s",
            (email,)
        )

        user = cursor.fetchone()

        if not user:
            return "Email not found"

        cursor.execute(
            "UPDATE users SET password=%s WHERE email=%s",
            (new_password, email)
        )

        db.commit()

        return redirect(url_for("login"))

    return render_template("forgot_password.html")

# ---------------- LOGOUT ----------------
@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("home"))


# ---------------- DASHBOARD ----------------
@app.route("/dashboard")
def dashboard():
    if "user_id" not in session:
        return redirect(url_for("login"))

    return render_template("exam_select.html")
# ---------------- TOPICS ----------------
@app.route("/topics/<int:subject_id>")
def topics(subject_id):
    if "user_id" not in session:
        return redirect(url_for("login"))

    cursor = get_db().cursor()
    cursor.execute(
        "SELECT * FROM topics WHERE subject_id=%s",
        (subject_id,)
    )

    topics = cursor.fetchall()

    return render_template(
    "topics.html",
    topics=topics,
    subject_id=subject_id
)

# ---------------- QUIZ ----------------
@app.route("/quiz/<int:subject_id>/<int:topic_id>")
def quiz(subject_id, topic_id):

    if "user_id" not in session:
        return redirect(url_for("login"))

    cursor = get_db().cursor()

    cursor.execute("""
        SELECT * FROM questions
        WHERE subject_id=%s AND topic_id=%s
    """, (subject_id, topic_id))

    questions = cursor.fetchall()

    print("Subject:", subject_id)
    print("Topic:", topic_id)

    cursor.execute(
        "SELECT topic_name FROM topics WHERE id=%s",
        (topic_id,)
    )

    topic = cursor.fetchone()

    return render_template(
        "quiz.html",
        questions=questions,
        topic_name=topic[0] if topic else "Quiz",
        subject_id=subject_id,
        topic_id=topic_id
    )

# ---------------- SUBMIT QUIZ ----------------

@app.route("/submit_quiz/<int:subject_id>/<int:topic_id>", methods=["POST"])
def submit_quiz(subject_id, topic_id):

    if "user_id" not in session:
        return redirect(url_for("login"))

    cursor = get_db().cursor()

    cursor.execute("""
        SELECT
            id,
            option1,
            option2,
            option3,
            option4,
            correct_option
        FROM questions
        WHERE subject_id=%s AND topic_id=%s
    """, (subject_id, topic_id))

    questions = cursor.fetchall()

    score = 0
    answer_summary = []
    attempt_answers = []

    for index, q in enumerate(questions, start=1):

        qid = str(q[0])

        option1 = q[1]
        option2 = q[2]
        option3 = q[3]
        option4 = q[4]

        correct = q[5]
        user_ans = request.form.get(f"q{qid}")

        if user_ans == correct:
            score += 1
            mark = "✔"
        else:
            mark = "✘"

        def get_option_letter(answer):
            if answer == option1:
                return "A"
            elif answer == option2:
                return "B"
            elif answer == option3:
                return "C"
            elif answer == option4:
                return "D"
            return "-"

        your_letter = get_option_letter(user_ans)
        correct_letter = get_option_letter(correct)

        answer_summary.append({
            "qno": index,
            "your_answer": f"{your_letter}. {user_ans}" if user_ans else "-",
            "correct_answer": f"{correct_letter}. {correct}",
            "result": mark
        })

        attempt_answers.append({
            "question_id": qid,
            "user_answer": user_ans,
            "correct_answer": correct,
            "is_correct": user_ans == correct
        })

    total = len(questions)
    percentage = (score / total * 100) if total > 0 else 0

    # Save values in session
    session["score"] = score
    session["percentage"] = round(percentage, 2)

    if percentage >= 90:
        session["grade"] = "A+"
    elif percentage >= 75:
        session["grade"] = "A"
    elif percentage >= 60:
        session["grade"] = "B"
    elif percentage >= 50:
        session["grade"] = "C"
    else:
        session["grade"] = "D"

    session["answer_summary"] = answer_summary

    cursor.execute("""
        INSERT INTO quiz_attempts
        (user_id, subject_id, topic_id, score, percentage)
        VALUES(%s,%s,%s,%s,%s)
    """, (
        session["user_id"],
        subject_id,
        topic_id,
        score,
        percentage
    ))

    attempt_id = cursor.lastrowid

    for ans in attempt_answers:

        cursor.execute("""
            INSERT INTO user_answers
            (attempt_id, question_id, user_answer, correct_answer, is_correct)
            VALUES(%s,%s,%s,%s,%s)
        """, (
            attempt_id,
            ans["question_id"],
            ans["user_answer"],
            ans["correct_answer"],
            ans["is_correct"]
        ))

    return render_template(
        "result.html",
        score=score,
        total=total,
        percentage=round(percentage, 2)
    )


# ---------------- LEADERBOARD ----------------
@app.route("/leaderboard")
def leaderboard():

    if "user_id" not in session:
        return redirect(url_for("login"))

    cursor = get_db().cursor()

    cursor.execute("""
        SELECT u.name, MAX(q.percentage) AS best_score
        FROM quiz_attempts q
        JOIN users u ON q.user_id = u.id
        GROUP BY q.user_id
        ORDER BY best_score DESC
        LIMIT 10
    """)

    leaders = cursor.fetchall()

    return render_template(
        "leaderboard.html",
        leaders=leaders
    )


# ---------------- ANALYTICS ----------------
@app.route("/analytics")
def analytics():

    if "user_id" not in session:
        return redirect(url_for("login"))

    cursor = get_db().cursor()

    # Logged-in user ka role check
    cursor.execute(
        "SELECT role FROM users WHERE id=%s",
        (session["user_id"],)
    )

    user = cursor.fetchone()

    if not user:
        return redirect(url_for("login"))

    role = user[0]

    # ================= ADMIN ANALYTICS =================

    if role == "admin":

        cursor.execute("SELECT COUNT(*) FROM users WHERE role='student'")
        total_students = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM quiz_attempts")
        total_attempts = cursor.fetchone()[0]

        cursor.execute("SELECT AVG(percentage) FROM quiz_attempts")
        avg_score = cursor.fetchone()[0] or 0

        cursor.execute("SELECT MAX(percentage) FROM quiz_attempts")
        best_score = cursor.fetchone()[0] or 0

        cursor.execute("""
            SELECT
                subjects.name,
                COUNT(*)
            FROM quiz_attempts
            JOIN subjects
                ON quiz_attempts.subject_id = subjects.id
            GROUP BY subjects.id
        """)

        subject_stats = cursor.fetchall()

        return render_template(
            "analytics.html",
            admin=True,
            total_students=total_students,
            total_attempts=total_attempts,
            avg_score=round(avg_score, 2),
            best_score=round(best_score, 2),
            subject_stats=subject_stats
        )

    # ================= STUDENT ANALYTICS =================

    cursor.execute(
        "SELECT COUNT(*) FROM quiz_attempts WHERE user_id=%s",
        (session["user_id"],)
    )
    total_quizzes = cursor.fetchone()[0]

    cursor.execute(
        "SELECT AVG(percentage) FROM quiz_attempts WHERE user_id=%s",
        (session["user_id"],)
    )
    avg_score = cursor.fetchone()[0] or 0

    cursor.execute(
        "SELECT MAX(percentage) FROM quiz_attempts WHERE user_id=%s",
        (session["user_id"],)
    )
    best_score = cursor.fetchone()[0] or 0

    cursor.execute(
        "SELECT COUNT(DISTINCT subject_id) FROM quiz_attempts WHERE user_id=%s",
        (session["user_id"],)
    )
    subjects = cursor.fetchone()[0]
    cursor.execute("""
        SELECT
            subjects.name,
            COUNT(*),
            ROUND(AVG(quiz_attempts.percentage),2),
            MAX(quiz_attempts.percentage)
        FROM quiz_attempts
        JOIN subjects
            ON quiz_attempts.subject_id = subjects.id
        WHERE quiz_attempts.user_id=%s
        GROUP BY subjects.id
    """, (session["user_id"],))

    subject_stats = cursor.fetchall()

    return render_template(
        "analytics.html",
        admin=False,
        total_quizzes=total_quizzes,
        avg_score=round(avg_score, 2),
        best_score=round(best_score, 2),
        subjects=subjects,
        subject_stats=subject_stats
    )


# ---------------- SCOREBOARD --------------- #

@app.route("/scoreboard")
def scoreboard():

    if "user_id" not in session:
        return redirect(url_for("login"))

    cursor = get_db().cursor()

    cursor.execute("""
        SELECT
            subjects.name,
            topics.topic_name,
            quiz_attempts.score,
            quiz_attempts.percentage,
            quiz_attempts.attempt_date
        FROM quiz_attempts
        JOIN subjects
            ON quiz_attempts.subject_id = subjects.id
        JOIN topics
            ON quiz_attempts.topic_id = topics.id
        WHERE quiz_attempts.user_id=%s
        ORDER BY quiz_attempts.attempt_date DESC
        LIMIT 1
    """, (session["user_id"],))

    data = cursor.fetchone()

    if not data:
        return "<h3>No quiz attempted yet.</h3>"

    return render_template(
        "scoreboard.html",
        data=data,
        answer_summary=session.get("answer_summary", [])
    )

@app.route("/history")
def history():

    if "user_id" not in session:
        return redirect(url_for("login"))

    cursor = get_db().cursor()

    cursor.execute("""
        SELECT
            subjects.name,
            topics.topic_name,
            quiz_attempts.score,
            quiz_attempts.percentage,
            quiz_attempts.attempt_date
        FROM quiz_attempts
        JOIN subjects
            ON quiz_attempts.subject_id = subjects.id
        JOIN topics
            ON quiz_attempts.topic_id = topics.id
        WHERE quiz_attempts.user_id = %s
        ORDER BY quiz_attempts.attempt_date DESC
    """, (session["user_id"],))

    attempts = cursor.fetchall()

    return render_template(
        "history.html",
        attempts=attempts
    )

@app.route("/profile")
def profile():

    if "user_id" not in session:
        return redirect(url_for("login"))

    cursor = get_db().cursor()

    cursor.execute("""
        SELECT
            name,
            email,
            phone,
            role,
            created_at,
            profile_pic
        FROM users
        WHERE id=%s
    """, (session["user_id"],))

    user = cursor.fetchone()

    cursor.execute("""
        SELECT
            COUNT(*),
            IFNULL(MAX(percentage),0),
            IFNULL(AVG(percentage),0),
            COUNT(DISTINCT subject_id)
        FROM quiz_attempts
        WHERE user_id=%s
    """, (session["user_id"],))

    stats = cursor.fetchone()

    return render_template(
        "profile.html",
        user=user,
        stats=stats
    )

@app.route("/edit_profile", methods=["GET", "POST"])
def edit_profile():

    if "user_id" not in session:
        return redirect(url_for("login"))

    cursor = get_db().cursor()

    if request.method == "POST":

        name = request.form["name"]
        phone = request.form["phone"]
        password = request.form["password"]

        file = request.files.get("profile_pic")

        if file and file.filename != "":

            filename = secure_filename(file.filename)

            upload_folder = os.path.join(app.root_path, "..", "static", "uploads")
            upload_folder = os.path.abspath(upload_folder)

            os.makedirs(upload_folder, exist_ok=True)

            file.save(os.path.join(upload_folder, filename))

            cursor.execute(
                "UPDATE users SET profile_pic=%s WHERE id=%s",
                (filename, session["user_id"])
            )

        if password.strip() == "":

            cursor.execute("""
                UPDATE users
                SET name=%s,
                    phone=%s
                WHERE id=%s
            """, (
                name,
                phone,
                session["user_id"]
            ))

        else:

            cursor.execute("""
                UPDATE users
                SET name=%s,
                    phone=%s,
                    password=%s
                WHERE id=%s
            """, (
                name,
                phone,
                password,
                session["user_id"]
            ))

        get_db().commit()

        session["user_name"] = name

        flash("Profile Updated Successfully!", "success")

        return redirect(url_for("profile"))

    cursor.execute("""
        SELECT
            name,
            email,
            phone,
            profile_pic
        FROM users
        WHERE id=%s
    """, (session["user_id"],))

    user = cursor.fetchone()

    return render_template(
        "edit_profile.html",
        user=user
    )

@app.route("/remove_profile_photo")
def remove_profile_photo():

    if "user_id" not in session:
        return redirect(url_for("login"))

    cursor = get_db().cursor()

    cursor.execute("""
        UPDATE users
        SET profile_pic=%s
        WHERE id=%s
    """, (
        "default.jpg",
        session["user_id"]
    ))

    get_db().commit()

    flash("Profile Photo Removed Successfully!", "success")

    return redirect(url_for("edit_profile"))

@app.route("/download_score_report")
def download_score_report():

    if "user_id" not in session:
        return redirect(url_for("login"))

    file_name = "score_report.pdf"

    doc = SimpleDocTemplate(
        file_name,
        pagesize=landscape(A4),
        leftMargin=40,
        rightMargin=40,
        topMargin=40,
        bottomMargin=40
    )

    title_style = ParagraphStyle(
        "Title",
        fontSize=28,
        alignment=TA_CENTER,
        textColor=darkblue,
        spaceAfter=6,
        leading=30
    )

    heading_style = ParagraphStyle(
        "Heading",
        fontSize=18,
        alignment=TA_CENTER,
        textColor=gold,
        spaceAfter=12,
        leading=22
    )

    normal_style = ParagraphStyle(
        "Normal",
        fontSize=13,
        alignment=TA_CENTER,
        textColor=black,
        leading=18,
        spaceAfter=4
    )

    name = session.get("user_name", "Student")

    cursor = get_db().cursor()

    score = session.get("score", 0)
    grade = session.get("grade", "N/A")
    report_id = f"RPT-{random.randint(100000,999999)}"
    report_date = datetime.now().strftime("%d %B %Y")

    cursor.execute("""
        SELECT percentage
        FROM quiz_attempts
        WHERE user_id=%s
        ORDER BY id DESC
        LIMIT 1
    """, (session["user_id"],))

    result = cursor.fetchone()

    if result:
        percentage = result[0]
    else:
        percentage = 0

    logo_path = os.path.join(
        os.path.dirname(app.root_path),
        "static",
        "images",
        "logo.png"
    )

    seal_path = os.path.join(
        os.path.dirname(app.root_path),
        "static",
        "images",
        "seal.png"
    )

    sign_path = os.path.join(
        os.path.dirname(app.root_path),
        "static",
        "images",
        "shikha_sign.png"
    )

    logo = Image(logo_path, width=100, height=100)
    logo.hAlign = "CENTER"

    seal = Image(seal_path, width=45, height=45)
    seal.hAlign = "CENTER"

    student_sign = Image(sign_path, width=110, height=35)
    student_sign.hAlign = "CENTER"

    content = []

    content.append(logo)
    content.append(Spacer(1, 0.08 * inch))

    content.append(Paragraph(
        "<b>SMART QUIZ PLATFORM</b>",
        title_style
    ))

    content.append(Paragraph(
        """
        <font size="22" color="gold">
        <b>QUIZ SCORE REPORT</b>
        </font>
        """,
        heading_style
    ))

    content.append(Spacer(1, 0.12 * inch))

    content.append(Paragraph(
        "This Score Report belongs to",
        normal_style
    ))

    content.append(Spacer(1, 0.08 * inch))

    content.append(Paragraph(
        f"""
        <para spaceAfter="18">
        <font size="34" color="darkblue">
        <b>{name}</b>
        </font>
        </para>
        """,
        normal_style
    ))

    content.append(Spacer(1, 0.12 * inch))

    content.append(Paragraph(
    """
    This report contains the student's latest quiz performance,
    including score, percentage and answer summary
    generated by the <b>Smart Quiz Platform</b>.
    """,
    normal_style
    ))

    content.append(Spacer(1, 0.18 * inch))

    result_table = Table(
    [
        ["Final Score", "Percentage", "Grade"],
        [str(score), f"{percentage}%", grade]
    ],
    colWidths=[170, 170, 170]
    )

    result_table.setStyle(TableStyle([
    ('GRID', (0, 0), (-1, -1), 1.5, gold),
    ('BACKGROUND', (0, 0), (-1, 0), darkblue),
    ('TEXTCOLOR', (0, 0), (-1, 0), white),
    ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
    ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
    ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
    ('FONTSIZE', (0, 0), (-1, -1), 14),
    ('BOTTOMPADDING', (0, 0), (-1, 0), 10),
    ('TOPPADDING', (1, 1), (-1, -1), 10),
    ]))

    content.append(result_table)

    content.append(Spacer(1, 0.18 * inch))

    content.append(Paragraph(
        f"<b>Report ID:</b> {report_id}",
        normal_style
    ))

    content.append(Paragraph(
        f"<b>Date:</b> {report_date}",
        normal_style
    ))


    doc.build(content)

    return send_file(file_name, as_attachment=True)   

@app.route("/subjects/<exam>")
def subjects(exam):

    if "user_id" not in session:
        return redirect(url_for("login"))

    global db

    try:
        db.ping(reconnect=True)
    except:
        db = pymysql.connect(
            host=os.getenv("MYSQLHOST"),
            user=os.getenv("MYSQLUSER"),
            password=os.getenv("MYSQLPASSWORD"),
            database=os.getenv("MYSQLDATABASE"),
            port=int(os.getenv("MYSQLPORT")),
            autocommit=True
        )

    cursor = get_db().cursor()

    if exam not in ["UPSC", "JEE", "SSC"]:
        return "Invalid Exam"

    cursor.execute(
        "SELECT * FROM subjects WHERE name=%s",
        (exam,)
    )

    subjects = cursor.fetchall()

    return render_template(
        "dashboard.html",
        subjects=subjects
    )

# ---------------- ADMIN DASHBOARD ----------------

@app.route("/admin")
def admin():

    if "user_id" not in session:
        return redirect(url_for("login"))

    cursor = get_db().cursor()

    cursor.execute(
        "SELECT role FROM users WHERE id=%s",
        (session["user_id"],)
    )

    user = cursor.fetchone()

    if not user or user[0] != "admin":
        return "Access Denied"

    search = request.args.get("search", "")
    subject = request.args.get("subject", "")

    # ---------------- Statistics ----------------

    cursor.execute("SELECT COUNT(*) FROM users WHERE role='student'")
    total_students = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM questions")
    total_questions = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM quiz_attempts")
    total_attempts = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM subjects")
    total_subjects = cursor.fetchone()[0]
    
    # ---------------- Recent Students ----------------

    cursor.execute("""
        SELECT
            name,
            email,
            created_at
        FROM users
        WHERE role='student'
        ORDER BY created_at DESC
        LIMIT 5
    """)

    recent_students = cursor.fetchall()


    # ---------------- Recent Quiz Attempts ----------------

    cursor.execute("""
        SELECT
            users.name,
            subjects.name,
            quiz_attempts.percentage,
            quiz_attempts.attempt_date
        FROM quiz_attempts
        JOIN users
            ON quiz_attempts.user_id = users.id
        JOIN subjects
            ON quiz_attempts.subject_id = subjects.id
        ORDER BY quiz_attempts.attempt_date DESC
        LIMIT 5
    """)

    recent_attempts = cursor.fetchall()


    # ---------------- Top 10 Students ----------------

    cursor.execute("""
        SELECT
            users.name,
            users.profile_pic,
            MAX(quiz_attempts.percentage) AS best_score
        FROM quiz_attempts
        JOIN users
            ON quiz_attempts.user_id = users.id
        GROUP BY
            users.id,
            users.name,
            users.profile_pic
        ORDER BY best_score DESC
        LIMIT 10
    """)

    top_students = cursor.fetchall()

    # ---------------- Most Active Students ----------------

    cursor.execute("""
        SELECT
            users.name,
            COUNT(quiz_attempts.id) AS total_attempts
        FROM users
        JOIN quiz_attempts
            ON users.id = quiz_attempts.user_id
        GROUP BY users.id
        ORDER BY total_attempts DESC
        LIMIT 5
    """)

    most_active_students = cursor.fetchall()
    # ---------------- Subject Wise Attempts ----------------

    cursor.execute("""
        SELECT
            subjects.name,
            COUNT(quiz_attempts.id)
        FROM subjects
        LEFT JOIN quiz_attempts
            ON subjects.id = quiz_attempts.subject_id
        GROUP BY subjects.id
        ORDER BY subjects.id
    """)

    subject_attempts = cursor.fetchall()
    # ---------------- Questions ----------------

    query = """
        SELECT questions.id,
               subjects.name,
               topics.topic_name,
               questions.question
        FROM questions
        JOIN subjects ON questions.subject_id = subjects.id
        JOIN topics ON questions.topic_id = topics.id
        WHERE 1=1
    """

    values = []

    if search:
        query += " AND questions.question LIKE %s"
        values.append(f"%{search}%")

    if subject:
        query += " AND subjects.name=%s"
        values.append(subject)

    query += " ORDER BY questions.id DESC"

    cursor.execute(query, tuple(values))
    questions = cursor.fetchall()

    print(questions)

    return render_template(
        "admin.html",
        questions=questions,
        search=search,
        subject=subject,
        total_students=total_students,
        total_questions=total_questions,
        total_attempts=total_attempts,
        total_subjects=total_subjects,
        recent_students=recent_students,
        recent_attempts=recent_attempts,
        top_students=top_students,
        most_active_students=most_active_students,
        subject_attempts=subject_attempts
    )

# ---------------- ADD QUESTION ----------------

@app.route("/add_question", methods=["GET", "POST"])
def add_question():

    if "user_id" not in session:
        return redirect(url_for("login"))

    cursor = get_db().cursor()

    # Admin check
    cursor.execute(
        "SELECT role FROM users WHERE id=%s",
        (session["user_id"],)
    )

    user = cursor.fetchone()

    if not user or user[0] != "admin":
        return "Access Denied"

    if request.method == "POST":

        subject_id = request.form["subject_id"]
        topic_id = request.form["topic_id"]
        question = request.form["question"]
        option1 = request.form["option1"]
        option2 = request.form["option2"]
        option3 = request.form["option3"]
        option4 = request.form["option4"]
        correct_option = request.form["correct_option"]

        cursor.execute("""
            INSERT INTO questions
            (subject_id, topic_id, question,
             option1, option2, option3, option4,
             correct_option)
            VALUES(%s,%s,%s,%s,%s,%s,%s,%s)
        """, (
            subject_id,
            topic_id,
            question,
            option1,
            option2,
            option3,
            option4,
            correct_option
        ))

        db.commit()

        flash("Question added successfully!", "success")

        return redirect(url_for("admin"))
    
    cursor.execute("SELECT * FROM subjects")
    subjects = cursor.fetchall()

    cursor.execute("SELECT * FROM topics")
    topics = cursor.fetchall()

    return render_template(
        "add_question.html",
        subjects=subjects,
        topics=topics
    )

# ---------------- DELETE QUESTION ----------------

@app.route("/delete_question/<int:question_id>")
def delete_question(question_id):

    if "user_id" not in session:
        return redirect(url_for("login"))

    cursor = get_db().cursor()

    # Check admin
    cursor.execute(
        "SELECT role FROM users WHERE id=%s",
        (session["user_id"],)
    )

    user = cursor.fetchone()

    if not user or user[0] != "admin":
        return "Access Denied"

    cursor.execute(
        "DELETE FROM questions WHERE id=%s",
        (question_id,)
    )

    db.commit()

    flash("Question deleted successfully!", "danger")

    return redirect(url_for("admin"))

# ---------------- EDIT QUESTION ----------------

@app.route("/edit_question/<int:question_id>", methods=["GET", "POST"])
def edit_question(question_id):

    if "user_id" not in session:
        return redirect(url_for("login"))

    cursor = get_db().cursor()

    cursor.execute(
        "SELECT role FROM users WHERE id=%s",
        (session["user_id"],)
    )

    user = cursor.fetchone()

    if not user or user[0] != "admin":
        return "Access Denied"

    if request.method == "POST":

        cursor.execute("""
            UPDATE questions
            SET question=%s,
                option1=%s,
                option2=%s,
                option3=%s,
                option4=%s,
                correct_option=%s
            WHERE id=%s
        """, (

            request.form["question"],
            request.form["option1"],
            request.form["option2"],
            request.form["option3"],
            request.form["option4"],
            request.form["correct_option"],
            question_id

        ))

        db.commit()

        flash("Question updated successfully!", "warning")

        return redirect(url_for("admin"))
    
    cursor.execute(
        "SELECT * FROM questions WHERE id=%s",
        (question_id,)
    )

    question = cursor.fetchone()

    return render_template(
        "edit_question.html",
        question=question
    )
@app.route("/students")
def students():

    if "user_id" not in session:
        return redirect(url_for("login"))

    cursor = get_db().cursor()

    search = request.args.get("search", "").strip()

    cursor.execute(
        "SELECT role FROM users WHERE id=%s",
        (session["user_id"],)
    )

    user = cursor.fetchone()

    if not user or user[0] != "admin":
        return "Access Denied"

    cursor.execute("""
    SELECT
        users.id,
        users.name,
        users.email,
        users.phone,
        users.role,
        users.created_at,
        COUNT(quiz_attempts.id) AS attempts,
        IFNULL(MAX(quiz_attempts.percentage),0) AS best_score,
        users.profile_pic
    FROM users
    LEFT JOIN quiz_attempts
    ON users.id = quiz_attempts.user_id
    WHERE
        users.name LIKE %s
        OR users.email LIKE %s
        OR users.phone LIKE %s
    GROUP BY
        users.id,
        users.name,
        users.email,
        users.phone,
        users.role,
        users.created_at,
        users.profile_pic
    ORDER BY users.id DESC
    """, (
        f"%{search}%",
        f"%{search}%",
        f"%{search}%"
    ))

    students = cursor.fetchall()

    return render_template(
        "students.html",
        students=students
    )

@app.route("/admin_edit_student/<int:user_id>", methods=["GET", "POST"])
def admin_edit_student(user_id):

    if "user_id" not in session:
        return redirect(url_for("login"))

    cursor = get_db().cursor()

    # Check Admin
    cursor.execute(
        "SELECT role FROM users WHERE id=%s",
        (session["user_id"],)
    )

    admin = cursor.fetchone()

    if not admin or admin[0] != "admin":
        return "Access Denied"

    if request.method == "POST":

        name = request.form["name"]
        phone = request.form["phone"]
        role = request.form["role"]

        file = request.files.get("profile_pic")

        cursor.execute(
            "SELECT profile_pic FROM users WHERE id=%s",
            (user_id,)
        )

        old = cursor.fetchone()

        filename = old[0] if old and old[0] else "default.jpg"

        if file and file.filename != "":

            filename = secure_filename(file.filename)

            upload_folder = os.path.join(app.root_path, "..", "static", "uploads")
            upload_folder = os.path.abspath(upload_folder)

            os.makedirs(upload_folder, exist_ok=True)

            file.save(os.path.join(upload_folder, filename))

        cursor.execute("""
            UPDATE users
            SET
                name=%s,
                phone=%s,
                role=%s,
                profile_pic=%s
            WHERE id=%s
        """,(
                name,
                phone,
                role,
                filename,
                user_id
            ))

        get_db().commit()

        flash("Student Updated Successfully!", "success")

        return redirect(url_for("students"))

    cursor.execute("""
        SELECT
            id,
            name,
            email,
            phone,
            role,
            profile_pic
        FROM users
        WHERE id=%s
    """, (user_id,))

    student = cursor.fetchone()

    return render_template(
        "admin_edit_student.html",
        student=student
    )

@app.route("/delete_student/<int:user_id>")
def delete_student(user_id):

    if "user_id" not in session:
        return redirect(url_for("login"))

    cursor = get_db().cursor()

    # Check admin
    cursor.execute(
        "SELECT role FROM users WHERE id=%s",
        (session["user_id"],)
    )

    admin = cursor.fetchone()

    if not admin or admin[0] != "admin":
        return "Access Denied"

    # Admin apna account delete na kar sake
    if user_id == session["user_id"]:
        flash("You cannot delete your own account.", "danger")
        return redirect(url_for("students"))

    # Student delete
    cursor.execute(
        "DELETE FROM users WHERE id=%s",
        (user_id,)
    )

    get_db().commit()

    flash("Student Deleted Successfully!", "success")

    return redirect(url_for("students"))

@app.route("/student_profile/<int:user_id>")
def student_profile(user_id):

    if "user_id" not in session:
        return redirect(url_for("login"))

    cursor = get_db().cursor()

    # Admin Check
    cursor.execute(
        "SELECT role FROM users WHERE id=%s",
        (session["user_id"],)
    )

    admin = cursor.fetchone()

    if not admin or admin[0] != "admin":
        return "Access Denied"

    # Student Details
    cursor.execute("""
        SELECT
            name,
            email,
            phone,
            role,
            created_at,
            profile_pic
        FROM users
        WHERE id=%s
    """, (user_id,))

    student = cursor.fetchone()

    # Quiz Statistics
    cursor.execute("""
        SELECT
            COUNT(*),
            IFNULL(MAX(percentage),0),
            IFNULL(AVG(percentage),0),
            COUNT(DISTINCT subject_id)
        FROM quiz_attempts
        WHERE user_id=%s
    """, (user_id,))

    stats = cursor.fetchone()

    # Subject Wise Best Performance

    cursor.execute("""
        SELECT
            subjects.name,
            MAX(quiz_attempts.percentage)
        FROM quiz_attempts
        JOIN subjects
            ON quiz_attempts.subject_id = subjects.id
        WHERE quiz_attempts.user_id=%s
        GROUP BY subjects.id
        ORDER BY MAX(quiz_attempts.percentage) DESC
    """, (user_id,))

    subject_performance = cursor.fetchall()

    # Student Quiz Attempt History

    cursor.execute("""
        SELECT
            subjects.name,
            topics.topic_name,
            quiz_attempts.score,
            quiz_attempts.percentage,
            quiz_attempts.attempt_date
        FROM quiz_attempts
        JOIN subjects
            ON quiz_attempts.subject_id = subjects.id
        JOIN topics
            ON quiz_attempts.topic_id = topics.id
        WHERE quiz_attempts.user_id=%s
        ORDER BY quiz_attempts.attempt_date DESC
    """, (user_id,))

    attempt_history = cursor.fetchall()

    # Last Attempt Date

    cursor.execute("""
        SELECT
            attempt_date
        FROM quiz_attempts
        WHERE user_id=%s
        ORDER BY attempt_date DESC
        LIMIT 1
    """, (user_id,))

    last_attempt = cursor.fetchone()

    return render_template(
        "student_profile.html",
        student=student,
        stats=stats,
        last_attempt=last_attempt,
        subject_performance=subject_performance,
        attempt_history=attempt_history
    )

@app.route("/attempts")
def attempts():

    if "user_id" not in session:
        return redirect(url_for("login"))

    cursor = get_db().cursor()

    # Admin Check
    cursor.execute(
        "SELECT role FROM users WHERE id=%s",
        (session["user_id"],)
    )

    user = cursor.fetchone()

    if not user or user[0] != "admin":
        return "Access Denied"

    search = request.args.get("search", "")

    query = """
        SELECT
            users.name,
            subjects.name,
            topics.topic_name,
            quiz_attempts.score,
            quiz_attempts.percentage,
            quiz_attempts.attempt_date
        FROM quiz_attempts
        JOIN users
            ON quiz_attempts.user_id = users.id
        JOIN subjects
            ON quiz_attempts.subject_id = subjects.id
        JOIN topics
            ON quiz_attempts.topic_id = topics.id
        WHERE 1=1
    """

    values = []

    if search:
        query += " AND users.name LIKE %s"
        values.append(f"%{search}%")

    query += """
        ORDER BY quiz_attempts.attempt_date DESC
    """

    cursor.execute(query, tuple(values))

    attempts = cursor.fetchall()

    cursor.execute("""
        SELECT
            COUNT(*),
            AVG(percentage),
            MAX(percentage)
        FROM quiz_attempts
    """)

    stats = cursor.fetchone()

    return render_template(
        "attempts.html",
        attempts=attempts,
        stats=stats,
        search=search
    )

@app.route("/download_report")
def download_report():

    if "user_id" not in session:
        return redirect(url_for("login"))

    cursor = get_db().cursor()

    cursor.execute(
        "SELECT role FROM users WHERE id=%s",
        (session["user_id"],)
    )

    user = cursor.fetchone()

    if not user or user[0] != "admin":
        return "Access Denied"

    cursor.execute("""
        SELECT
            users.name,
            subjects.name,
            topics.topic_name,
            quiz_attempts.score,
            quiz_attempts.percentage,
            quiz_attempts.attempt_date
        FROM quiz_attempts
        JOIN users
            ON quiz_attempts.user_id = users.id
        JOIN subjects
            ON quiz_attempts.subject_id = subjects.id
        JOIN topics
            ON quiz_attempts.topic_id = topics.id
        ORDER BY quiz_attempts.attempt_date DESC
    """)

    attempts = cursor.fetchall()

    pdf_file = "quiz_report.pdf"

    doc = SimpleDocTemplate(pdf_file)

    data = [[
        "Student",
        "Subject",
        "Topic",
        "Score",
        "Percentage",
        "Date"
    ]]

    for row in attempts:
        data.append([
            row[0],
            row[1],
            row[2],
            str(row[3]),
            f"{row[4]}%",
            row[5].strftime("%d-%m-%Y")
        ])

    table = Table(data)

    table.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (-1,0), colors.darkblue),
        ("TEXTCOLOR", (0,0), (-1,0), colors.white),
        ("GRID", (0,0), (-1,-1), 1, colors.black),
        ("BACKGROUND", (0,1), (-1,-1), colors.beige),
        ("ALIGN", (0,0), (-1,-1), "CENTER"),
        ("BOTTOMPADDING", (0,0), (-1,0), 10),
    ]))

    doc.build([table])

    return send_file(pdf_file, as_attachment=True)

# ---------------- 404 ERROR PAGE ----------------

@app.errorhandler(404)
def page_not_found(e):
    return render_template("404.html"), 404

# ---------------- RUN ----------------
if __name__ == "__main__":
    print(app.url_map)
    app.run(debug=True)