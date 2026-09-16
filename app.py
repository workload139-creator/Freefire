from flask import (
    Flask, render_template, request,
    redirect, url_for, session, flash,
    send_from_directory
)
import sqlite3
import os
from datetime import datetime

app = Flask(__name__)

# CHANGE THIS
app.secret_key = "FF_TOURNAMENT_CHANGE_THIS_SECRET"

DB = "tournament.db"
UPLOAD_FOLDER = "uploads"

os.makedirs(UPLOAD_FOLDER, exist_ok=True)

app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER


# =========================
# DATABASE
# =========================

def get_db():
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():

    conn = get_db()

    conn.execute("""
        CREATE TABLE IF NOT EXISTS submissions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            uid TEXT NOT NULL,
            history_file TEXT NOT NULL,
            video_file TEXT NOT NULL,
            submitted_at TEXT NOT NULL,
            status TEXT DEFAULT 'Pending',
            kills INTEGER DEFAULT 0,
            position INTEGER DEFAULT 0,
            verified_at TEXT
        )
    """)

    conn.commit()
    conn.close()


# =========================
# HOME
# =========================

@app.route("/")
def home():
    return render_template("index.html")


# =========================
# PLAYER SUBMISSION
# =========================

@app.route("/submit", methods=["POST"])
def submit():

    uid = request.form.get("uid", "").strip()

    history = request.files.get("history")
    video = request.files.get("video")

    if not uid:
        flash("UID is required.")
        return redirect(url_for("home"))

    if not history or not video:
        flash("History screenshot and video are required.")
        return redirect(url_for("home"))

    image_extensions = {
        ".jpg",
        ".jpeg",
        ".png",
        ".webp"
    }

    video_extensions = {
        ".mp4",
        ".mov",
        ".webm"
    }

    history_ext = os.path.splitext(
        history.filename
    )[1].lower()

    video_ext = os.path.splitext(
        video.filename
    )[1].lower()

    if history_ext not in image_extensions:

        flash("Invalid history image.")
        return redirect(url_for("home"))

    if video_ext not in video_extensions:

        flash("Invalid video format.")
        return redirect(url_for("home"))

    timestamp = datetime.now().strftime(
        "%Y%m%d%H%M%S%f"
    )

    history_name = (
        f"{uid}_{timestamp}_history"
        f"{history_ext}"
    )

    video_name = (
        f"{uid}_{timestamp}_video"
        f"{video_ext}"
    )

    history_path = os.path.join(
        UPLOAD_FOLDER,
        history_name
    )

    video_path = os.path.join(
        UPLOAD_FOLDER,
        video_name
    )

    history.save(history_path)
    video.save(video_path)

    conn = get_db()

    conn.execute("""
        INSERT INTO submissions
        (
            uid,
            history_file,
            video_file,
            submitted_at,
            status
        )
        VALUES (?, ?, ?, ?, ?)
    """, (
        uid,
        history_name,
        video_name,
        datetime.now().isoformat(),
        "Pending"
    ))

    conn.commit()
    conn.close()

    flash(
        "Submission received. "
        "You cannot edit it after submission."
    )

    return redirect(url_for("home"))


# =========================
# ADMIN LOGIN
# =========================

ADMIN_USERNAME = "FFTournament_Admin"

# CHANGE THIS PASSWORD
ADMIN_PASSWORD = "CHANGE_THIS_PASSWORD"


@app.route("/admin/login", methods=["GET", "POST"])
def admin_login():

    if request.method == "POST":

        username = request.form.get(
            "username",
            ""
        )

        password = request.form.get(
            "password",
            ""
        )

        if (
            username == ADMIN_USERNAME
            and password == ADMIN_PASSWORD
        ):

            session["admin"] = True

            return redirect(
                url_for("admin_panel")
            )

        flash("Invalid admin login.")

    return render_template(
        "admin_login.html"
    )


# =========================
# ADMIN PANEL
# =========================

@app.route("/admin")
def admin_panel():

    if not session.get("admin"):
        return redirect(
            url_for("admin_login")
        )

    conn = get_db()

    submissions = conn.execute("""
        SELECT *
        FROM submissions
        ORDER BY id DESC
    """).fetchall()

    conn.close()

    return render_template(
        "admin.html",
        submissions=submissions
    )


# =========================
# VERIFY RESULT
# =========================

@app.route(
    "/admin/verify/<int:submission_id>",
    methods=["POST"]
)
def verify_submission(submission_id):

    if not session.get("admin"):
        return redirect(
            url_for("admin_login")
        )

    kills = request.form.get(
        "kills",
        "0"
    )

    position = request.form.get(
        "position",
        "0"
    )

    try:
        kills = int(kills)
        position = int(position)

    except ValueError:

        flash("Kills and position must be numbers.")

        return redirect(
            url_for("admin_panel")
        )

    if kills < 0:
        kills = 0

    if position < 0:
        position = 0

    conn = get_db()

    # Only Pending records can be verified.
    cursor = conn.execute("""
        UPDATE submissions

        SET
            kills = ?,
            position = ?,
            status = 'Verified',
            verified_at = ?

        WHERE
            id = ?
            AND status = 'Pending'
    """, (
        kills,
        position,
        datetime.now().isoformat(),
        submission_id
    ))

    conn.commit()
    conn.close()

    if cursor.rowcount == 1:

        flash(
            "Result verified and locked."
        )

    else:

        flash(
            "This result is already locked "
            "or does not exist."
        )

    return redirect(
        url_for("admin_panel")
    )


# =========================
# REJECT
# =========================

@app.route(
    "/admin/reject/<int:submission_id>",
    methods=["POST"]
)
def reject_submission(submission_id):

    if not session.get("admin"):
        return redirect(
            url_for("admin_login")
        )

    conn = get_db()

    conn.execute("""
        UPDATE submissions

        SET status = 'Rejected'

        WHERE
            id = ?
            AND status = 'Pending'
    """, (submission_id,))

    conn.commit()
    conn.close()

    flash("Submission rejected.")

    return redirect(
        url_for("admin_panel")
    )


# =========================
# FILE VIEW
# =========================

@app.route("/uploads/<filename>")
def uploaded_file(filename):

    if not session.get("admin"):
        return "Unauthorized", 403

    return send_from_directory(
        UPLOAD_FOLDER,
        filename
    )


# =========================
# LEADERBOARD
# =========================

@app.route("/leaderboard")
def leaderboard():

    conn = get_db()

    players = conn.execute("""
        SELECT
            uid,
            SUM(kills) AS total_kills,
            COUNT(*) AS matches
        FROM submissions
        WHERE status = 'Verified'
        GROUP BY uid
        ORDER BY total_kills DESC
    """).fetchall()

    conn.close()

    return render_template(
        "admin.html",
        submissions=[],
        players=players
    )


# =========================
# LOGOUT
# =========================

@app.route("/admin/logout")
def admin_logout():

    session.pop("admin", None)

    return redirect(
        url_for("admin_login")
    )


# =========================
# START
# =========================

if __name__ == "__main__":

    init_db()

    app.run(
        host="0.0.0.0",
        port=5000,
        debug=True
    )
