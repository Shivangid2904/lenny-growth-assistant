import uuid
from sqlalchemy import text
from app.models.session import Session
from app.models.message import Message
from app.models.transcript_chunk import TranscriptChunk
from app.models.artifact import Artifact


def test_pgvector_column_type(db):
    """Verify that transcript_chunks.embedding column is actually vector(768) in PostgreSQL."""
    result = db.execute(
        text(
            """
            SELECT data_type, udt_name 
            FROM information_schema.columns 
            WHERE table_name = 'transcript_chunks' AND column_name = 'embedding';
            """
        )
    ).fetchone()
    assert result is not None
    # In PostgreSQL with pgvector, udt_name is 'vector'
    assert result[1] == "vector"

    # Also verify dimension directly via pg_attribute / pgvector type info
    dim_result = db.execute(
        text(
            """
            SELECT atttypmod 
            FROM pg_attribute 
            WHERE attrelid = 'transcript_chunks'::regclass AND attname = 'embedding';
            """
        )
    ).scalar()
    # atttypmod for vector(768) is 768
    assert dim_result == 768


def test_vector_insertion_and_distance_search(db):
    """Verify inserting 768-dimensional embedding and querying with pgvector cosine distance <=>."""
    vec1 = [0.1] * 768
    vec2 = [0.9] * 768

    chunk1 = TranscriptChunk(
        episode_id="ep-101",
        episode_title="Elena Verna on PLG",
        chunk_index=0,
        content="Product led growth is about creating self-serve motions.",
        chunk_metadata={"guest": "Elena Verna"},
        embedding=vec1,
    )
    chunk2 = TranscriptChunk(
        episode_id="ep-102",
        episode_title="Casey Winters on Loops",
        chunk_index=0,
        content="Growth loops are closed systems where inputs produce outputs.",
        chunk_metadata={"guest": "Casey Winters"},
        embedding=vec2,
    )
    db.add_all([chunk1, chunk2])
    db.commit()

    # Query with cosine distance <=> to vec1
    # chunk1 should be closest
    query_vec = str(vec1)
    results = db.execute(
        text(
            f"""
            SELECT id, episode_title, embedding <=> '{query_vec}' AS distance
            FROM transcript_chunks
            ORDER BY embedding <=> '{query_vec}' ASC
            LIMIT 1;
            """
        )
    ).fetchone()

    assert results is not None
    assert results[1] == "Elena Verna on PLG"
    assert abs(results[2]) < 1e-4  # Cosine distance to itself is ~0


def test_session_cascade_deletion(db):
    """Verify deleting a session cascades and removes associated messages and artifacts in PostgreSQL."""
    session = Session(title="Cascade Test Session")
    db.add(session)
    db.commit()
    db.refresh(session)

    # Add message
    msg = Message(
        session_id=session.id,
        role="user",
        content="Test user message",
    )
    # Add artifact
    art = Artifact(
        session_id=session.id,
        type="markdown",
        title="Test Artifact",
        content="# Sample Doc",
        sanitized=True,
    )
    db.add_all([msg, art])
    db.commit()

    # Verify rows exist
    assert db.query(Message).filter(Message.session_id == session.id).count() == 1
    assert db.query(Artifact).filter(Artifact.session_id == session.id).count() == 1

    # Delete session
    db.delete(session)
    db.commit()

    # Verify cascade deletion took place in PostgreSQL
    assert db.query(Session).filter(Session.id == session.id).count() == 0
    assert db.query(Message).filter(Message.session_id == session.id).count() == 0
    assert db.query(Artifact).filter(Artifact.session_id == session.id).count() == 0
