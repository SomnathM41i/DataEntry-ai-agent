import os, json, threading, csv, io
from datetime import datetime
from flask import Flask, render_template, request, jsonify, send_file, Response
from werkzeug.utils import secure_filename
from config.settings import load_config
from core.processor import process_file_streaming
from core.exporter import to_sql, to_csv, to_excel, to_json, DEFAULT_FIELDS

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 100 * 1024 * 1024
app.config["UPLOAD_FOLDER"] = "./input"
ALLOWED_EXTENSIONS = {"pdf", "docx", "txt"}
jobs = {}
chat_histories = {}

def allowed_file(f):
    return "." in f and f.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/fields")
def get_fields():
    """Return default field list for the structure editor."""
    return jsonify(DEFAULT_FIELDS)


@app.route("/api/upload", methods=["POST"])
def upload():
    if "file" not in request.files:
        return jsonify({"error": "No file"}), 400
    file    = request.files["file"]
    api_key = request.form.get("api_key", "").strip()
    delay   = float(request.form.get("request_delay", 2.0))
    model   = request.form.get("model", "llama-3.3-70b-versatile")

    if not file.filename:           return jsonify({"error": "No file selected"}), 400
    if not allowed_file(file.filename): return jsonify({"error": "Use PDF, DOCX, or TXT"}), 400
    if not api_key:                 return jsonify({"error": "Groq API key required"}), 400

    filename = secure_filename(file.filename)
    os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)
    filepath = os.path.join(app.config["UPLOAD_FOLDER"], filename)
    file.save(filepath)

    job_id = datetime.now().strftime("%Y%m%d%H%M%S%f")
    jobs[job_id] = {
        "status": "queued", "file": filename,
        "logs": [], "profiles": [],
        "sql_file": None, "json_file": None,
        "total_pages": 0, "processed": 0, "success": 0,
        "started_at": datetime.now().isoformat(),
        "current_model": model, "pause_reason": None,
    }
    chat_histories[job_id] = []

    config = load_config(api_key=api_key)
    config["output_dir"]    = "./output"
    config["request_delay"] = delay
    config["model"]         = model

    threading.Thread(
        target=process_file_streaming,
        args=(filepath, config, job_id, jobs),
        daemon=True
    ).start()
    return jsonify({"job_id": job_id})


@app.route("/api/status/<job_id>")
def status(job_id):
    job = jobs.get(job_id)
    if not job: return jsonify({"error": "Not found"}), 404
    return jsonify(job)


@app.route("/api/export/<job_id>", methods=["POST"])
def export(job_id):
    """
    Export profiles in requested format with optional custom structure.
    Body JSON:
      format: "sql" | "csv" | "excel" | "json"
      table:  "register"  (for SQL)
      fields: null | [str] | [{from, to}] | {out: src}
    """
    job = jobs.get(job_id)
    if not job: return jsonify({"error": "Job not found"}), 404

    profiles = job.get("profiles", [])
    if not profiles: return jsonify({"error": "No profiles extracted yet"}), 400

    data     = request.json or {}
    fmt      = data.get("format", "sql").lower()
    table    = data.get("table", "register")
    fields   = data.get("fields", None)   # custom structure
    filename = data.get("filename", "")

    base = filename or f"profiles_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    os.makedirs("./output", exist_ok=True)

    if fmt == "sql":
        content  = to_sql(profiles, table=table, fields=fields)
        path = f"./output/{base}.sql"
        with open(path, "w", encoding="utf-8") as f: f.write(content)
        return send_file(path, as_attachment=True, download_name=f"{base}.sql",
                         mimetype="text/plain")

    elif fmt == "csv":
        content = to_csv(profiles, fields=fields)
        return Response(
            content,
            mimetype="text/csv",
            headers={"Content-Disposition": f"attachment; filename={base}.csv"}
        )

    elif fmt == "excel":
        path = f"./output/{base}.xlsx"
        to_excel(profiles, fields=fields, output_path=path)
        return send_file(path, as_attachment=True, download_name=f"{base}.xlsx",
                         mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

    elif fmt == "json":
        content = to_json(profiles, fields=fields)
        return Response(
            content,
            mimetype="application/json",
            headers={"Content-Disposition": f"attachment; filename={base}.json"}
        )

    return jsonify({"error": f"Unknown format: {fmt}"}), 400


@app.route("/api/chat", methods=["POST"])
def chat():
    data    = request.json
    job_id  = data.get("job_id")
    message = data.get("message", "").strip()
    api_key = data.get("api_key", "").strip()
    if not message or not api_key:
        return jsonify({"error": "Message and API key required"}), 400

    job      = jobs.get(job_id)
    profiles = job.get("profiles", []) if job else []
    history  = chat_histories.get(job_id, [])

    profile_ctx = ""
    if profiles:
        profile_ctx = f"\n\nYou have {len(profiles)} extracted matrimonial profiles:\n"
        for i, p in enumerate(profiles[:10]):
            profile_ctx += f"\nProfile {i+1}: {json.dumps({k:v for k,v in p.items() if v}, ensure_ascii=False)}"

    system = f"""You are a helpful matrimonial data assistant.
Help users analyze profiles, find matches, summarize data, or write SQL/CSV queries.{profile_ctx}
Be concise and clear. Use markdown for tables when listing profiles."""

    messages = [{"role": "system", "content": system}]
    for h in history[-10:]:
        messages.append({"role": h["role"], "content": h["content"]})
    messages.append({"role": "user", "content": message})

    try:
        from groq import Groq
        client = Groq(api_key=api_key)
        resp   = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=messages,
            max_tokens=1024
        )
        reply = resp.choices[0].message.content
        history.append({"role": "user",      "content": message})
        history.append({"role": "assistant", "content": reply})
        chat_histories[job_id] = history
        return jsonify({"reply": reply})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    os.makedirs("./input",  exist_ok=True)
    os.makedirs("./output", exist_ok=True)
    os.makedirs("./logs",   exist_ok=True)
    print("\n🚀 Matrimony AI Agent → http://localhost:5000\n")
    app.run(debug=True, port=5000)
