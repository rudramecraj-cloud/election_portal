from flask import Flask, render_template, request, redirect, session
from flask import send_file
from openpyxl import Workbook
from collections import defaultdict
import sqlite3

CATEGORIES = {
    "HEAD BOY": ["Aditya Biju", "Shravan Sonu Joseph"],
    "HEAD GIRL": ["Adithi P Dinesh", "Ann Mary Leo"],
    "DISCIPLINE MINISTER": ["Abigail Libeesh", "Milan Paul", "Theertha Danesh"],
    "SPORTS CAPTAIN": ["Arya Nanda K.R", "Ann Rachel"]
}
app = Flask(__name__)
app.secret_key = "SBOA_2026_Election_7xK29QpLm"

ADMIN_PASSWORD = "SBOA@Election2026"
# ---------- DB INIT ----------
def init_db():
    conn = sqlite3.connect("database.db")
    c = conn.cursor()

    c.execute("""
    CREATE TABLE IF NOT EXISTS votes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        admission_no TEXT,
        category TEXT,
        candidate TEXT,
        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
)
""")

    conn.commit()
    conn.close()

init_db()

# ---------- HOME ----------
@app.route("/")
def landing():
    return render_template("landing.html")

@app.route("/begin")
def begin():
    return redirect("/voting")

@app.route("/admin", methods=["GET", "POST"])
def admin():

    if request.method == "POST":

        password = request.form.get("password")

        if password == ADMIN_PASSWORD:
            session["admin"] = True
            return redirect("/results")

        return render_template(
            "error.html",
            message="Incorrect admin password."
        )

    return render_template("admin_login.html")

# ---------- START FLOW ----------
@app.route("/start", methods=["POST"])
def start():

    admission_no = request.form.get("admission_no")

    if not admission_no:
        return "Missing Admission Number"

    conn = sqlite3.connect("database.db")
    c = conn.cursor()

    # 🔐 check if already voted
    c.execute("SELECT * FROM votes WHERE admission_no=?", (admission_no,))
    existing = c.fetchone()

    if existing:
        conn.close()
        return render_template(
            "error.html",
            message="You have already voted."
        )
    conn.close()

    # allow voting
    return render_template("ballot.html",
                           admission_no=admission_no,
                           categories=CATEGORIES)

# ---------- VOTE SUBMISSION ----------
@app.route("/vote", methods=["POST"])
def vote():

    admission_no = request.form.get("admission_no")

    if not admission_no:
        return render_template(
        "error.html",
        message="Admission number is required."
    )
    conn = sqlite3.connect("database.db")
    c = conn.cursor()

    # double check safety
    c.execute("SELECT * FROM votes WHERE admission_no=?", (admission_no,))
    if c.fetchone():
        conn.close()
        return render_template(
            "error.html",
            message="You have already voted."
        )

    for category in CATEGORIES.keys():
        candidate = request.form.get(category)

        if not candidate:
            conn.close()
            return f"Missing vote for {category}"

        c.execute(
            "INSERT INTO votes (admission_no, category, candidate) VALUES (?, ?, ?)",
            (admission_no, category, candidate)
        )

    conn.commit()
    conn.close()

    return render_template("success.html")

@app.route("/voting")
def voting():
    return render_template("index.html")

@app.route("/reset-election")
def reset_election():

    if not session.get("admin"):
        return "Unauthorized"

    conn = sqlite3.connect("database.db")
    c = conn.cursor()

    c.execute("DELETE FROM votes")

    conn.commit()
    conn.close()

    return "Election reset successfully"

# ---------- RESULTS ----------
@app.route("/results")
def results():

    if not session.get("admin"):
        return render_template(
            "error.html",
            message="Admin login required."
        )

    conn = sqlite3.connect("database.db")
    c = conn.cursor()

    results = {}
    leaders = {}
    category_totals = {}

    for category in CATEGORIES.keys():

        c.execute("""
        SELECT candidate, COUNT(*)
        FROM votes
        WHERE category=?
        GROUP BY candidate
        ORDER BY COUNT(*) DESC
        """, (category,))

        data = c.fetchall()

        results[category] = data

        category_totals[category] = sum(
            votes for _, votes in data
        )

        leaders[category] = []

        if data:

            highest_votes = data[0][1]

            for candidate, votes in data:

                if votes == highest_votes:

                    leaders[category].append(candidate)

    # Total number of students who voted
    c.execute("""
    SELECT COUNT(DISTINCT admission_no)
    FROM votes
    """)

    total_voters = c.fetchone()[0]

    conn.close()

    return render_template(
        "result.html",
        results=results,
        leaders=leaders,
        category_totals=category_totals,
        total_voters=total_voters
    )

@app.route("/download-results")
def download_results():

    if not session.get("admin"):
        return render_template(
            "error.html",
            message="Admin login required."
        )

    conn = sqlite3.connect("database.db")
    c = conn.cursor()

    c.execute("""
        SELECT admission_no,
               timestamp,
               category,
               candidate
        FROM votes
        ORDER BY id
    """)

    rows = c.fetchall()
    conn.close()

    votes = defaultdict(dict)

    for admission_no, timestamp, category, candidate in rows:

        key = (admission_no, timestamp)

        votes[key][category] = candidate

    wb = Workbook()
    ws = wb.active

    ws.title = "Form_Responses"

    ws.append([
        "Timestamp",
        "HEAD BOY",
        "HEAD GIRL",
        "DISCIPLINE MINISTER",
        "SPORTS CAPTAIN"
    ])

    for (admission_no, timestamp), ballot in votes.items():

        ws.append([
            timestamp,
            ballot.get("HEAD BOY", ""),
            ballot.get("HEAD GIRL", ""),
            ballot.get("DISCIPLINE MINISTER", ""),
            ballot.get("SPORTS CAPTAIN", "")
        ])

    filename = "Election_Results.xlsx"

    wb.save(filename)

    return send_file(
        filename,
        as_attachment=True
    )

@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")

if __name__ == "__main__":
    app.run()