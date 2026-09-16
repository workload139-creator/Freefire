from flask import Flask, render_template, request, redirect, url_for, flash
import sqlite3
import os
from datetime import datetime, timedelta

app = Flask(__name__)
app.secret_key = "change-this-secret-key"

UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

DB = "tournament.db"


def init_db():
    conn = sqlite3.connect(DB)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS submissions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            uid TEXT NOT NULL,
            history_file TEXT NOT NULL,
            video_file TEXT NOT NULL,
            submitted_at TEXT NOT NULL,
            status TEXT DEFAULT 'Pending'
        )
    """)

    conn.commit()
    conn.close()


@app.route("/")
def home():
    return render_template("index.html")


@app.route("/submit", methods=["POST"])
def submit():

    uid = request.form.get("uid", "").strip()
    history = request.files.get("history")
    video = request.files.get("video")

    if not uid:
        flash("UID required.")
        return redirect(url_for("home"))

    if not history or not video:
        flash("History screenshot and video are required.")
        return redirect(url_for("home"))

    # File extensions
    image_ext = {
        ".jpg", ".jpeg", ".png", ".webp"
    }

    video_ext = {
        ".mp4", ".mov", ".webm", ".mkv"
    }

    history_ext = os.path.splitext(history.filename)[1].lower()
    video_ext_name = os.path.splitext(video.filename)[1].lower()

    if history_ext not in image_ext:
        flash("History file must be an image.")
        return redirect(url_for("home"))

    if video_ext_name not in video_ext:
        flash("Video file format is not supported.")
        return redirect(url_for("home"))

    # Unique filenames
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")

    history_name = f"{uid}_{timestamp}_history{history_ext}"
    video_name = f"{uid}_{timestamp}_video{video_ext_name}"

    history_path = os.path.join(
        app.config["UPLOAD_FOLDER"],
        history_name
    )

    video_path = os.path.join(
        app.config["UPLOAD_FOLDER"],
        video_name
    )

    history.save(history_path)
    video.save(video_path)

    conn = sqlite3.connect(DB)

    conn.execute("""
        INSERT INTO submissions
        (uid, history_file, video_file, submitted_at, status)
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

    flash("Submission received. You cannot edit it after submission.")

    return redirect(url_for("home"))


if __name__ == "__main__":
    init_db()

    app.run(
        host="0.0.0.0",
        port=5000,
        debug=True
    )
