# IP-SAKTI Sahayak

A free, bilingual (Hindi + English) AI assistant that answers questions about
**Ayurveda Intellectual Property and regulations** — patents, GI tags,
trademarks, NDCT Rules 2019, AYUSH guidelines — and **cites the exact source
document** for every answer.

Built for hackathons. Total cost: **0**. No credit card, no paid API, no server.

---

## How it works (30-second version)

```
Your question (Hindi/English)
        |
        v
[1] Question -> numbers (sentence-transformers, runs on your CPU)
        |
        v
[2] Chroma vector DB finds the 4 most relevant paragraphs
    from 20-30 official PDFs (runs as a local file, no server)
        |
        v
[3] Question + those paragraphs -> Gemini API (free tier)
    -> answer with [source filename] cited inline
```

If the internet/API fails, it automatically falls back to **Llama 3 running
fully offline** on your laptop via Ollama. Judges love that part.

---

## Tech stack (everything is free)

| Component   | What we use                          | Cost |
|-------------|--------------------------------------|------|
| LLM         | Gemini API (aistudio.google.com)     | Free |
| Offline LLM | Ollama + Llama 3 (laptop only)       | Free |
| Vector DB   | Chroma (a file on your laptop)       | Free |
| Embeddings  | sentence-transformers (local CPU)    | Free |
| Website UI  | Streamlit -> Streamlit Community Cloud | Free |

---

## Project files

| File                | What it does | When you run it |
|---------------------|--------------|-----------------|
| `ingest.py`         | Reads PDFs in `data/`, cuts them into chunks, converts to vectors, builds the `db/` knowledge base | ONCE (or whenever PDFs change) |
| `app_streamlit.py`  | The website (chat UI + RAG + citations) | Every time you use the app |
| `debug.py`          | Test tool: type a question, see which chunks Chroma retrieves | Only when something looks wrong |
| `data/`             | Folder with all the source PDFs | You create this, fill with 20-30 PDFs |
| `db/`               | The built knowledge base (auto-created by ingest.py) | Never touch |
| `requirements.txt`  | List of Python packages — REQUIRED for the cloud website | Never touch |
| `start_demo.bat`    | Windows double-click launcher (no PowerShell typing) | Demo day |
| `.streamlit/secrets.toml` | Your Gemini API key (local only — NEVER upload to GitHub) | Create once |

---

## PART A — One-time setup on your laptop (Windows PowerShell)

Open PowerShell in your project folder and run:

```powershell
# 1. Create a virtual environment (keeps packages isolated)
python -m venv venv

# 2. Activate it. If PowerShell blocks this command, run this once first:
#    Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
venv\Scripts\Activate.ps1

# 3. Install all packages (one time, ~5 min)
pip install streamlit chromadb sentence-transformers google-genai pypdf requests

# 4. Put your PDFs in a folder named  data  (create it next to the scripts)
mkdir data
```

> If `python` is not recognized on your machine, use `py` instead
> (e.g. `py -m venv venv`).

## PART B — Build the knowledge base (one time, ~10 min)

```powershell
python ingest.py
```

Wait for: `Done! Knowledge base built with N chunks.`
The `db/` folder now exists. You only re-run this if you add/remove PDFs.

## PART C — Run the app on your laptop

```powershell
streamlit run app_streamlit.py
```

It opens automatically in your browser at `http://localhost:8501`.
To stop: `Ctrl + C` in PowerShell.
Demo-day shortcut: double-click `start_demo.bat` instead — no typing.

## PART D — Get the permanent WEBSITE (one time, ~30 min)

Judges get a normal link like `https://your-app.streamlit.app`. You set this
up ONCE; after that nobody ever runs commands.

1. Create a GitHub account → New repository → name it e.g. `ipsakti-sahayak`.
2. Upload these to the repo (web upload is fine):
   - `app_streamlit.py`
   - `requirements.txt`  <-- without this the site crashes with ModuleNotFoundError
   - the whole `db/` folder (your knowledge base — do not skip)
3. Go to share.streamlit.io → Sign in **with GitHub** → **New app** →
   pick your repo → main file: `app_streamlit.py**.
4. Expand **Advanced settings** -> **Secrets**, paste exactly:
   ```toml
   GEMINI_API_KEY = "your-key-here"
   ```
   (key from aistudio.google.com -> Get API key)
5. **Deploy.** First build takes 5-10 min (downloads the embedding model).
6. Done. Share the URL.

**Website rules to remember:**
- The free site **sleeps** when unused. Open the link 2-3 minutes BEFORE your
  demo so it wakes up in time.
- The offline (Ollama) fallback does NOT exist on the website — it only works
  on your laptop. The site uses Gemini only.

## PART E — Offline fallback with Ollama (your laptop only)

1. Install Ollama from ollama.com
2. In PowerShell: `ollama pull llama3` (one-time ~4 GB download)
3. That's it. If Gemini is unreachable, `app_streamlit.py` automatically
   switches to Llama 3 — the Sources box even shows which engine answered.

---

## Troubleshooting

| Symptom | Fix |
|---|---|
| `ModuleNotFoundError: No module named 'chromadb'` (cloud) | `requirements.txt` missing from repo root / wrong name. Upload it, reboot app. |
| `SyntaxError: unterminated f-string` | File got corrupted during upload. Re-upload `app_streamlit.py` fresh from this repo. |
| `No Gemini API key found` | Local: create `.streamlit/secrets.toml`. Cloud: set the secret in app settings, then reboot. |
| Site shows "app is asleep" | Open it and wait ~1 min, or reboot from the Manage app page. |
| `'python' is not recognized` | Use `py` instead of `python`. |
| Answer cites wrong/irrelevant sources | Test with `python debug.py` — if retrieval is bad, check your PDFs are text-based (not scanned images). |
| Gemini fails after many questions | Free tier rate limit — app retries automatically; just wait 30s. |

---

## Golden rules (read before demo day)

1. **NEVER commit your API key to GitHub.** Key goes only in Streamlit's secret
   settings (cloud) or `.streamlit/secrets.toml` (local, and add it to
   `.gitignore`). A leaked key gets abused within hours.
2. **NEVER commit `.streamlit/secrets.toml`.**
3. Always commit the `db/` folder — the website is useless without it.
4. Do 3 dry runs: (a) normal online, (b) WiFi OFF (Ollama path), (c) a question
   outside your documents — it should honestly say "I don't have enough
   information."
5. Wake the website 3 minutes before presenting.

## Demo script (30 seconds)

> "This is IP-SAKTI Sahayak — ask it anything about Ayurveda IP law, in Hindi
> or English. Everything it answers comes from official documents, and it cites
> the source for every claim — no hallucination. And if the internet dies
> mid-demo, it keeps working fully offline on my laptop. Try it."
