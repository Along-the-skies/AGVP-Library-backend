

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
if ADMIN_PASSWORD is not None:
    ADMIN_PASSWORD = ADMIN_PASSWORD.strip()


def load_json_file(path, default):
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, UnicodeDecodeError, IOError):
            # If the file is missing, invalid, or corrupted, reset to default.
            save_json_file(path, default)
            return default
    return default


def save_json_file(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4)


def save_submission_to_firestore(submission):
    if not FIREBASE_ENABLED:
        return False
    try:
        db.collection("submissions").add(submission)
        return True
    except Exception as e:
        print("⚠️ Firestore write failed:", e)
        return False


def load_submissions_from_firestore():
    if not FIREBASE_ENABLED:
        return None
    try:
        docs = db.collection("submissions").stream()
        return [doc.to_dict() for doc in docs]
    except Exception as e:
        print("⚠️ Firestore read failed:", e)
        return None


def clear_firestore_submissions():
    if not FIREBASE_ENABLED:
        return False
    try:
        for doc in db.collection("submissions").stream():
            doc.reference.delete()
        return True
    except Exception as e:
        print("⚠️ Firestore clear failed:", e)
        return False


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
    {"question": "കേരളത്തിലെ ഗ്രന്ഥശാലാ പ്രസ്ഥാനത്തിന്റെ അമരക്കാരനായി അറിയപ്പെടുന്ന വ്യക്തിയുടെ ചരമദിനമാണ് നമ്മൾ 'വായനദിന'മായി ആചരിക്കുന്നത്. 'വായിച്ചു വളരുക, ചിന്തിച്ചു വിവേകം നേടുക' എന്ന സന്ദേശം നൽകിയ അദ്ദേഹം ആരാണ്?", "choices": [" എം.പി പോള്‍"," പി.എന്‍ പണിക്കര്‍","കെ.എന്‍.പണിക്കര്‍","ജി.എന്‍. പണിക്കര്‍."], "answer": "B"},
    {"question": "മലയാളത്തിലെ ആദ്യത്തെ ലക്ഷണമൊത്ത നോവലായി കണക്കാക്കപ്പെടുന്ന കൃതിയാണ് ഇത്. 1889-ൽ പുറത്തിറങ്ങിയ ഈ നോവലിലെ നായിക പുതിയ കാലഘട്ടത്തിന്റെ പ്രതിനിധിയായി ചിത്രീകരിക്കപ്പെട്ടു. ഏതാണ് ഈ നോവൽ?", "choices": ["കുന്ദലത","ശാരദ","ഒരു നരിയെ കൊന്ന വെടി","ഇന്ദുലേഖ"], "answer": "D"},
    {"question": "ഭാരതത്തിലെ ഏറ്റവും ഉയർന്ന സാഹിത്യ പുരസ്കാരമായ ജ്ഞാനപീഠം ആദ്യമായി മലയാളത്തിന് നേടിക്കൊടുത്തത് ആരാണ്?", "choices": ["വൈലോപ്പിള്ളി ശ്രീധരമേനോന്‍","എന്‍. കുമാരനാശാന്‍","വള്ളത്തോള്‍ നാരായണമേനോന്‍","ജി. ശങ്കരക്കുറുപ്പ്"], "answer": "D"},
    {"question": "ബേപ്പൂർ, മാങ്കോസ്റ്റീന്‍ മരം, തലയോലപ്പറമ്പ്, ശിങ്കിടിമുങ്കന്‍  ഈ വാക്കുകളെല്ലാം ഒരു വ്യക്തിയിലേക്ക് വിരല്‍ ചൂണ്ടുന്നു. ആരാണ് ഈ വ്യക്തി.  ലളിതമായ ഭാഷയിൽ സാധാരണക്കാരുടെ ജീവിതം പറഞ്ഞ ഇദ്ദേഹം ഒരു നിശ്ചിത കാലം ജയിലിലും കഴിഞ്ഞിട്ടുണ്ട്.", "choices": ["എസ്.കെ പൊറ്റെക്കാട്","മാധവിക്കുട്ടി","വൈക്കം മുഹമ്മദ് ബഷീര്‍","എം.ടി വാസുദേവന്‍ നായര്‍"], "answer": "C"},
    {"question": "മലയാള ഭാഷയുടെ പിതാവ് എന്നറിയപ്പെടുന്ന തുഞ്ചത്ത് എഴുത്തച്ഛന്റെ പേരിൽ ഒരു സാഹിത്യ പഠന കേന്ദ്രം മലപ്പുറം ജില്ലയിൽ സ്ഥിതി ചെയ്യുന്നുണ്ട്. എവിടെയാണത്?", "choices": ["മഞ്ചേരി","പൊന്നാനി","തൃശ്ശൂര്‍","തിരൂര്‍"], "answer": "D"},
    {"question": "അറബിക്കടലിന്റെ പശ്ചാത്തലത്തിൽ ചെമ്പൻ കുഞ്ഞിന്റെയും കറുത്തമ്മയുടെയും കഥ പറഞ്ഞ തകഴിയുടെ ലോകപ്രശസ്തമായ നോവൽ ഏതാണ്? ഇതിന് സിനിമയാക്കപ്പെട്ടപ്പോൾ രാഷ്ട്രപതിയുടെ സ്വർണ്ണമെഡൽ ലഭിച്ചിട്ടുണ്ട്.", "choices": ["കയര്‍","ചെമ്മീന്‍"," രണ്ടിടങ്ങഴി","അഞ്ചു പെണ്ണുങ്ങള്‍"], "answer": "B"},
    {"question": "ഭീമന്റെ കഥയാണ് രണ്ടാമൂഴം പറഞ്ഞ് പോവുന്നത്. എന്നാല്‍ കര്‍ണന്റെ കഥ പറഞ്ഞ മറ്റൊരു നോവല്‍ മലയാളത്തില്‍ ഏറെ വായിക്കപ്പെട്ടു. ഏതാണ് ആ നോവല്‍.", "choices": ["മഞ്ഞ്","ഇനി ഞാനുറങ്ങട്ടെ","ഒരു ദേശത്തിന്റെ കഥ","ആത്രേയകം"], "answer": "B"},
    {"question": "ലോകസാഹിത്യത്തിലെ അനശ്വരരായ രണ്ട് ബാലകഥാപാത്രങ്ങളായ 'ടോം സോയറെയും' 'ഹക്കിൾബറി ഫിന്നിനെയും' സൃഷ്ടിച്ച അമേരിക്കൻ നോവലിസ്റ്റാണ് ഇദ്ദേഹം. മിസിസിപ്പി നദിയിലൂടെ പോകുന്ന കപ്പലുകളിലെ നാവികർ നദിയുടെ ആഴം അളക്കാൻ ഉപയോഗിച്ചിരുന്ന 'രണ്ട് ഫാതം സുരക്ഷിതം' (Two fathoms - safe depth) എന്നർത്ഥം വരുന്ന ഒരു പ്രയോഗത്തിൽ നിന്നാണ് അദ്ദേഹം തന്റെ ഈ ലോകപ്രശസ്തമായ തൂലികാനാമം സ്വീകരിച്ചത്. \n ഹാലിയുടെ വാൽനക്ഷത്രം ഭൂമിക്ക് സമീപത്തുകൂടി കടന്നുപോയ 1835-ൽ ജനിക്കുകയും, കൃത്യം 75 വർഷങ്ങൾക്ക് ശേഷം ആ വാൽനക്ഷത്രം വീണ്ടും പ്രത്യക്ഷപ്പെട്ട 1910-ൽ തന്നെ അന്തരിക്കുകയും ചെയ്ത ഈ വിശ്വപ്രസിദ്ധ സാഹിത്യകാരൻ ആരാണ്?", "choices": ["മാര്‍ക് ട്വെയ്ന്‍","ചാള്‍സ് ഡിക്കന്‍സ്"," ജോര്‍ജ്ജ് എലിയട്ട്","വിക്തര്‍ ഹ്യൂഗോ"], "answer": "A"},
    {"question": "മലയാള സാഹിത്യത്തിലെ മഹാരഥന്മാരായ വൈക്കം മുഹമ്മദ് ബഷീർ, എസ്.കെ. പൊറ്റെക്കാട്ട്, എം.ടി. വാസുദേവൻ നായർ തുടങ്ങിയവരുടെ സാഹിത്യ പ്രവർത്തനങ്ങൾക്ക് സാക്ഷ്യം വഹിച്ച നഗരമാണ് കോഴിക്കോട്. പുസ്തകത്തെരുവായ മിഠായിത്തെരുവും നിരവധി വായനശാലകളും കൊണ്ട് സമ്പന്നമായ ഈ നഗരത്തെ, 2023 ഒക്ടോബറിൽ യുനെസ്കോ (UNESCO) ഒരു പ്രത്യേക പദവി നൽകി ആദരിച്ചു. ഇന്ത്യയിൽ ആദ്യമായാണ് ഒരു നഗരത്തിന് ഈ അംഗീകാരം ലഭിക്കുന്നത്. ഏതാണ് ആ പദവി", "choices": ["പുസ്തകനഗരം","പൈതൃക നഗരം","സംഗീത നഗരം","സാഹിത്യ നഗരം"], "answer": "D"},
    {"question": "സന്തോഷ് എച്ചിക്കാനത്തിന്റെ 'ബിരിയാണി' എന്ന ചെറുകഥ പ്രധാനമായും ചർച്ച ചെയ്യുന്ന സാമൂഹിക പ്രമേയം എന്താണ്?", "choices": ["അന്തര്‍ സംസ്ഥാന തൊഴിലാളി പ്രശ്നങ്ങള്‍","ആഡംബര വിവാഹങ്ങളിലെ മനുഷ്യത്വ വിരുദ്ധ ദൂര്‍ത്ത്","വിവാഹ പ്രശ്നങ്ങളേ പറ്റി","ഇതൊന്നുമല്ല"], "answer": "B"},
    {"question": "വെള്ളായിയപ്പന്‍ മലയാളത്തിലെ ഏത് പ്രശസ്ത കഥയിലെ കഥാപാത്രമാണ്", "choices": ["കടല്‍തീരത്ത്","വെള്ളപ്പൊക്കത്തില്‍"," ഈസ","ഗൗരി"], "answer": "A"},
    {"question": "കെ.ആര്‍ മീരയുടെ ഏറ്റവും പുതിയ നോവലിന്റെ പേര് കലാച്ചി എന്നാണ്. കലാച്ചി ഒരു രാജ്യത്തെ ഒരു ചെറു നഗരത്തിന്റെ പേരാണ്. നോവല്‍ എഴുതുന്നതിനായി എഴുത്തുകാരി ആ സ്ഥലത്ത് നേരിട്ട് പോയിരുന്നു. ഏത് രാജ്യത്താണ് കലാച്ചി", "choices": ["കസാക്കിസ്ഥാന്‍","ഉസ്ബെക്കിസ്ഥാന്‍","താജിക്കിസ്ഥാന്‍","അഫ്ഗാനിസ്ഥാന്‍"], "answer": "A"},
    {"question": "1964ല്‍ പുറത്തിറങ്ങിയ Identity Card എന്ന കവിത, സ്വാതന്ത്ര്യത്തിന്റെയും പ്രതിരോധത്തിന്റെയും കവിതയായി വാഴ്ത്തപ്പെട്ടു. \"രേഖപ്പെടുത്തുക, ഞാനൊരു അറബിയാണ്\" (Record! I am an Arab) എന്ന വരികൾ ആ കവിതയിലേതാണ്. ഈ കവിതയുമായി ബന്ധപ്പെട്ട് താഴെ ചേര്‍ക്കുന്ന കോമ്പിനേഷനിലെ ശരി തെരഞ്ഞെടുക്കുക.", "choices": ["പാലസ്തീൻ-മുഹമ്മദ് ദര്‍വ്വീഷ്","നൈജീര്യ - കെന്‍ സരോവിവ","എത്യോപ്യ - വംഗാരി മാതായ്","ഇറാന്‍ - നര്‍ഗീസ് അഹമ്മദി"], "answer": "A"},
    {"question": "നിലവാരം കുറഞ്ഞ കണ്ടന്റുകള്‍ സാമൂഹ്യമാധ്യമങ്ങളില്‍ കണ്ട് കണ്ട് മനുഷ്യന്റെ തലച്ചോറുകള്‍ പതുക്കെ നിരാശ നിറഞ്ഞ അവസ്ഥയിലേക്ക് പതിക്കുമെന്ന് സൂചിപ്പിക്കുന്ന വാക്കാണ് Brain rot. 2025 ല്‍ മറിയം വെബ്സ്റ്റേഴ്സ് ഡിക്ഷണറി നിലവാരം കുറഞ്ഞ കണ്ടന്റുകളെ സൂചിപ്പിക്കുന്ന ഒരു വാക്കിനെ ആ വര്‍ഷത്തിന്റെ വാക്കായി തെരഞ്ഞെടുത്തു. ഏതാണ് ഈ വാക്ക്.", "choices": ["Slop","Doom-scrol","Slope","Nightmare"], "answer": "A"}
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

@app.route("/check-submission", methods=["POST"])
def check_submission():
    data = request.get_json()
    if data is None:
        return jsonify({"status": "error", "message": "Invalid JSON"}), 400
    
    phone = data.get("phone")
    today_str = str(date.today())

    if phone is None or not phone.isdigit() or len(phone) != 10:
        return jsonify({"status": "error", "message": "Invalid phone number"}), 400

    # Check if user already submitted today
    for entry in submissions:
        if entry["phone"] == phone and entry.get("date") == today_str:
            return jsonify({"alreadySubmitted": True}), 200

    # Also check Firestore if enabled
    if FIREBASE_ENABLED:
        try:
            query = db.collection("submissions").where("phone", "==", phone).where("date", "==", today_str).limit(1).stream()
            if list(query):
                return jsonify({"alreadySubmitted": True}), 200
        except Exception as e:
            print("⚠️ Firestore check failed:", e)

    return jsonify({"alreadySubmitted": False}), 200

@app.route("/submit", methods=["POST"])
def submit():
    data = request.get_json()
    if data is None:
        return jsonify({"status": "error", "message": "Invalid JSON"}), 400

    name = data.get("name", "").strip()
    phone = data.get("phone", "").strip()
    answer = data.get("answer", "").strip()
    question_no = data.get("questionNo")
    time_taken = data.get("timeTaken")
    today_str = str(date.today())

    # Validation
    if not name or not phone or not answer or question_no is None:
        return jsonify({"status": "error", "message": "Missing fields"}), 400

    try:
        question_no = int(question_no)
        if question_no < 1 or question_no > len(questions):
            return jsonify({"status": "error", "message": "Invalid question number"}), 400
    except (TypeError, ValueError):
        return jsonify({"status": "error", "message": "Invalid question number"}), 400

    if not phone.isdigit() or len(phone) != 10:
        return jsonify({"status": "error", "message": "Invalid phone number"}), 400
    if name.lower() == "admin":
        return jsonify({"status": "error", "message": "Reserved name not allowed"}), 400

    correct_answer = questions[question_no - 1]["answer"]
    is_correct = (answer == correct_answer)

    # Prevent duplicate submission for the same phone number on the same day
    for entry in submissions:
        if entry["phone"] == phone and entry.get("date") == today_str:
            return jsonify({"status": "error", "message": "Already submitted for today"}), 409

    submission = {
        "name": name,
        "phone": phone,
        "answer": answer,
        "questionNo": question_no,
        "timeTaken": time_taken,
        "isCorrect": is_correct,
        "date": today_str
    }

    # Save to Firestore first when available, and keep a local cache
    firestore_saved = save_submission_to_firestore(submission)

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

    if FIREBASE_ENABLED and not firestore_saved:
        print("⚠️ Firestore save failed; saved submission to local JSON only.")

    return jsonify({"status": "success", "isCorrect": is_correct, "message": "Answer submitted successfully"}), 200


@app.route("/submissions")
def submissions_view():
    password = request.args.get("password")
    if not password or unquote(password).strip() != ADMIN_PASSWORD:
        return "Unauthorized", 403

    subs = load_submissions_from_firestore() if FIREBASE_ENABLED else None
    if subs is None:
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


@app.route("/reset", methods=["GET"])
def reset():
    password = request.args.get("password")
    if password != ADMIN_PASSWORD:
        return "Unauthorized", 403
    
    # Clear JSON files
    save_json_file(DATA_FILE, [])
    save_json_file(ARCHIVE_FILE, [])

    # Clear Firestore submissions if enabled
    if FIREBASE_ENABLED:
        firestore_cleared = clear_firestore_submissions()
        if not firestore_cleared:
            return jsonify({"status": "Database reset locally, but Firestore clear failed"}), 500

    return jsonify({"status": "Database reset"}), 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)), debug=False)