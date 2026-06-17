from flask import Flask , jsonify,request
import json
import os
from datetime import date
from flask_cors import CORS


app = Flask(__name__) #APP
CORS(app)

qa_archive = []

submissions = []

DATA_FILE = "submissions.json"
ARCHIVE_FILE = "qa_archive.json"
ADMIN_PASSWORD = "Agp2026access:BinoyMathew"
day_index_global = 0
current_question_global = ""

if os.path.exists(DATA_FILE):
    with open(DATA_FILE, "r") as f:
        submissions = json.load(f)
else:
    submissions = []

if os.path.exists(ARCHIVE_FILE):
    with open(ARCHIVE_FILE, "r") as f:
        qa_archive = json.load(f)

else:
    qa_archive = []


#=================DateSystem===================

start_date = date(2026, 6, 19)
end_date = date(2026, 7, 2)



#=============Questions(TOP SECRET USA AIRBASE PASSWORD IS HERE)===================

questions = [{
    "question": "Question 1",
    "choices" : ["A","B","C","D"],
    "answer": "A"
},{
    "question": "Question 2",
    "choices" : ["A","B","C","D"],
    "answer": "B"
},{
    "question": "Question 3",
    "choices" : ["A","B","C","D"],
    "answer": "C"
},{
    "question": "Question 4",
    "choices" : ["A","B","C","D"],
    "answer": "D"
},{
    "question": "Question 5",
    "choices" : ["A","B","C","D"],
    "answer": "A"
},{
    "question": "Question 6",
    "choices" : ["A","B","C","D"],
    "answer": "B"
},{ 
    "question": "Question 7",
    "choices" : ["A","B","C","D"],
    "answer": "C"
},{
    "question": "Question 8",
    "choices" : ["A","B","C","D"],
    "answer": "A"
},{
    "question": "Question 9",
    "choices" : ["A","B","C","D"],
    "answer": "D"
},{
    "question": "Question 10",
    "choices" : ["A","B","C","D"],
    "answer": "B"
},{
    "question": "Question 11",
    "choices" : ["A","B","C","D"],
    "answer": "C"
},{
    "question": "Question 12",
    "choices" : ["A","B","C","D"],
    "answer": "A"
},{
    "question": "Question 13",
    "choices" : ["A","B","C","D"],
    "answer": "B"
},{
    "question": "Question 14",
    "choices" : ["A","B","C","D"],
    "answer": "C"

}
]




#===============Main==============


@app.route('/')
def main():
    return "AVGP Library Quiz Backend"

#======================Reading Day Quiz==================


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



#=====================Questions================



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
#=============Submit===========================


@app.route("/submit", methods=["POST"])
def submit():
    data = request.get_json()

    name = data.get("name")
    phone = data.get("phone")
    answer = data.get("answer")
    question_no = data.get("questionNo")
    time_taken = data.get("timeTaken")

    today = str(date.today())

    # basic validation
    if not name or not phone or not answer or not question_no:
        return jsonify({
            "status": "error",
            "message": "Missing fields"
        }), 400
    
    if not phone.isdigit() or len(phone) != 10:
        return jsonify({"status":"error","message":"Invalid phone number"}), 400

    if name.lower() == "admin":
        return jsonify({"status":"error","message":"Reserved name not allowed"}), 400


    # check correct answer
    correct_answer = questions[day_index_global]["answer"]
    is_correct = (answer == correct_answer)

    # prevent duplicate per day per question
    for entry in submissions:
        if (
            entry["phone"] == phone and
            entry.get("date") == today and
            entry.get("questionNo") == question_no
        ):
            return jsonify({
                "status": "error",
                "message": "Already submitted for this question today"
            }), 409

    # submission object
    submission = {
        "name": name,
        "phone": phone,
        "answer": answer,
        "questionNo": question_no,
        "timeTaken": time_taken,
        "isCorrect": is_correct,
        "date": today
    }

    # save main submissions
    submissions.append(submission)

    with open(DATA_FILE, "w") as f:
        json.dump(submissions, f, indent=4)

    # ===============================
    # 🔥 QA ARCHIVE (grouped per question)
    # ===============================

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

    return jsonify({
        "status": "success",
        "isCorrect": is_correct,
        "timeTaken": time_taken
    })



@app.route("/submissions")
def submissions_view():
    password = request.args.get("password")
    if password != "Agp2026access:BinoyMathew":
        return "Unauthorized", 403

    # Load all submissions
    with open("submissions.json", "r") as f:
        submissions = json.load(f)

    # Group by date
    grouped = {}
    for sub in submissions:
        date = sub["date"]
        grouped.setdefault(date, []).append(sub)

    # Sort dates (latest first)
    sorted_dates = sorted(grouped.keys(), reverse=True)

    # Build HTML
    html = "<html><head><link rel='stylesheet' href='/static/style.css'></head><body>"
    html += "<h1>Quiz Submissions (Admin View)</h1>"

    # Limit to 14 tables
    for date in sorted_dates[:14]:
        html += f"<h2>{date} Leaderboard</h2>"
        html += "<table class='leaderboard'><tr><th>Name</th><th>Phone</th><th>Question</th><th>Answer</th><th>Correct</th><th>Time Taken</th></tr>"
        # Sort by timeTaken for leaderboard style
        day_subs = sorted(grouped[date], key=lambda x: x["timeTaken"])
        for sub in day_subs:
            html += f"<tr><td>{sub['name']}</td><td>{sub['phone']}</td><td>{sub['questionNo']}</td><td>{sub['answer']}</td><td>{'✅' if sub['isCorrect'] else '❌'}</td><td>{sub['timeTaken']}s</td></tr>"
        html += "</table><br>"
    html += "</body></html>"

    return html









if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)

