from flask import Flask, jsonify, request
from datetime import date
from flask_cors import CORS
from urllib.parse import unquote
import os
import psycopg2
from psycopg2.extras import RealDictCursor
import json   # ✅ Added back

app = Flask(__name__)
CORS(app)

ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "default_password")
DATABASE_URL = os.environ.get("DATABASE_URL")

# Dates
start_date = date(2026, 6, 19)
end_date = date(2026, 7, 2)

# Questions
questions = [
    {"question": "Question 1", "choices": ["A","B","C","D"], "answer": "A"},
    {"question": "Question 2", "choices": ["A","B","C","D"], "answer": "B"},
    {"question": "Question 3", "choices": ["A","B","C","D"], "answer": "C"},
    {"question": "Question 4", "choices": ["A","B","C","D"], "answer": "D"},
    {"question": "Question 5", "choices": ["A","B","C","D"], "answer": "A"},
    {"question": "Question 6", "choices": ["A","B","C","D"], "answer": "B"},
    {"question": "Question 7", "choices": ["A","B","C","D"], "answer": "C"},
    {"question": "Question 8", "choices": ["A","B","C","D"], "answer": "A"},
    {"question": "Question 9", "choices": ["A","B","C","D"], "answer": "D"},
    {"question": "Question 10", "choices": ["A","B","C","D"], "answer": "B"},
    {"question": "Question 11", "choices": ["A","B","C","D"], "answer": "C"},
    {"question": "Question 12", "choices": ["A","B","C","D"], "answer": "A"},
    {"question": "Question 13", "choices": ["A","B","C","D"], "answer": "B"},
    {"question": "Question 14", "choices": ["A","B","C","D"], "answer": "C"}
]

def get_db_connection():
    return psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor)

@app.route('/')
def main():
    return "AGVP Library Quiz Backend (Postgres)"

@app.route("/reading-day-quiz")
def reading_day_quiz():
    today = date.today()
    if today < start_date:
        status = "not_started"
    elif today > end_date:
        status = "ended"
    else:
        status = "online"
    return jsonify({
        "title": "Reading day quiz",
        "status": status,
        "startDate": str(start_date),
        "endDate": str(end_date)
    })

@app.route("/question")
def question():
    today = date.today()
    if today < start_date:
        return jsonify({"status": "not_started"})
    if today > end_date:
        return jsonify({"status": "ended"})
    day_index = (today - start_date).days
    if day_index < 0 or day_index >= len(questions):
        return jsonify({"status": "no_question"})
    current_question = questions[day_index]
    return jsonify({
        "questionNo": day_index + 1,
        "question": current_question["question"],
        "choices": current_question["choices"]
    })

@app.route("/submit", methods=["POST"])
def submit():
    data = request.get_json()
    name = data.get("name")
    phone = data.get("phone")
    answer = data.get("answer")
    question_no = data.get("questionNo")
    time_taken = data.get("timeTaken")
    today_str = str(date.today())

    # ✅ Safer validation
    try:
        question_no = int(question_no)
        if question_no < 1 or question_no > len(questions):
            return jsonify({"status":"error","message":"Invalid question number"}), 400
    except:
        return jsonify({"status":"error","message":"Invalid question number"}), 400

    if name is None or phone is None or answer is None:
        return jsonify({"status": "error", "message": "Missing fields"}), 400
    if not phone.isdigit() or len(phone) != 10:
        return jsonify({"status":"error","message":"Invalid phone number"}), 400
    if name.lower() == "admin":
        return jsonify({"status":"error","message":"Reserved name not allowed"}), 400

    correct_answer = questions[question_no - 1]["answer"]
    is_correct = (answer == correct_answer)

    conn = get_db_connection()
    cur = conn.cursor()

    # Check duplicate
    cur.execute("""
        SELECT 1 FROM submissions
        WHERE phone=%s AND date=%s AND question_no=%s
    """, (phone, today_str, question_no))
    if cur.fetchone():
        cur.close()
        conn.close()
        return jsonify({"status": "error", "message": "Already submitted"}), 409

    # Insert submission
    cur.execute("""
        INSERT INTO submissions (name, phone, answer, question_no, time_taken, is_correct, date)
        VALUES (%s,%s,%s,%s,%s,%s,%s)
    """, (name, phone, answer, question_no, time_taken, is_correct, today_str))

    # Archive (requires UNIQUE(date, question_no) on qa_archive)
    submission_json = json.dumps([{
        "name": name,
        "phone": phone,
        "answer": answer,
        "questionNo": question_no,
        "timeTaken": time_taken,
        "isCorrect": is_correct,
        "date": today_str
    }])
    cur.execute("""
        INSERT INTO qa_archive (date, question_no, question, answer_data)
        VALUES (%s,%s,%s,%s)
        ON CONFLICT (date, question_no) DO UPDATE
        SET answer_data = qa_archive.answer_data || %s
    """, (today_str, question_no, questions[question_no-1]["question"], submission_json, submission_json))

    conn.commit()
    cur.close()
    conn.close()

    return jsonify({"status": "success", "isCorrect": is_correct, "timeTaken": time_taken})

@app.route("/submissions")
def submissions_view():
    password = request.args.get("password")
    if not password or unquote(password).strip() != ADMIN_PASSWORD:
        return "Unauthorized", 403

    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM submissions ORDER BY date DESC, time_taken ASC")
    subs = cur.fetchall()
    cur.close()
    conn.close()

    grouped = {}
    for sub in subs:
        date_key = sub["date"]
        grouped.setdefault(date_key, []).append(sub)

    sorted_dates = sorted(grouped.keys(), reverse=True)

    html = "<html><head><link rel='stylesheet' href='/static/style.css'></head><body>"
    html += "<h1>Quiz Submissions (Admin View)</h1>"
    html += "<div style='display:grid; grid-template-columns:repeat(2, 1fr); gap:20px;'>"

    for i in range(14):
        if i < len(sorted_dates):
            date_key = sorted_dates[i]
            html += f"<div class='table-box'><h2>{date_key} Leaderboard</h2>"
            html += "<table class='leaderboard'><tr><th>Name</th><th>Phone</th><th>Question</th><th>Answer</th><th>Correct</th><th>Time Taken</th></tr>"
            day_subs = sorted(grouped[date_key], key=lambda x: float(x["time_taken"]))
            for sub in day_subs:
                html += f"<tr><td>{sub['name']}</td><td>{sub['phone']}</td><td>{sub['question_no']}</td><td>{sub['answer']}</td><td>{'✅' if sub['is_correct'] else '❌'}</td><td>{sub['time_taken']}s</td></tr>"
            html += "</table></div>"
        else:
            html += f"<div class='table-box'><h2>Leaderboard {i+1} (No Data)</h2>"
            html += "<table class='leaderboard'><tr><th>Name</th><th>Phone</th><th>Question</th><th>Answer</th><th>Correct</th><th>Time Taken</th></tr>"
            html += "<tr><td colspan='6'>No submissions yet</td></tr></table></div>"

    html += "</body></html>"
    return html

@app.route("/db-test")
def db_test():
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT 1")
        cur.fetchone()
        cur.close()
        conn.close()
        return {"status": "connected"}   # ✅ simplified
    except Exception as e:
        return {"status": "failed", "error": str(e)}, 500

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)