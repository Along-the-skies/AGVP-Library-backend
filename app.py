

from flask import Flask, jsonify, request
import json, os
from datetime import date
from flask_cors import CORS
from urllib.parse import unquote

# Firebase imports
import firebase_admin
from firebase_admin import credentials, firestore

app = Flask(__name__)
CORS(app)

# JSON file paths
DATA_FILE = "submissions.json"
ARCHIVE_FILE = "qa_archive.json"
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "Agp2026access_BinoyMathew")


def load_json_file(path, default):
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            return default
    return default


def save_json_file(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4)


def safe_time_taken(value):
    try:
        return float(value)
    except (TypeError, ValueError):
        return float("inf")


submissions = load_json_file(DATA_FILE, [])
qa_archive = load_json_file(ARCHIVE_FILE, [])

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

# Firebase setup
firebase_key_json = os.environ.get("SERVICE_ACCOUNT_KEY_JSON")
if firebase_key_json:
    try:
        cred_dict = json.loads(firebase_key_json)
        cred = credentials.Certificate(cred_dict)
        firebase_admin.initialize_app(cred)
        db = firestore.client()
        FIREBASE_ENABLED = True
    except Exception as e:
        print("⚠️ Firebase not initialized from env var:", e)
        FIREBASE_ENABLED = False
else:
    try:
        cred = credentials.Certificate("serviceAccountKey.json")
        firebase_admin.initialize_app(cred)
        db = firestore.client()
        FIREBASE_ENABLED = True
    except Exception as e:
        print("⚠️ Firebase not initialized from file:", e)
        FIREBASE_ENABLED = False

@app.route('/')
def main():
    return "AGVP Library Quiz Backend (JSON + Firestore)"

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

    # Validation
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

    # Prevent duplicate in JSON
    for entry in submissions:
        if entry["phone"] == phone and entry.get("date") == today_str and entry.get("questionNo") == question_no:
            return jsonify({"status": "error", "message": "Already submitted"}), 409

    submission = {
        "name": name,
        "phone": phone,
        "answer": answer,
        "questionNo": question_no,
        "timeTaken": time_taken,
        "isCorrect": is_correct,
        "date": today_str
    }

    # Save to JSON
    submissions.append(submission)
    save_json_file(DATA_FILE, submissions)

    found = False
    for r in qa_archive:
        if r["date"] == today_str and r["questionNo"] == question_no:
            r["answers"].append(submission)
            found = True
            break
    if not found:
        qa_archive.append({
            "date": today_str,
            "questionNo": question_no,
            "question": questions[question_no - 1],
            "answers": [submission]
        })
    save_json_file(ARCHIVE_FILE, qa_archive)

    # Save to Firestore (optional)
    if FIREBASE_ENABLED:
        try:
            db.collection("submissions").add(submission)
        except Exception as e:
            print("⚠️ Firestore write failed:", e)

    return jsonify({"status": "success", "isCorrect": is_correct, "timeTaken": time_taken})


@app.route("/submissions")
def submissions_view():
    password = request.args.get("password")
    if not password or unquote(password).strip() != ADMIN_PASSWORD:
        return "Unauthorized", 403

    subs = load_json_file(DATA_FILE, [])

    if request.args.get("format") == "json" or "application/json" in request.headers.get("Accept", ""):
        grouped = {}
        for sub in subs:
            date_key = sub.get("date")
            grouped.setdefault(date_key, []).append(sub)
        return jsonify({"submissions": grouped})

    grouped = {}
    for sub in subs:
        date_key = sub.get("date")
        grouped.setdefault(date_key, []).append(sub)

    sorted_dates = sorted(grouped.keys(), reverse=True)

    html = "<div class='submissions-wrapper'>"
    html += "<style>"
    html += ".submissions-wrapper{font-family:Arial,Helvetica,sans-serif;color:#222;}"
    html += ".leaderboards-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(320px,1fr));gap:20px;margin:20px 0;}"
    html += ".table-box{padding:18px;border:1px solid #ddd;border-radius:14px;background:#fafafa;box-shadow:0 2px 10px rgba(0,0,0,0.05);overflow-x:auto;}"
    html += ".table-box h2{margin-top:0;font-size:1.1rem;color:#333;}"
    html += ".leaderboard{width:100%;border-collapse:collapse;margin-top:12px;}"
    html += ".leaderboard th,.leaderboard td{border:1px solid #ddd;padding:10px;text-align:left;font-size:0.95rem;}"
    html += ".leaderboard th{background:#5b3ea6;color:#fff;}"
    html += ".leaderboard td{background:#fff;}"
    html += ".no-data{color:#666;padding:12px;}"
    html += "</style>"
    html += "<h1>Quiz Submissions (Admin View)</h1>"
    html += "<div class='leaderboards-grid'>"

    for i in range(14):
        if i < len(sorted_dates):
            date_key = sorted_dates[i]
            html += f"<div class='table-box'><h2>{date_key} Leaderboard</h2>"
            html += "<table class='leaderboard'><tr><th>Name</th><th>Phone</th><th>Question</th><th>Answer</th><th>Correct</th><th>Time Taken</th></tr>"
            day_subs = sorted(grouped[date_key], key=lambda x: (0 if x.get("isCorrect") else 1, safe_time_taken(x.get("timeTaken"))))
            for sub in day_subs:
                html += f"<tr><td>{sub.get('name','')}</td><td>{sub.get('phone','')}</td><td>{sub.get('questionNo','')}</td><td>{sub.get('answer','')}</td><td>{'✅' if sub.get('isCorrect') else '❌'}</td><td>{sub.get('timeTaken','')}s</td></tr>"
            html += "</table></div>"
        else:
            html += f"<div class='table-box'><h2>Leaderboard {i+1} (No Data)</h2>"
            html += "<table class='leaderboard'><tr><th>Name</th><th>Phone</th><th>Question</th><th>Answer</th><th>Correct</th><th>Time Taken</th></tr>"
            html += "<tr><td colspan='6' class='no-data'>No submissions yet</td></tr>"
            html += "</table></div>"

    html += "</div></div>"
    return html

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)), debug=False)