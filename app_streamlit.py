# app_streamlit.py — IP-SAKTI Sahayak (Streamlit UI)
# Run with:  streamlit run app_streamlit.py
import os
import time
import requests
import streamlit as st
import chromadb
from sentence_transformers import SentenceTransformer
from google import genai

st.set_page_config(page_title="IP-SAKTI Sahayak", page_icon="🌿")

# ---------- cached resources (load once, reuse on every rerun) ----------
@st.cache_resource
def load_embedder():
    return SentenceTransformer("paraphrase-multilingual-MiniLM-L12-v2")

@st.cache_resource
def load_collection():
    client = chromadb.PersistentClient(path="db")
    return client.get_collection("ipsakti")

@st.cache_resource
def load_gemini():
    key = st.secrets.get("GEMINI_API_KEY", os.getenv("GEMINI_API_KEY", ""))
    if not key:
        st.error("No Gemini API key found. Add it to .streamlit/secrets.toml")
        st.stop()
    return genai.Client(api_key=key)

embedder = load_embedder()
collection = load_collection()
gemini = load_gemini()

# ---------- LLM: Gemini with retries, then Ollama offline fallback ----------
def ask_llm(prompt: str) -> tuple[str, str]:
    for attempt in range(3):
        try:
            r = gemini.models.generate_content(model="gemini-2.5-flash", contents=prompt)
            return r.text, "Gemini (online)"
        except Exception:
            if attempt < 2:
                time.sleep(5 * (attempt + 1))
    try:  # offline fallback — Ollama must be running: `ollama serve`
        r = requests.post(
            "http://localhost:11434/api/generate",
            json={"model": "llama3", "prompt": prompt, "stream": False},
            timeout=180,
        )
        return r.json()["response"], "Llama 3 (offline, Ollama)"
    except Exception:
        return ("Sorry, the AI service is temporarily unavailable and no offline "
                "model is running. Start Ollama or try again later."), "unavailable"

# ---------- RAG ----------
def answer(question: str) -> tuple[str, list[str], str]:
    q_vec = embedder.encode([question]).tolist()
    results = collection.query(query_embeddings=q_vec, n_results=4)

    context = ""
    sources = []
    for doc, meta in zip(results["documents"][0], results["metadatas"][0]):
        context += f"[Source: {meta['source']}]
{doc}

"
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
  English — that's fine, translate/summarize it into the question's language.

CONTEXT:
{context}

QUESTION: {question}"""

    text, engine = ask_llm(prompt)
    return text, sources, engine

# ---------- Streamlit UI ----------
st.title("🌿 IP-SAKTI Sahayak")
st.caption("Ayurveda Intellectual Property & regulatory guidance · Hindi + English · source-cited")

if "messages" not in st.session_state:
    st.session_state.messages = []

for m in st.session_state.messages:
    with st.chat_message(m["role"]):
        st.markdown(m["content"])
        if m.get("sources"):
            with st.expander("📚 Sources"):
                for s in m["sources"]:
                    st.caption(f"• {s}")
                st.caption(f"_Engine: {m['engine']}_")

if q := st.chat_input("e.g. क्या आयुर्वेदिक उत्पाद पर patent मिल सकता है?"):
    st.session_state.messages.append({"role": "user", "content": q})
    with st.chat_message("user"):
        st.markdown(q)

    with st.chat_message("assistant"):
        with st.spinner("Searching knowledge base..."):
            text, sources, engine = answer(q)
        st.markdown(text)
        with st.expander("📚 Sources"):
            for s in sources:
                st.caption(f"• {s}")
            st.caption(f"_Engine: {engine}_")
    st.session_state.messages.append(
        {"role": "assistant", "content": text, "sources": sources, "engine": engine}
    )
