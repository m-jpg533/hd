```python
from flask import Flask, request, jsonify, render_template
import sqlite3
import os
import uuid
import html

from werkzeug.utils import secure_filename

app = Flask(__name__)

# =========================
# 設定
# =========================

BASE_DIR = os.path.dirname(
    os.path.abspath(__file__)
)

UPLOAD_FOLDER = os.path.join(
    BASE_DIR,
    "static",
    "videos"
)

app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

app.config["MAX_CONTENT_LENGTH"] = (
    500 * 1024 * 1024
)

ALLOWED_EXTENSIONS = {
    "mp4",
    "mov",
    "webm"
}

# 建立資料夾
os.makedirs(
    app.config["UPLOAD_FOLDER"],
    exist_ok=True
)

# =========================
# DB
# =========================

DB_PATH = os.path.join(
    BASE_DIR,
    "videos.db"
)

def db():

    conn = sqlite3.connect(DB_PATH)

    return conn

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

    cur.execute("""
        CREATE TABLE IF NOT EXISTS comments (

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            video_id INTEGER,

            text TEXT

        )
    """)

    conn.commit()

    conn.close()

init_db()

# =========================
# 副檔名檢查
# =========================

def allowed_file(filename):

    return (
        "." in filename
        and
        filename.rsplit(".",1)[1].lower()
        in ALLOWED_EXTENSIONS
    )

# =========================
# 首頁
# =========================

@app.route("/")
def home():

    return render_template(
        "index.html"
    )

# =========================
# 取得影片
# =========================

@app.route("/api/videos")
def videos():

    try:

        conn = db()

        cur = conn.cursor()

        cur.execute("""
            SELECT
                id,
                title,
                video_url,
                likes
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

    except Exception as e:

        return jsonify({
            "error": str(e)
        }),500

# =========================
# 上傳影片
# =========================

@app.route(
    "/api/upload",
    methods=["POST"]
)
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

        ext = file.filename.rsplit(".",1)[1]

        filename = (
            str(uuid.uuid4())
            + "."
            + ext
        )

        filename = secure_filename(
            filename
        )

        save_path = os.path.join(
            app.config["UPLOAD_FOLDER"],
            filename
        )

        file.save(save_path)

        print("SAVE:", save_path)

        # DB只存相對路徑
        video_url = (
            "static/videos/"
            + filename
        )

        conn = db()

        cur = conn.cursor()

        cur.execute(
            """
            INSERT INTO videos
            (title, video_url)
            VALUES (?,?)
            """,
            (
                filename,
                video_url
            )
        )

        conn.commit()

        conn.close()

        return jsonify({
            "ok":True
        })

    except Exception as e:

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
# 留言
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
        VALUES (?,?)
        """,
        (
            id,
            text
        )
    )

    conn.commit()

    conn.close()

    return jsonify({
        "ok":True
    })

# =========================
# 取得留言
# =========================

@app.route("/api/comments/<int:id>")
def comments(id):

    conn = db()

    cur = conn.cursor()

    cur.execute(
        """
        SELECT text
        FROM comments
        WHERE video_id=?
        ORDER BY id DESC
        """,
        (id,)
    )

    rows = cur.fetchall()

    conn.close()

    data = []

    for r in rows:

        data.append(r[0])

    return jsonify(data)

# =========================
# 刪除影片
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

        path = row[0]

        full_path = os.path.join(
            BASE_DIR,
            path
        )

        if os.path.exists(full_path):

            os.remove(full_path)

        cur.execute(
            """
            DELETE FROM videos
            WHERE id=?
            """,
            (id,)
        )

        conn.commit()

    conn.close()

    return jsonify({
        "ok":True
    })

# =========================
# 啟動
# =========================

if __name__ == "__main__":

    app.run(
        host="0.0.0.0",
        port=5024,
        debug=True
    )
```

