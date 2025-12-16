#!/usr/bin/env python3
from ollama import Client
import chromadb
from chromadb.config import Settings
import numpy as np
import logging

logging.getLogger("chromadb.telemetry.product.posthog").setLevel(logging.CRITICAL)

ollama = Client()

client = chromadb.Client(settings=Settings(anonymized_telemetry=False))
try:
    collection = client.get_collection("wiki_rag")
except:
    collection = client.create_collection("wiki_rag")

def embed_text(text: str):
    e = ollama.embed(model="nomic-embed-text:latest", input=text)
    return np.array(e.embeddings[0])

def retrieve_context(query: str, k=5):
    query_vec = embed_text(query)
    results = collection.query(query_embeddings=[query_vec.tolist()], n_results=k)
    docs = results["documents"][0]
    return "\n".join(docs)

def ask_rag(query: str):
    context = retrieve_context(query)
    prompt = f"Context:\n{context}\n\nQuestion: {query}"
    resp = ollama.generate(model="gemma3:4b", prompt=prompt)
    return resp.response

if __name__ == "__main__":
    print("RAG CLI — type your question (exit to quit)")
    while True:
        q = input("> ")
        if q.strip().lower() in ["exit", "quit"]:
            break

        answer = ask_rag(q)
        print("\n" + answer + "\n")

