from app.services.vector_store import get_collection

collection = get_collection()

print("Total chunks stored:", collection.count())

results = collection.get(
    include=["documents", "metadatas"]
)

for index, document in enumerate(results["documents"]):
    print(f"\nChunk {index + 1}:")
    print(document[:300])
    print("Metadata:", results["metadatas"][index])