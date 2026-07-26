import pytest
import os
from app.memory.database import LocalDatabase

def test_local_database_operations(tmp_path):
    db_file = tmp_path / "test_myra.db"
    db = LocalDatabase(str(db_file))
    
    # 1. Test conversation logging and retrieval
    row_id1 = db.log_conversation("sess-1", "user", "audio", "[User Voice Speech Detected]")
    assert row_id1 is not None
    row_id2 = db.log_conversation("sess-1", "myra", "text", "হ্যালো, আমি মায়রা! কিভাবে সাহায্য করতে পারি?")
    assert row_id2 is not None
    
    recent = db.get_recent_conversations(session_id="sess-1")
    assert len(recent) == 2
    assert recent[1]["sender"] == "myra"
    assert "মায়রা" in recent[1]["content"]
    
    # 2. Test search conversations
    results = db.search_conversations("সাহায্য")
    assert len(results) == 1
    
    # 3. Test memory saving and retrieval
    assert db.save_memory("favorite_language", "Bengali")
    assert db.get_memory("favorite_language") == "Bengali"
    
    memories = db.get_all_memories()
    assert "favorite_language" in memories
    
    # 4. Test data import
    imp_id = db.import_data("project", "github", "commit: initial import")
    assert imp_id is not None
