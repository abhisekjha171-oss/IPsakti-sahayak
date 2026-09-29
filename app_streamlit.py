# app_streamlit.py - IP-SAKTI Sahayak (Modern Ayurvedic Theme + self-healing KB)
# Run with:  streamlit run app_streamlit.py
import os
import time
import requests
import streamlit as st
import chromadb
from sentence_transformers import SentenceTransformer
from google import genai

st.set_page_config(
    page_title="IP-SAKTI Sahayak",
    page_icon="🌿",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ---------------- Modern Ayurvedic theme ----------------
CSS = """
@import url('https://fonts.googleapis.com/css2?family=Poppins:wght@300;400;600;700&display=swap');

html, body, [class*="css"]  { font-family: 'Poppins', sans-serif; }

.stApp {
    background: linear-gradient(135deg, #f7f4ec 0%, #eef3e6 50%, #f9f1e3 100%);
}

.hero {
    background: linear-gradient(90deg, #1b4332 0%, #2d6a4f 55%, #b07d2b 130%);
    padding: 1.4rem 2rem;
    border-radius: 16px;
    color: #ffffff;
    margin-bottom: 1.2rem;
    box-shadow: 0 4px 18px rgba(27,67,50,.25);
}
.hero h1 { margin: 0; font-size: 1.9rem; font-weight: 700; letter-spacing: .5px; }
.hero p  { margin: .3rem 0 0 0; font-weight: 300; color: #e9f5ec; font-size: .95rem; }

[data-testid="stChatMessage"] {
    background: #ffffff;
    border-radius: 14px;
    padding: .8rem 1rem;
    border-left: 4px solid #2d6a4f;
    box-shadow: 0 2px 8px rgba(27,67,50,.08);
    margin-bottom: .6rem;
}

[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #1b4332 0%, #2d6a4f 100%);
}
[data-testid="stSidebar"] * { color: #eaf4ec; }
[data-testid="stSidebar"] .stButton button {
    background: rgba(255,255,255,.10);
    color: #ffffff;
    border: 1px solid rgba(255,255,255,.35);
    border-radius: 10px;
    text-align: left;
    font-size: .85rem;
}
[data-testid="stSidebar"] .stButton button:hover {
    background: rgba(255,255,255,.22);
    border-color: #f4d58d;
}

.stButton button { border-radius: 10px; }
.stChatInputContainer { border-radius: 12px; }

details summary { font-weight: 600; color: #2d6a4f; }
"""

st.markdown("<style>" + CSS + "</style>", unsafe_allow_html=True)

st.markdown(
    '<div class="hero"><h1>🌿 IP-SAKTI Sahayak</h1>'
    "<p>Ayurveda Intellectual Property &amp; Regulatory Guidance · "
    "हिंदी + English · Every answer source-cited</p></div>",
    unsafe_allow_html=True,
)

# ---------------- cached resources ----------------
@st.cache_resource
def load_embedder():
    return SentenceTransformer("paraphrase-multilingual-MiniLM-L12-v2")

CHUNK_SIZE = 500
CHUNK_OVERLAP = 100

def _chunk_text(text):
    chunks = []
    for i in range(0, len(text), CHUNK_SIZE - CHUNK_OVERLAP):
        c = text[i:i + CHUNK_SIZE].strip()
        if len(c) > 50:
            chunks.append(c)
    return chunks

@st.cache_resource
def load_collection():
    # NOTE: no parameters allowed here - Streamlit cannot hash ML objects.
    # We call load_embedder() INSIDE, it is cached so this is free.
    emb_model = load_embedder()
    client = chromadb.PersistentClient(path="db")
    try:
        return client.get_collection("ipsakti")
    except Exception:
        pass  # not built yet -> build from data/ PDFs

    from pypdf import PdfReader

    docs, ids, metas = [], [], []
    doc_n = 0
    data_dir = "data"
    if os.path.isdir(data_dir):
        for fn in os.listdir(data_dir):
            if not fn.lower().endswith(".pdf"):
                continue
            reader = PdfReader(os.path.join(data_dir, fn))
            full = ""
            for page in reader.pages:
                t = page.extract_text()
                if t:
                    full += t + "\n"
            for j, c in enumerate(_chunk_text(full)):
                docs.append(c)
                ids.append(f"doc{doc_n}_chunk{j}")
                metas.append({"source": fn, "chunk": j})
            doc_n += 1

    if not docs:
        st.error(
            "Knowledge base not found. Upload either the db/ folder "
            "or your PDFs in a data/ folder to the repo, then Reboot."
        )
        st.stop()

    st.warning(
        "First run on this server: building the knowledge base from data/ PDFs. "
        "This can take 5-10 minutes - please don't close this tab."
    )
    emb = emb_model.encode(docs, show_progress_bar=False).tolist()
    col = client.get_or_create_collection(
        name="ipsakti", metadata={"hnsw:space": "cosine"}
    )
    col.add(documents=docs, ids=ids, metadatas=metas, embeddings=emb)
    return col

@st.cache_resource
def load_gemini():
    key = st.secrets.get("GEMINI_API_KEY", os.getenv("GEMINI_API_KEY", ""))
    if not key:
        st.error("No Gemini API key found. Add GEMINI_API_KEY in Streamlit secrets.")
        st.stop()
    return genai.Client(api_key=key)

embedder = load_embedder()
collection = load_collection()
gemini = load_gemini()

# ---------------- LLM: Gemini with retries, then Ollama offline fallback ----------------
def ask_llm(prompt: str):
    for attempt in range(3):
        try:
            r = gemini.models.generate_content(model="gemini-2.5-flash", contents=prompt)
            return r.text, "Gemini (online)"
        except Exception:
            if attempt < 2:
                time.sleep(5 * (attempt + 1))
    try:  # offline fallback - Ollama must be running: `ollama serve`
        r = requests.post(
            "http://localhost:11434/api/generate",
            json={"model": "llama3", "prompt": prompt, "stream": False},
            timeout=180,
        )
        return r.json()["response"], "Llama 3 (offline, Ollama)"
    except Exception:
        return ("Sorry, the AI service is temporarily unavailable and no offline "
                "model is running. Start Ollama or try again later."), "unavailable"

# ---------------- RAG ----------------
def answer(question: str):
    q_vec = embedder.encode([question]).tolist()
    results = collection.query(query_embeddings=q_vec, n_results=4)

    context = ""
    sources = []
    for doc, meta in zip(results["documents"][0], results["metadatas"][0]):
        context += f"[Source: {meta['source']}]\n{doc}\n\n"
        if meta["source"] not in sources:
            sources.append(meta["source"])

    prompt = f"""You are IP-SAKTI Sahayak, an assistant for Intellectual Property
and regulatory guidance in Ayurveda (Indian + international regimes).

Rules:
- Base your answer ONLY on the context below.
- Synthesize information from ALL provided chunks; combine them into one
  coherent answer. Do not mention "chunks" or "context" in your answer.
- If the context covers the topic but not the exact question asked, explain
  what the context DOES say about the topic.
- Only if the context is completely unrelated to the question, say:
  "I don't have enough information in my knowledge base."
- Always cite sources inline like [source filename].
- Answer in the SAME language as the question. Note: the context is in
  English - that's fine, translate/summarize it into the question's language.

CONTEXT:
{context}

QUESTION: {question}"""

    text, engine = ask_llm(prompt)
    return text, sources, engine

# ---------------- chat ----------------
if "messages" not in st.session_state:
    st.session_state.messages = []

def render_history():
    for m in st.session_state.messages:
        avatar = "🧑‍💼" if m["role"] == "user" else "🌿"
        with st.chat_message(m["role"], avatar=avatar):
            st.markdown(m["content"])
            if m.get("sources"):
                with st.expander("📚 Sources"):
                    for s in m["sources"]:
                        st.caption(f"• {s}")
                    st.caption(f"Engine: {m['engine']}")

def respond(q: str):
    st.session_state.messages.append({"role": "user", "content": q})
    with st.chat_message("user", avatar="🧑‍💼"):
        st.markdown(q)
    with st.chat_message("assistant", avatar="🌿"):
        with st.spinner("🔍 Searching the knowledge base..."):
            text, sources, engine = answer(q)
        st.markdown(text)
        with st.expander("📚 Sources"):
            for s in sources:
                st.caption(f"• {s}")
            st.caption(f"Engine: {engine}")
    st.session_state.messages.append(
        {"role": "assistant", "content": text, "sources": sources, "engine": engine}
    )

render_history()

# ---------------- sidebar: example questions + info ----------------
with st.sidebar:
    st.markdown("### ✨ Try an example")
    st.caption("Tap any question - perfect for demos.")
    examples = [
        "क्या आयुर्वेदिक उत्पाद को patent मिल सकता है?",
        "What is a Geographical Indication and how does it protect Ayurveda products?",
        "NDCT Rules 2019 में traditional knowledge के लिए क्या प्रावधान हैं?",
        "How can an Ayurveda startup register a trademark?",
        "Ayurveda में biopiracy से बचाव कैसे होता है?",
    ]
    for ex in examples:
        if st.button(ex, key=ex, use_container_width=True):
            respond(ex)
            st.rerun()

    st.markdown("---")
    st.markdown("#### About")
    st.markdown(
        "Answers come **only** from official documents in the knowledge base — "
        "each claim cites its source. Works in Hindi & English."
    )
    st.markdown(
        "🛡️ *Offline mode:* if the API is unreachable, the app switches to a "
        "local Llama 3 model automatically."
    )

# ---------------- main input ----------------
if q := st.chat_input("Ask about Ayurveda patents, GI tags, trademarks..."):
    respond(q)
