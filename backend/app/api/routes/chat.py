
from datetime import datetime, timezone
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.models import User, Conversation, Message
from app.schemas.chat import (
    ChatRequest,
    ChatResponse,
    SourceReference,
    ConversationSummary,
    ConversationDetail,
    MessageResponse,
)
from app.security.permissions import require_roles
from app.services.document_authorization import (
    get_authorized_document_ids,
)
from app.services.retrieval_service import search_authorized_chunks
from app.services.llm_service import generate_answer


router = APIRouter(tags=["Chat"])


def get_user_conversation(
    db: Session,
    conversation_id,
    user_id,
):
    statement = select(Conversation).where(
        Conversation.id == conversation_id,
        Conversation.user_id == user_id,
    )

    conversation = db.scalar(statement)

    if conversation is None:
        raise HTTPException(
            status_code=404,
            detail="Conversation not found",
        )

    return conversation


def get_recent_conversation_history(
    db: Session,
    conversation_id,
    limit: int = 10,
) -> list[dict]:

    statement = (
        select(Message)
        .where(Message.conversation_id == conversation_id)
        .order_by(Message.created_at.desc(), Message.id.desc())
        .limit(limit)
    )

    messages = db.scalars(statement).all()

    # The query returns newest first.
    # Reverse it so the LLM receives chronological history.
    messages = list(reversed(messages))

    return [
        {
            "role": message.role,
            "content": message.content,
        }
        for message in messages
    ]


@router.post("/api/v1/chat", response_model=ChatResponse)
def chat(
    request: ChatRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_roles("EMPLOYEE", "DEPARTMENT_ADMIN", "SUPER_ADMIN")
    ),
):
    try:
        # Step 1: Find an existing conversation or create one.
        if request.conversation_id:
            conversation = get_user_conversation(
                db=db,
                conversation_id=request.conversation_id,
                user_id=current_user.id,
            )
        else:
            conversation = Conversation(
                id=uuid4(),
                user_id=current_user.id,
                title=request.question.strip()[:200],
            )
            db.add(conversation)
            db.flush()

        # Step 2: Load previous messages BEFORE adding
        # the current user question.
        conversation_history = get_recent_conversation_history(
            db=db,
            conversation_id=conversation.id,
            limit=10,
        )

        # Step 3: Save the current user message.
        user_message = Message(
            conversation_id=conversation.id,
            role="user",
            content=request.question,
            created_at=datetime.now(timezone.utc),
        )
        db.add(user_message)

        # Step 4: Determine authorized documents.
        authorized_document_ids = get_authorized_document_ids(
            db=db,
            current_user=current_user,
        )

        # Step 5: Retrieve authorized document chunks.
        retrieved_chunks = search_authorized_chunks(
            query=request.question,
            authorized_document_ids=authorized_document_ids,
            top_k=request.top_k,
        )

        # Step 6: Generate an answer using conversation history.
        answer = generate_answer(
            question=request.question,
            retrieved_chunks=retrieved_chunks,
            conversation_history=conversation_history,
        )

        # Step 7: Save the assistant response.
        assistant_message = Message(
            conversation_id=conversation.id,
            role="assistant",
            content=answer,
            created_at=datetime.now(timezone.utc),
        )
        db.add(assistant_message)

        conversation.updated_at = datetime.now(timezone.utc)

        # Step 8: Build structured source references.
        sources = [
            SourceReference(
                source_number=index,
                document_id=chunk["document_id"],
                chunk_index=chunk["chunk_index"],
                file_type=chunk["file_type"],
            )
            for index, chunk in enumerate(retrieved_chunks, start=1)
        ]

        conversation_id = conversation.id

        db.commit()

        return ChatResponse(
            conversation_id=conversation_id,
            answer=answer,
            sources=sources,
        )

    except Exception:
        db.rollback()
        raise


@router.get(
    "/api/v1/conversations",
    response_model=list[ConversationSummary],
)
def list_conversations(
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_roles("EMPLOYEE", "DEPARTMENT_ADMIN", "SUPER_ADMIN")
    ),
):
    statement = (
        select(Conversation)
        .where(Conversation.user_id == current_user.id)
        .order_by(Conversation.updated_at.desc())
    )

    conversations = db.scalars(statement).all()

    return [
        ConversationSummary(
            id=conversation.id,
            title=conversation.title,
            created_at=conversation.created_at,
            updated_at=conversation.updated_at,
        )
        for conversation in conversations
    ]


@router.get(
    "/api/v1/conversations/{conversation_id}",
    response_model=ConversationDetail,
)
def get_conversation(
    conversation_id,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_roles("EMPLOYEE", "DEPARTMENT_ADMIN", "SUPER_ADMIN")
    ),
):
    conversation = get_user_conversation(
        db=db,
        conversation_id=conversation_id,
        user_id=current_user.id,
    )

    statement = (
        select(Message)
        .where(Message.conversation_id == conversation.id)
        .order_by(Message.created_at.asc(), Message.id.asc())
    )

    messages = db.scalars(statement).all()

    return ConversationDetail(
        id=conversation.id,
        title=conversation.title,
        created_at=conversation.created_at,
        updated_at=conversation.updated_at,
        messages=[
            MessageResponse(
                id=message.id,
                role=message.role,
                content=message.content,
                created_at=message.created_at,
            )
            for message in messages
        ],
    )
