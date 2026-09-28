# app.py — complete final version
import time
import chromadb
from sentence_transformers import SentenceTransformer
from google import genai

API_KEY = "AQ.Ab8RN6JQ_-7Ur9Ur0S30yN-fic7DZBiBIef9Gva-XbtDmGXsGQ"   # your key should already be here — keep it!

gemini = genai.Client(api_key=API_KEY)
embedder = SentenceTransformer("paraphrase-multilingual-MiniLM-L12-v2")
collection = chromadb.PersistentClient(path="db").get_collection("ipsakti")


def ask(question: str) -> str:
    q_vec = embedder.encode([question]).tolist()
    results = collection.query(query_embeddings=q_vec, n_results=4)

    context = ""
    for doc, meta in zip(results["documents"][0], results["metadatas"][0]):
        context += f"[Source: {meta['source']}]\n{doc}\n\n"

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

    for attempt in range(4):
        try:
            response = gemini.models.generate_content(
                model="gemini-3.8-flash",
                contents=prompt,
            )
            return response.text
        except Exception:
            if attempt < 3:
                wait = 10 * (attempt + 1)
                print(f"(Google busy, retrying in {wait}s...)")
                time.sleep(wait)
            else:
                return "Sorry, the AI service is temporarily unavailable. Please try again."


if __name__ == "__main__":
    print("IP-SAKTI Sahayak ready. Type 'quit' to exit.\n")
    while True:
        q = input("You: ").strip()
        if q.lower() in ("quit", "exit"):
            break
        print("\nSahayak:", ask(q), "\n")