from flask import Flask, jsonify, request
import json, os
from datetime import date
from flask_cors import CORS
from urllib.parse import unquote

app = Flask(__name__)
CORS(app)

# Files + Password
DATA_FILE = "submissions.json"
ARCHIVE_FILE = "qa_archive.json"
ADMIN_PASSWORD = "Agp2026access:BinoyMathew"

# Load data safely
def safe_load(path):
    if os.path.exists(path):
        try:
            with open(path, "r") as f:
                return json.load(f)
        except Exception:
            return []
    return []

submissions = safe_load(DATA_FILE)
qa_archive = safe_load(ARCHIVE_FILE)

# Date system
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

# Routes
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
        return jsonify({"error": "Unauthorized"}), 403

    subs = safe_load(DATA_FILE)
    grouped = {}
    for sub in subs:
        qno = sub.get("questionNo")
        if not qno:
            continue
        day_key = f"day{qno}"
        grouped.setdefault(day_key, []).append(sub)

    result = {}
    for i in range(1, 15):
        key = f"day{i}"
        result[key] = grouped.get(key, [])

    return jsonify(result)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
