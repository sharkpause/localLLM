import chromadb
from chromadb.config import Settings

client = chromadb.PersistentClient(
    path="./chroma_db",
    settings=Settings(
        anonymized_telemetry=False
    )
)
collection = client.get_collection("wiki_rag")

docs = collection.get()
print("Number of documents in collection:", len(docs["ids"]))

for i, doc in enumerate(docs["documents"]):
    print(f"Document {i}:")
    print(doc)
    print("-"*20)
