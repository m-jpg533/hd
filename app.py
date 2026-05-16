from flask import Flask, request, jsonify, render_template
import sqlite3
import os

app = Flask(__name__)
app.config["UPLOAD_FOLDER"] = "static/videos"

def db():
    return sqlite3.connect("videos.db")

# ===== 首頁 =====
@app.route("/")
def home():
    return render_template("index.html")

# ===== 取得影片 =====
@app.route("/api/videos")
def videos():

    conn = db()
    cur = conn.cursor()

    cur.execute("SELECT id, title, video_url, likes FROM videos")
    rows = cur.fetchall()

    data = []

    for r in rows:
        data.append({
            "id": r[0],
            "title": r[1],
            "url": r[2],
            "likes": r[3]
        })

    return jsonify(data)

# ===== 上傳影片 =====
@app.route("/api/upload", methods=["POST"])
def upload():

    file = request.files["video"]

    path = os.path.join(app.config["UPLOAD_FOLDER"], file.filename)
    file.save(path)

    conn = db()
    cur = conn.cursor()

    cur.execute(
        "INSERT INTO videos(title, video_url) VALUES (?, ?)",
        (file.filename, path)
    )

    conn.commit()

    return {"ok": True}

# ===== 按讚 =====
@app.route("/api/like/<int:id>")
def like(id):

    conn = db()
    cur = conn.cursor()

    cur.execute(
        "UPDATE videos SET likes = likes + 1 WHERE id=?",
        (id,)
    )

    conn.commit()

    return {"ok": True}

if __name__ == "__main__":
    app.run(port=5024,debug=True)
