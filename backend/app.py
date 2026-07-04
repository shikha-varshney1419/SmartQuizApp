from flask import Flask, render_template, request, jsonify, session, redirect, url_for, send_file
from dotenv import load_dotenv
import pymysql
import os
load_dotenv()
from reportlab.platypus import SimpleDocTemplate, Paragraph
from reportlab.lib.styles import getSampleStyleSheet

import os

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
    autocommit=True
)

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
    data = request.get_json()

    cursor = db.cursor()
    cursor.execute(
        "INSERT INTO users(name,email,password) VALUES(%s,%s,%s)",
        (data["name"], data["email"], data["password"])
    )

    return jsonify({"message": "Registration Successful"})


# ---------------- LOGIN ----------------
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "GET":
        return render_template("login.html")

    try:
        data = request.get_json()

        email = data.get("email", "").strip()
        password = data.get("password", "").strip()

        cursor = db.cursor()
        cursor.execute(
            "SELECT * FROM users WHERE email=%s AND password=%s",
            (email, password)
        )

        user = cursor.fetchone()

        if user:
            session["user_id"] = user[0]
            session["user_name"] = user[1]

            return jsonify({
                "message": "Login Successful",
                "redirect": "/dashboard"
            })

        return jsonify({"message": "Invalid Email or Password"})

    except Exception as e:
        print("LOGIN ERROR:", e)
        return jsonify({"message": "Server Error"}), 500
                

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

    cursor = db.cursor()
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

    cursor = db.cursor()

    cursor.execute("""
        SELECT * FROM questions
        WHERE subject_id=%s AND topic_id=%s
    """, (subject_id, topic_id))

    questions = cursor.fetchall()

    print("Subject:", subject_id)
    print("Topic:", topic_id)
    print("Questions:", questions)

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

    cursor = db.cursor()

    cursor.execute("""
        SELECT id, correct_option
        FROM questions
        WHERE subject_id=%s AND topic_id=%s
    """, (subject_id, topic_id))

    questions = cursor.fetchall()

    score = 0

    for q in questions:
        qid = str(q[0])
        correct = q[1]
        user_ans = request.form.get(f"q{qid}")

        if user_ans == correct:
            score += 1

    total = len(questions)
    percentage = (score / total * 100) if total > 0 else 0

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

    return render_template(
        "result.html",
        score=score,
        total=total,
        percentage=round(percentage, 2)
    )


# ---------------- LEADERBOARD ----------------
@app.route("/leaderboard")
def leaderboard():

    cursor = db.cursor()

    cursor.execute("""
        SELECT u.name, MAX(q.percentage) as best_score
        FROM quiz_attempts q
        JOIN users u ON q.user_id = u.id
        GROUP BY q.user_id
        ORDER BY best_score DESC
        LIMIT 10
    """)

    leaders = cursor.fetchall()

    return str(leaders)


# ---------------- ANALYTICS ----------------
@app.route("/analytics")
def analytics():

    if "user_id" not in session:
        return redirect(url_for("login"))

    cursor = db.cursor()

    cursor.execute("SELECT COUNT(*) FROM quiz_attempts WHERE user_id=%s", (session["user_id"],))
    total_quizzes = cursor.fetchone()[0]

    cursor.execute("SELECT AVG(percentage) FROM quiz_attempts WHERE user_id=%s", (session["user_id"],))
    avg_score = cursor.fetchone()[0] or 0

    cursor.execute("SELECT MAX(percentage) FROM quiz_attempts WHERE user_id=%s", (session["user_id"],))
    best_score = cursor.fetchone()[0] or 0

    cursor.execute("SELECT COUNT(DISTINCT subject_id) FROM quiz_attempts WHERE user_id=%s", (session["user_id"],))
    subjects = cursor.fetchone()[0]

    return render_template(
        "analytics.html",
        total_quizzes=total_quizzes,
        avg_score=round(avg_score, 2),
        best_score=round(best_score, 2),
        subjects=subjects
    )


# ---------------- CERTIFICATE ----------------
@app.route("/certificate")
def certificate():

    if "user_id" not in session:
        return redirect(url_for("login"))

    return render_template(
        "certificate.html",
        name=session.get("user_name")
    )


@app.route("/download_certificate")
def download_certificate():

    if "user_id" not in session:
        return redirect(url_for("login"))

    file_name = "certificate.pdf"

    doc = SimpleDocTemplate(file_name)
    styles = getSampleStyleSheet()

    content = []

    name = session.get("user_name")

    content.append(Paragraph("🎓 Certificate of Completion", styles["Title"]))
    content.append(Paragraph(f"This certifies that <b>{name}</b> has completed Smart Quiz.", styles["Normal"]))

    doc.build(content)

    return send_file(file_name, as_attachment=True)
   
@app.route("/subjects/<exam>")
def subjects(exam):

    cursor = db.cursor()

    if exam == "UPSC":
        subject_id = 12
    elif exam == "JEE":
        subject_id = 13
    elif exam == "SSC":
        subject_id = 14
    else:
        return "Invalid Exam"

    cursor.execute(
        "SELECT * FROM subjects WHERE id=%s",
        (subject_id,)
    )

    subjects = cursor.fetchall()

    return render_template(
        "dashboard.html",
        subjects=subjects
    )
# ---------------- RUN ----------------
if __name__ == "__main__":
    print(app.url_map)
    app.run(debug=True)