from flask import Flask, render_template, request, redirect, session
from flask import send_file
from openpyxl import Workbook
from collections import defaultdict
import sqlite3
import os

CATEGORIES = {
    "PRESIDENT": ["Emma", "Charlotte"],
    "VICE PRESIDENT": ["James", "Chloe"],
    "SECRETARY": ["Abigail", "Ethan", "Ruby"],
    "EXECUTIVE": ["Daniel", "Lucas"]
}
app = Flask(__name__)
app.secret_key = "Election_7xK29QpLm"

ADMIN_PASSWORD = "Election2026"

@app.route("/debug-db")
def debug_db():
    import os
    return os.path.abspath("database.db")

@app.route("/debug-files")
def debug_files():
    import os
    return "<br>".join(os.listdir("."))

@app.route("/debug-count")
def debug_count():
    conn = sqlite3.connect("database.db")
    c = conn.cursor()

    c.execute("SELECT COUNT(*) FROM votes")
    count = c.fetchone()[0]

    conn.close()

    return f"Votes in DB: {count}"

# ---------- DB INIT ----------
def init_db():
    conn = sqlite3.connect("database.db")
    c = conn.cursor()

    c.execute("""
    CREATE TABLE IF NOT EXISTS votes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        key TEXT,
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

    key = request.form.get("key")

    if not key:
        return "Missing Key"

    conn = sqlite3.connect("database.db")
    c = conn.cursor()

    # 🔐 check if already voted
    c.execute("SELECT * FROM votes WHERE key=?", (key,))
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
                           key=key,
                           categories=CATEGORIES)

# ---------- VOTE SUBMISSION ----------
@app.route("/vote", methods=["POST"])
def vote():

    key = request.form.get("key")

    if not key:
        return render_template(
        "error.html",
        message="Key is required."
    )
    conn = sqlite3.connect("database.db")
    c = conn.cursor()

    # double check safety
    c.execute("SELECT * FROM votes WHERE key=?", (key,))
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
            "INSERT INTO votes (key, category, candidate) VALUES (?, ?, ?)",
            (key, category, candidate)
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
    SELECT COUNT(DISTINCT key)
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
        SELECT key,
               timestamp,
               category,
               candidate
        FROM votes
        ORDER BY id
    """)

    rows = c.fetchall()
    conn.close()

    votes = defaultdict(dict)

    for key, timestamp, category, candidate in rows:

        key = (key, timestamp)

        votes[key][category] = candidate

    wb = Workbook()
    ws = wb.active

    ws.title = "Form_Responses"

    ws.append([
        "Timestamp",
        "PRESIDENT",
        "VICE PRESIDENT",
        "SECRETARY",
        "EXECUTIVE"
    ])

    for (key, timestamp), ballot in votes.items():

        ws.append([
            timestamp,
            ballot.get("PRESIDENT", ""),
            ballot.get("VICE PRESIDENT", ""),
            ballot.get("SECRETARY", ""),
            ballot.get("EXECUTIVE", "")
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