import os, json, sqlite3, base64
from datetime import datetime
from flask import Flask, render_template, redirect
import openai

openai.api_key = os.getenv("OPENAI_API_KEY")

with open("config.json") as f:
    CONFIG = json.load(f)

app = Flask(__name__)
DB = "posts.db"
IMAGEDIR = "static/images"


def init_db():
    os.makedirs(IMAGEDIR, exist_ok=True)
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("""
      CREATE TABLE IF NOT EXISTS posts(
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          title TEXT,
          content TEXT,
          image TEXT,
          created TIMESTAMP
      )
    """)
    conn.commit(); conn.close()


def generate_image(title: str) -> str:
    """Create futuristic banner via DALL‑E 3."""
    try:
        img_resp = openai.images.generate(
            model="dall-e-3",
            prompt=f"Modern futuristic banner image for an article titled '{title}' about AI prompts and business innovation",
            size="1024x512"
        )
        img_b64 = img_resp.data[0].b64_json
        img_bytes = base64.b64decode(img_b64)
        filename = f"{datetime.utcnow().timestamp():.0f}.png"
        path = os.path.join(IMAGEDIR, filename)
        with open(path, "wb") as f:
            f.write(img_bytes)
        return filename
    except Exception as e:
        print("Image generation error:", e)
        return ""


def generate_post():
    prompt = f"""
    Write one SEO‑optimized blog article (900‑1200 words) explaining practical AI prompt use-cases for startups.
    Include 3 affiliate call‑to‑action links tagged as:
    {CONFIG['affiliate_template']}.

    Return in the following format:
    TITLE:
    <title>
    BODY:
    <body>
    """
    resp = openai.ChatCompletion.create(
        model="gpt-4o-mini",
        messages=[{"role":"user","content":prompt}],
        temperature=0.7
    )
    msg = resp.choices[0].message.content
    try:
        title = msg.split("TITLE:")[1].split("BODY:")[0].strip()
        body = msg.split("BODY:")[1].strip()
    except:
        title, body = "Untitled", msg
    image = generate_image(title)
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("INSERT INTO posts(title,content,image,created) VALUES(?,?,?,?)",
              (title, body, image, datetime.utcnow()))
    conn.commit(); conn.close()
    return title


@app.route("/")
def home():
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("SELECT id,title,created,image FROM posts ORDER BY created DESC")
    posts = c.fetchall()
    conn.close()
    return render_template("index.html", posts=posts, ads=CONFIG["adsense_slot"])


@app.route("/post/<int:pid>")
def post(pid):
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("SELECT title,content,created,image FROM posts WHERE id=?",(pid,))
    row = c.fetchone(); conn.close()
    if not row: return "Post not found",404
    title,content,created,image=row
    return render_template("post.html",title=title,content=content,
                           created=created,image=image,ads=CONFIG["adsense_slot"])


@app.route("/store")
def store():
    return render_template("store.html", ads=CONFIG["adsense_slot"])


@app.route("/generate")
def manual_generate():
    t=generate_post()
    return redirect("/")

if __name__=="__main__":
    init_db()
    app.run(host="0.0.0.0",port=5000)
