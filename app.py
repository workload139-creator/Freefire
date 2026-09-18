from flask import (
    Flask, render_template, request,
    redirect, url_for, session, flash,
    send_from_directory
)

import sqlite3
import os
from datetime import datetime
from werkzeug.utils import secure_filename


app = Flask(__name__)


# =========================
# APP SETTINGS
# =========================

app.secret_key = "FF_TOURNAMENT_CHANGE_THIS_SECRET"

DB = "tournament.db"

UPLOAD_FOLDER = "uploads"

os.makedirs(UPLOAD_FOLDER, exist_ok=True)

app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

# Maximum total upload size = 50 MB
app.config["MAX_CONTENT_LENGTH"] = 50 * 1024 * 1024


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

            qr_file TEXT,

            submitted_at TEXT NOT NULL,

            status TEXT DEFAULT 'Pending',

            kills INTEGER DEFAULT 0,

            position INTEGER DEFAULT 0,

            verified_at TEXT

        )
    """)

    # ---------------------------------
    # Old database me QR column add karo
    # ---------------------------------

    columns = conn.execute(
        "PRAGMA table_info(submissions)"
    ).fetchall()

    column_names = [
        column["name"]
        for column in columns
    ]

    if "qr_file" not in column_names:

        conn.execute("""
            ALTER TABLE submissions
            ADD COLUMN qr_file TEXT
        """)

    conn.commit()

    conn.close()


init_db()


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

    uid = request.form.get(
        "uid",
        ""
    ).strip()

    history = request.files.get(
        "history"
    )

    video = request.files.get(
        "video"
    )

    qr = request.files.get(
        "qr"
    )


    # =========================
    # UID CHECK
    # =========================

    if not uid:

        flash(
            "Free Fire UID is required."
        )

        return redirect(
            url_for("home")
        )


    # =========================
    # FILE CHECK
    # =========================

    if not history or not video or not qr:

        flash(
            "Game History, Match Video and Payment QR are required."
        )

        return redirect(
            url_for("home")
        )


    if (
        not history.filename
        or not video.filename
        or not qr.filename
    ):

        flash(
            "Please select all required files."
        )

        return redirect(
            url_for("home")
        )


    # =========================
    # ALLOWED EXTENSIONS
    # =========================

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


    qr_ext = os.path.splitext(
        qr.filename
    )[1].lower()


    # =========================
    # HISTORY VALIDATION
    # =========================

    if history_ext not in image_extensions:

        flash(
            "Invalid Game History image format."
        )

        return redirect(
            url_for("home")
        )


    # =========================
    # VIDEO VALIDATION
    # =========================

    if video_ext not in video_extensions:

        flash(
            "Invalid video format. Use MP4, MOV or WEBM."
        )

        return redirect(
            url_for("home")
        )


    # =========================
    # QR VALIDATION
    # =========================

    if qr_ext not in image_extensions:

        flash(
            "Invalid Payment QR image format."
        )

        return redirect(
            url_for("home")
        )


    # =========================
    # SECURE UID
    # =========================

    safe_uid = secure_filename(uid)


    if not safe_uid:

        flash(
            "Invalid UID."
        )

        return redirect(
            url_for("home")
        )


    # =========================
    # UNIQUE FILE NAME
    # =========================

    timestamp = datetime.now().strftime(
        "%Y%m%d%H%M%S%f"
    )


    history_name = (
        f"{safe_uid}_{timestamp}_history"
        f"{history_ext}"
    )


    video_name = (
        f"{safe_uid}_{timestamp}_video"
        f"{video_ext}"
    )


    qr_name = (
        f"{safe_uid}_{timestamp}_qr"
        f"{qr_ext}"
    )


    history_path = os.path.join(
        UPLOAD_FOLDER,
        history_name
    )


    video_path = os.path.join(
        UPLOAD_FOLDER,
        video_name
    )


    qr_path = os.path.join(
        UPLOAD_FOLDER,
        qr_name
    )


    try:

        # =========================
        # SAVE FILES
        # =========================

        history.save(
            history_path
        )

        video.save(
            video_path
        )

        qr.save(
            qr_path
        )


        # =========================
        # DATABASE
        # =========================

        conn = get_db()


        conn.execute("""
            INSERT INTO submissions
            (
                uid,
                history_file,
                video_file,
                qr_file,
                submitted_at,
                status,
                kills,
                position
            )

            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (

            uid,

            history_name,

            video_name,

            qr_name,

            datetime.now().isoformat(),

            "Pending",

            0,

            0

        ))


        conn.commit()

        conn.close()


        flash(
            "✅ Submission received successfully. "
            "UID, History, Video and QR are now locked."
        )


    except Exception as e:

        # =========================
        # CLEANUP
        # =========================

        if os.path.exists(history_path):

            os.remove(history_path)


        if os.path.exists(video_path):

            os.remove(video_path)


        if os.path.exists(qr_path):

            os.remove(qr_path)


        print(
            "SUBMISSION ERROR:",
            repr(e)
        )


        flash(
            "Submission failed. Please try again."
        )


    return redirect(
        url_for("home")
    )


# =========================
# FILE TOO LARGE
# =========================

@app.errorhandler(413)
def file_too_large(error):

    flash(
        "❌ Total upload size is too large. Maximum is 50 MB."
    )

    return redirect(
        url_for("home")
    )


# =========================
# ADMIN LOGIN
# =========================

ADMIN_USERNAME = "FFTournament_Admin"

ADMIN_PASSWORD = "CHANGE_THIS_PASSWORD"


@app.route(
    "/admin/login",
    methods=["GET", "POST"]
)
def admin_login():

    if request.method == "POST":

        username = request.form.get(
            "username",
            ""
        ).strip()

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


        flash(
            "Invalid admin login."
        )


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
def verify_submission(
    submission_id
):

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


    # =========================
    # NUMBER VALIDATION
    # =========================

    try:

        kills = int(kills)

        position = int(position)

    except ValueError:

        flash(
            "Kills and position must be numbers."
        )

        return redirect(
            url_for("admin_panel")
        )


    # =========================
    # RANGE VALIDATION
    # =========================

    if kills < 0:

        flash(
            "Kills cannot be negative."
        )

        return redirect(
            url_for("admin_panel")
        )


    if kills > 99:

        flash(
            "Invalid kills value."
        )

        return redirect(
            url_for("admin_panel")
        )


    if position < 1:

        flash(
            "Position must be at least 1."
        )

        return redirect(
            url_for("admin_panel")
        )


    if position > 100:

        flash(
            "Invalid position."
        )

        return redirect(
            url_for("admin_panel")
        )


    # =========================
    # REWARD
    # =========================

    reward = kills * 5


    print(
        f"VERIFY | Submission: {submission_id} "
        f"| Kills: {kills} "
        f"| Position: {position} "
        f"| Reward: ₹{reward}"
    )


    # =========================
    # LOCK RESULT
    # =========================

    conn = get_db()


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


    # =========================
    # RESULT
    # =========================

    if cursor.rowcount == 1:

        flash(
            f"✅ Result verified and locked. "
            f"Reward: ₹{reward}"
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
def reject_submission(
    submission_id
):

    if not session.get("admin"):

        return redirect(
            url_for("admin_login")
        )


    conn = get_db()


    cursor = conn.execute("""
        UPDATE submissions

        SET
            status = 'Rejected',
            verified_at = ?

        WHERE
            id = ?
            AND status = 'Pending'
    """, (

        datetime.now().isoformat(),

        submission_id

    ))


    conn.commit()

    conn.close()


    if cursor.rowcount == 1:

        flash(
            "❌ Submission rejected."
        )

    else:

        flash(
            "This submission is already locked "
            "or does not exist."
        )


    return redirect(
        url_for("admin_panel")
    )


# =========================
# FILE VIEW
# =========================

@app.route(
    "/uploads/<filename>"
)
def uploaded_file(filename):

    # Only logged-in Admin
    # can view player files.

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
        "leaderboard.html",
        players=players
    )


# =========================
# LOGOUT
# =========================

@app.route(
    "/admin/logout"
)
def admin_logout():

    session.pop(
        "admin",
        None
    )

    return redirect(
        url_for("admin_login")
    )


# =========================
# START SERVER
# =========================

if __name__ == "__main__":

    app.run(

        host="0.0.0.0",

        port=5000,

        debug=True

    )
