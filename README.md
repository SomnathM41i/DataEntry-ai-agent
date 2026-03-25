# Matrimony AI Agent

Extracts matrimonial profiles from PDF/DOCX/TXT biodata files and generates SQL INSERT statements for MariaDB.

Supports **Marathi, Hindi, and English** biodatas. Processes every page as a separate profile.

---

## Project Structure

```
matrimony-ai-agent/
├── app.py                   # Flask web server (Web UI)
├── main.py                  # CLI entry point
├── requirements.txt
├── .env.example
│
├── core/
│   ├── reader.py            # PDF/DOCX/TXT file reading
│   ├── extractor.py         # Groq LLM extraction → JSON
│   ├── sql_generator.py     # JSON → SQL INSERT
│   ├── processor.py         # Full pipeline (web + CLI)
│   └── logger.py            # Log entry helper
│
├── config/
│   └── settings.py          # Config from .env
│
├── templates/
│   └── index.html           # Web UI
│
├── input/                   # Uploaded files stored here
├── output/                  # SQL + JSON results
└── logs/                    # Run logs
```

---

## Setup

```bash
cd matrimony-ai-agent
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# Edit .env and add your Groq API key
```

Get free key: https://console.groq.com

---

## Web UI (Recommended)

```bash
python app.py
# Open http://localhost:5000
```

Upload your file, paste your Groq API key, click **Extract Profiles**.
Watch live progress in the terminal panel. Download SQL or JSON when done.

## CLI

```bash
python main.py --file biodata.pdf --key gsk_YOUR_KEY
python main.py --file biodata.pdf --pages 1-20 --key gsk_YOUR_KEY
```

---

## Output

| File | Contents |
|------|----------|
| `output/biodata_TIMESTAMP.sql` | SQL INSERTs, one per profile |
| `output/biodata_TIMESTAMP.json` | All profiles as JSON array |
