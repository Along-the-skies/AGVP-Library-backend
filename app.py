from flask import Flask, jsonify, request
import json, os
from datetime import date
from flask_cors import CORS
from urllib.parse import unquote

app = Flask(__name__)
CORS(app)

DATA_FILE = "submissions.json"
ARCHIVE_FILE = "qa_archive.json"
ADMIN_PASSWORD = "Agp2026access_BinoyMathew"

# Load submissions
if os.path.exists(DATA_FILE):
    with open(DATA_FILE, "r") as f:
        submissions = json.load(f)
else:
    submissions = []

# Load archive
if os.path.exists(ARCHIVE_FILE):
    with open(ARCHIVE_FILE, "r") as f:
        qa_archive = json.load(f)
else:
    qa_archive = []

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

day_index_global = 0
current_question_global = {}

@app.route('/')
def main():
    return "AGVP Library Quiz Backend"

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
    global day_index_global, current_question_global
    day_index_global = day_index
    current_question_global = questions[day_index]
    return jsonify({
        "questionNo": day_index + 1,
        "question": current_question_global["question"],
        "choices": current_question_global["choices"]
    })

@app.route("/submit", methods=["POST"])
def submit():
    data = request.get_json()
    name = data.get("name")
    phone = data.get("phone")
    answer = data.get("answer")
    question_no = data.get("questionNo")
    time_taken = data.get("timeTaken")
    today = str(date.today())

    if not name or not phone or not answer or not question_no:
        return jsonify({"status": "error", "message": "Missing fields"}), 400
    if not phone.isdigit() or len(phone) != 10:
        return jsonify({"status":"error","message":"Invalid phone number"}), 400
    if name.lower() == "admin":
        return jsonify({"status":"error","message":"Reserved name not allowed"}), 400

    correct_answer = questions[day_index_global]["answer"]
    is_correct = (answer == correct_answer)

    for entry in submissions:
        if entry["phone"] == phone and entry.get("date") == today and entry.get("questionNo") == question_no:
            return jsonify({"status": "error", "message": "Already submitted"}), 409

    submission = {
        "name": name,
        "phone": phone,
        "answer": answer,
        "questionNo": question_no,
        "timeTaken": time_taken,
        "isCorrect": is_correct,
        "date": today
    }
    submissions.append(submission)
    with open(DATA_FILE, "w") as f:
        json.dump(submissions, f, indent=4)

    found = False
    for r in qa_archive:
        if r["date"] == today and r["questionNo"] == question_no:
            r["answers"].append(submission)
            found = True
            break
    if not found:
        qa_archive.append({
            "date": today,
            "questionNo": question_no,
            "question": current_question_global,
            "answers": [submission]
        })
    with open(ARCHIVE_FILE, "w") as f:
        json.dump(qa_archive, f, indent=4)

    return jsonify({"status": "success", "isCorrect": is_correct, "timeTaken": time_taken})

@app.route("/submissions")
def submissions_view():
    password = request.args.get("password")
    if not password or unquote(password).strip() != ADMIN_PASSWORD:
        return "Unauthorized", 403

    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r") as f:
            subs = json.load(f)
    else:
        subs = []

    grouped = {}
    for sub in subs:
        date_key = sub.get("date")
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
            day_subs = sorted(grouped[date_key], key=lambda x: x["timeTaken"])
            for sub in day_subs:
                html += f"<tr><td>{sub['name']}</td><td>{sub['phone']}</td><td>{sub['questionNo']}</td><td>{sub['answer']}</td><td>{'✅' if sub['isCorrect'] else '❌'}</td><td>{sub['timeTaken']}s</td></tr>"
            html += "</table></div>"
        else:
            html += f"<div class='table-box'><h2>Leaderboard {i+1} (No Data)</h2>"
            html += "<table class='leaderboard'><tr><th>Name</th><th>Phone</th><th>Question</th><th>Answer</th><th>Correct</th><th>Time Taken</th></tr>"
            html += "<tr><td colspan='6'>No submissions yet</td></tr></table></div>"


    html += "</body></html>"
    return html



import psycopg2
import os

@app.route("/db-test")
def db_test():
    try:
        conn = psycopg2.connect(os.environ.get("DATABASE_URL"))

        cur = conn.cursor(["DATABASE_URL"])

        cur = conn.cursor()
        cur.execute("SELECT 1")

        result = cur.fetchone()

        cur.close()
        conn.close()

        return {"status": "connected"}

    except Exception as e:
        return {
            "status": "failed",
            "error": str(e)
        }, 500

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
