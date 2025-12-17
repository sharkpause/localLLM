#!/usr/bin/env python3
import os
from bs4 import BeautifulSoup
import chromadb
from chromadb.config import Settings
import numpy as np
from ollama import Client

# ---------- CONFIG ----------
DUMP_DIR = "wiki_dump"          # folder with dumped HTML files
CHUNK_SIZE = 200                # smaller chunks to avoid embed limits
COLLECTION_NAME = "wiki_rag"
EMBED_MODEL = "nomic-embed-text:latest"
MAX_FILES=1000

# ---------- INIT ----------
ollama = Client()
client = chromadb.PersistentClient(
    path="./chroma_db",
    settings=Settings(
        anonymized_telemetry=False
    )
)

try:
    collection = client.get_collection(COLLECTION_NAME)
    print('Collection get')
except:
    collection = client.create_collection(COLLECTION_NAME)
    print('Collection created')

# ---------- FUNCTIONS ----------
def extract_text_from_html(file_path):
    """Extract visible text from an HTML file"""
    try:
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            soup = BeautifulSoup(f, "html.parser")
            text = soup.get_text(separator="\n")
            text = "\n".join([line.strip() for line in text.splitlines() if line.strip()])
            return text
    except Exception as e:
        print(f"Skipping {file_path}: {e}")
        return ""

def chunk_text(text, chunk_size=CHUNK_SIZE):
    """Split text into smaller chunks"""
    words = text.split()
    chunks = []
    for i in range(0, len(words), chunk_size):
        chunk = " ".join(words[i:i+chunk_size])
        if chunk.strip():
            chunks.append(chunk)
    return chunks

def embed_text(text):
    """Embed text using Ollama"""
    return np.array(ollama.embed(model=EMBED_MODEL, input=text).embeddings[0])

def process_folder(folder, max_files=MAX_FILES):
    """Walk folder and embed only the first max_files article files"""
    processed_files = 0
    for root, _, files in os.walk(folder):
        for file in files:
            if processed_files >= max_files:
                return
            path = os.path.join(root, file)
            if not os.path.isfile(path):
                continue
            if file.startswith("_") or file.endswith(".js") or file.startswith("."):
                continue
            text = extract_text_from_html(path)
            if not text:
                continue
            chunks = chunk_text(text)
            for idx, chunk in enumerate(chunks):
                try:
                    vector = embed_text(chunk)
                    doc_id = f"{path}_{idx}"
                    collection.add(
                        documents=[chunk],
                        ids=[doc_id],
                        embeddings=[vector.tolist()]
                    )
                except Exception as e:
                    print(f"Embedding failed for chunk {doc_id}: {e}")
            print(f"Processed {file}, {len(chunks)} chunks.")
            processed_files += 1

# ---------- RUN ----------
process_folder(DUMP_DIR)
print(f"Finished embedding first {MAX_FILES} files into Chroma!")

