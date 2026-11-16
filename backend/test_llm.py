from app.services.llm_service import generate_answer


test_chunks = [
    {
        "document_id": "test-document-001",
        "chunk_index": 0,
        "text": """
        Employees are entitled to 18 days of annual leave
        every calendar year. Unused annual leave can be
        carried forward up to 5 days.
        """
    }
]

question = "How many annual leave days do employees receive?"

answer = generate_answer(
    question=question,
    retrieved_chunks=test_chunks
)

print("\nQUESTION:")
print(question)

print("\nGENERATED ANSWER:")
print(answer)