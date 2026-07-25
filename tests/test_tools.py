import pytest
from pathlib import Path
from app.tools.file_system import FileSystemTools
from app.tools.destructive_gate import DestructiveActionGate
from app.core.state_machine import StateMachine

def test_file_system_sandbox(tmp_path, monkeypatch):
    # Set workspace_dir to tmp_path
    monkeypatch.setattr("app.tools.file_system.settings.workspace_dir", str(tmp_path))
    fs = FileSystemTools()
    
    # Try directory traversal
    with pytest.raises(PermissionError):
        fs.read_file("../../windows/system32/cmd.exe")

    # Safe write and read
    write_res = fs.write_file("test.txt", "hello")
    assert "Successfully" in write_res
    
    read_res = fs.read_file("test.txt")
    assert read_res == "hello"

def test_destructive_gate():
    sm = StateMachine()
    gate = DestructiveActionGate(sm)
    
    assert gate.is_dangerous("rm -rf /") is True
    assert gate.is_dangerous("del /s /q *") is True
    assert gate.is_dangerous("git push --force origin main") is True
    assert gate.is_dangerous("ls -la") is False
    assert gate.is_dangerous("python script.py") is False
    
    # Case insensitivity
    assert gate.is_dangerous("RM -RF /") is True
