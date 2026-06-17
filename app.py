from flask import Flask , jsonify,request
import json
import os
from datetime import date

app = Flask(__name__) #APP

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

questions = [
    "WHAT THE HELLLLLL? ",
    "Who invented Python?",
    "Which is faster, frontend or backend? ",
    "What is 2 + 2 in computer language?",
    "Why is the library WiFi always slow? "
]

correct_answers = {
    1: "A",
    2: "B",
    3: "C",
    4: "D",
    5: "A"
}

#===============Main==============


@app.route('/')
def main():
    return "AVGP Library Quiz Backend"

#======================Reading Day Quiz==================


@app.route("/reading-day-quiz")
def reading_day_quiz():
    return jsonify({
        "title":"Reading day quiz",
        "status" : "online",
        "startDate": "2026-06-19",
        "endDate": "2026-07-02"
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
        "question": current_question_global
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

    # check correct answer
    correct_answer = correct_answers.get(question_no)
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


@app.route("/Submissions")
def get_submissions():
    password = request.args.get("password")

    if password != ADMIN_PASSWORD:
        return jsonify({"status": "error", "message": "Invalid password"}), 401

    return jsonify(submissions)


@app.route("/leaderboard")
def leaderboard():
    today = str(date.today())

    today_data = [
        s for s in submissions
        if s.get("date") == today and s.get("timeTaken") is not None
    ]

    # sort fastest first
    sorted_data = sorted(today_data, key=lambda x: x["timeTaken"])

    # assign rank
    for i, entry in enumerate(sorted_data):
        entry["rank"] = i + 1

    return jsonify({
        "date": today,
        "count": len(sorted_data),
        "leaderboard": sorted_data
    })




if __name__ == "__main__":
    app.run()


