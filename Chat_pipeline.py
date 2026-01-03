import os
import sys
import json
import requests
from dotenv import load_dotenv
from sqlalchemy import create_engine, text

load_dotenv()

CONFIG = {
    "maple_key": os.getenv("MAPLE_KEY"),
    "voyage_key": os.getenv("VOYAGE_API_KEY"),
    "chat_url": "http://localhost:8080/v1/chat/completions",
    "emb_url": "https://api.voyageai.com/v1/embeddings",
    "db_url": os.getenv("DATABASE_URL") if os.getenv("DATABASE_URL") else None,
    "model": "llama-3.3-70b"
}

def get_db_engine():
    if not CONFIG["db_url"]:
        return None
    return create_engine(CONFIG["db_url"])

def get_embedding(text_input):
    try:
        if not CONFIG["voyage_key"]:
            return []
            
        resp = requests.post(
            CONFIG["emb_url"],
            headers={"Authorization": f"Bearer {CONFIG['voyage_key']}"},
            json={"model": "voyage-3", "input": text_input, "input_type": "query"},
            timeout=10
        )
        resp.raise_for_status()
        return resp.json()["data"][0]["embedding"]
    except Exception:
        return []

def retrieve_context(query_text):
    vector = get_embedding(query_text)
    if not vector: return ""
    
    try:
        db = get_db_engine()
        if not db: return ""
        
        with db.connect() as conn:
            sql = text("SELECT content FROM knowledge_chunks ORDER BY embedding <=> CAST(:vec AS vector) LIMIT 8")
            rows = conn.execute(sql, {"vec": str(vector)}).fetchall()
        return "\n---\n".join(r[0] for r in rows)
    except Exception:
        return ""

def llm_chat(messages, temperature=0.1, json_mode=False):
    try:
        if not CONFIG["maple_key"]:
            return None

        payload = {
            "model": CONFIG["model"],
            "messages": messages,
            "temperature": temperature,
            "max_tokens": 8192,
            "frequency_penalty": 0.5,
            "presence_penalty": 0.5
        }
        if json_mode:
            payload["response_format"] = {"type": "json_object"}

        resp = requests.post(
            CONFIG["chat_url"],
            headers={"Authorization": f"Bearer {CONFIG['maple_key']}"},
            json=payload,
            timeout=120
        )
        resp.raise_for_status() 
        return resp.json()["choices"][0]["message"]["content"]
    except Exception:
        return None