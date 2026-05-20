
from flask import Flask
from flask import request
from flask import jsonify
from flask import render_template

import sqlite3
import os
import html

from datetime import datetime

from werkzeug.utils import secure_filename

# =========================
# Flask
# =========================
app = Flask(__name__)

# =========================
# Upload
# =========================
UPLOAD_FOLDER = "static/videos"
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER


# =========================
# 副檔名
# =========================
ALLOWED_EXTENSIONS = {
    "mp4",
    "mov",
    "webm"
}

# =========================
# 攻擊字串
# =========================
BAD_WORDS = [

    "<script>",

    "or 1=1",

    "union select",

    "../",

    "drop table",

    "javascript:",

    "onerror="
]

# =========================
# DB
# =========================
def db():

    conn = sqlite3.connect(
        "videos.db"
    )

    conn.row_factory = sqlite3.Row

    return conn

# =========================
# 初始化 DB
# =========================
def init_db():

    conn = db()

    cur = conn.cursor()

    # ===== videos =====
    cur.execute("""

    CREATE TABLE IF NOT EXISTS videos(

        id INTEGER PRIMARY KEY AUTOINCREMENT,

        title TEXT,

        video_url TEXT,

        likes INTEGER DEFAULT 0

    )

    """)

    # ===== comments =====
    cur.execute("""

    CREATE TABLE IF NOT EXISTS comments(

        id INTEGER PRIMARY KEY AUTOINCREMENT,

        video_id INTEGER,

        text TEXT

    )

    """)

    # ===== logs =====
    cur.execute("""

    CREATE TABLE IF NOT EXISTS logs(

        id INTEGER PRIMARY KEY AUTOINCREMENT,

        ip TEXT,

        path TEXT,

        attack TEXT,

        time TEXT

    )

    """)

    conn.commit()

    conn.close()

init_db()

# =========================
# 副檔名檢查
# =========================
def allowed_file(filename):

    return "." in filename and \
    filename.rsplit(".",1)[1].lower() \
    in ALLOWED_EXTENSIONS

# =========================
# Security Monitor
# =========================
@app.before_request
def security_monitor():

    ip = request.remote_addr

    path = request.full_path.lower()

    attack = ""

    # ===== 不記錄 dashboard API =====
    if path.startswith("/api/security"):
        return

    if path.startswith("/api/logs"):
        return

    # ===== 攻擊檢查 =====
    for b in BAD_WORDS:

        if b in path:

            attack = b

            conn = db()

            cur = conn.cursor()

            cur.execute(
                """
                INSERT INTO logs
                (ip,path,attack,time)

                VALUES(?,?,?,?)
                """,
                (
                    ip,
                    path,
                    attack,
                    str(datetime.now())
                )
            )

            conn.commit()

            conn.close()

            return {
                "error":"blocked"
            },403

    # ===== 正常流量 =====
    conn = db()

    cur = conn.cursor()

    cur.execute(
        """
        INSERT INTO logs
        (ip,path,attack,time)

        VALUES(?,?,?,?)
        """,
        (
            ip,
            path,
            attack,
            str(datetime.now())
        )
    )

    conn.commit()

    conn.close()

# =========================
# 首頁
# =========================
@app.route("/")
def home():

    return render_template(
        "index.html"
    )

# =========================
# Dashboard
# =========================
@app.route("/dashboard")
def dashboard():

    return render_template(
        "dashboard.html"
    )

# =========================
# Videos API
# =========================
@app.route("/api/videos")
def videos():

    conn = db()

    cur = conn.cursor()

    cur.execute(
        """
        SELECT *
        FROM videos
        ORDER BY id DESC
        """
    )

    rows = cur.fetchall()

    conn.close()

    data = []

    for r in rows:

        data.append({

            "id":r["id"],

            "title":r["title"],

            "url":"/"+r["video_url"],

            "likes":r["likes"]

        })

    return jsonify(data)

# =========================
# Upload API
# =========================
@app.route(
    "/api/upload",
    methods=["POST"]
)
def upload():

    if "video" not in request.files:

        return {
            "error":"沒有檔案"
        }

    file = request.files["video"]

    if file.filename == "":

        return {
            "error":"空檔案"
        }

    # ===== 副檔名 =====
    if not allowed_file(
        file.filename
    ):

        return {
            "error":"只允許 mp4/mov/webm"
        }

    # ===== 安全檔名 =====
    filename = secure_filename(
        file.filename
    )

    path = os.path.join(
        UPLOAD_FOLDER,
        filename
    )

    file.save(path)

    conn = db()

    cur = conn.cursor()

    cur.execute(
        """
        INSERT INTO videos
        (title,video_url)

        VALUES(?,?)
        """,
        (
            filename,
            path
        )
    )

    conn.commit()

    conn.close()

    return {
        "ok":True
    }

# =========================
# Like API
# =========================
@app.route("/api/like/<int:id>")
def like(id):

    conn = db()

    cur = conn.cursor()

    cur.execute(
        """
        UPDATE videos
        SET likes=likes+1
        WHERE id=?
        """,
        (id,)
    )

    conn.commit()

    cur.execute(
        """
        SELECT likes
        FROM videos
        WHERE id=?
        """,
        (id,)
    )

    likes = cur.fetchone()[0]

    conn.close()

    return {
        "likes":likes
    }

# =========================
# Comment API
# =========================
@app.route(
    "/api/comment/<int:id>",
    methods=["POST"]
)
def comment(id):

    text = html.escape(
        request.json["text"]
    )

    conn = db()

    cur = conn.cursor()

    cur.execute(
        """
        INSERT INTO comments
        (video_id,text)

        VALUES(?,?)
        """,
        (
            id,
            text
        )
    )

    conn.commit()

    conn.close()

    return {
        "ok":True
    }

# =========================
# Security API
# =========================
@app.route("/api/security")
def security():

    conn = db()

    cur = conn.cursor()

    # ===== 總流量 =====
    cur.execute(
        "SELECT COUNT(*) FROM logs"
    )

    total = cur.fetchone()[0]

    # ===== 攻擊數 =====
    cur.execute(
        """
        SELECT COUNT(*)
        FROM logs
        WHERE attack!=''
        """
    )

    attacks = cur.fetchone()[0]

    # ===== XSS =====
    cur.execute(
        """
        SELECT COUNT(*)
        FROM logs
        WHERE path LIKE '%script%'
        """
    )

    xss = cur.fetchone()[0]

    # ===== SQLi =====
    cur.execute(
        """
        SELECT COUNT(*)
        FROM logs
        WHERE path LIKE '%or 1=1%'
        """
    )

    sqli = cur.fetchone()[0]

    conn.close()

    return jsonify({

        "total":total,

        "attacks":attacks,

        "xss":xss,

        "sqli":sqli

    })

# =========================
# Logs API
# =========================
@app.route("/api/logs")
def logs():

    conn = db()

    cur = conn.cursor()

    cur.execute(
        """
        SELECT *
        FROM logs
        ORDER BY id DESC
        LIMIT 20
        """
    )

    rows = cur.fetchall()

    conn.close()

    data = []

    for r in rows:

        data.append({

            "ip":r["ip"],

            "path":r["path"],

            "attack":r["attack"],

            "time":r["time"]

        })

    return jsonify(data)

# =========================
# Delete Video
# =========================
@app.route("/api/delete/<int:id>")
def delete(id):

    conn = db()

    cur = conn.cursor()

    cur.execute(
        """
        SELECT video_url
        FROM videos
        WHERE id=?
        """,
        (id,)
    )

    row = cur.fetchone()

    if row:

        path = row["video_url"]

        if os.path.exists(path):

            os.remove(path)

        cur.execute(
            """
            DELETE FROM videos
            WHERE id=?
            """,
            (id,)
        )

        conn.commit()

    conn.close()

    return {
        "ok":True
    }

# =========================
# Run
# =========================
if __name__ == "__main__":

    app.run(
        host="0.0.0.0",
        port=5024,
        debug=False
    )
