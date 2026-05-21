from flask import Flask, request, jsonify, render_template
import sqlite3
import os
import html
import uuid

from werkzeug.utils import secure_filename

app = Flask(__name__)

# =========================
# 設定
# =========================

app.config["MAX_CONTENT_LENGTH"] = 500 * 1024 * 1024

UPLOAD_FOLDER = "static/videos"

app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

ALLOWED_EXTENSIONS = {
    "mp4",
    "mov",
    "webm"
}

# 建立資料夾
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

# =========================
# DB
# =========================

BASE_DIR = os.path.dirname(
    os.path.abspath(__file__)
)

DB_PATH = os.path.join(
    BASE_DIR,
    "videos.db"
)

def db():

    return sqlite3.connect(DB_PATH)

# =========================
# 初始化 DB
# =========================

def init_db():

    conn = db()

    cur = conn.cursor()

    cur.execute("""
    CREATE TABLE IF NOT EXISTS videos (

        id INTEGER PRIMARY KEY AUTOINCREMENT,

        title TEXT,

        video_url TEXT,

        likes INTEGER DEFAULT 0

    )
    """)

    conn.commit()

    conn.close()

init_db()

# =========================
# 檢查副檔名
# =========================

def allowed_file(filename):

    return "." in filename and \
    filename.rsplit(".",1)[1].lower() \
    in ALLOWED_EXTENSIONS

# =========================
# 首頁
# =========================

@app.route("/")
def home():

    return render_template("index.html")

# =========================
# API 影片
# =========================

@app.route("/api/videos")
def videos():

    conn = db()

    cur = conn.cursor()

    cur.execute("""
    SELECT id,title,video_url,likes
    FROM videos
    ORDER BY id DESC
    """)

    rows = cur.fetchall()

    conn.close()

    data = []

    for r in rows:

        data.append({

            "id": r[0],

            "title": r[1],

            "url": "/" + r[2],

            "likes": r[3]

        })

    return jsonify(data)

# =========================
# 上傳影片
# =========================
@app.route("/api/upload", methods=["POST"])
def upload():

    try:

        if "video" not in request.files:

            return jsonify({
                "error":"沒有影片"
            }),400

        file = request.files["video"]

        if file.filename == "":

            return jsonify({
                "error":"沒有選擇檔案"
            }),400

        if not allowed_file(file.filename):

            return jsonify({
                "error":"只允許 mp4/mov/webm"
            }),400

        # 安全檔名
        ext = file.filename.rsplit(".",1)[1]

        filename = (
            str(uuid.uuid4())
            + "."
            + ext
        )

        filename = secure_filename(filename)

        path = os.path.join(
            app.config["UPLOAD_FOLDER"],
            filename
        )

       

        # DB
        conn = db()

        cur = conn.cursor()

        cur.execute(
            """
            INSERT INTO videos
            (title,video_url)
            VALUES (?,?)
            """,
            (
                filename,
                path
            )
        )

        conn.commit()

        conn.close()

        return jsonify({
            "ok":True
        })

    except Exception as e:

        print(e)

        return jsonify({
            "error":str(e)
        }),500

# =========================
# 按讚
# =========================

@app.route("/api/like/<int:id>")
def like(id):

    conn = db()

    cur = conn.cursor()

    cur.execute(
        """
        UPDATE videos
        SET likes = likes + 1
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

    return jsonify({
        "likes":likes
    })

# =========================
# 啟動
# =========================

if __name__ == "__main__":

    app.run(
        host="0.0.0.0",
        port=5024,
        debug=False
    )
