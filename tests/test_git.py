import pytest
from pathlib import Path
from app.tools.git_github import GitTools
import git

def test_git_init_and_commit(tmp_path, monkeypatch):
    monkeypatch.setattr("app.tools.git_github.settings.workspace_dir", str(tmp_path))
    git_tools = GitTools()
    
    # Test init
    init_res = git_tools.git_init()
    assert "Successfully initialized" in init_res
    assert (tmp_path / ".git").exists()
    
    # Write a test file
    (tmp_path / "test.txt").write_text("hello git", encoding="utf-8")
    
    # Test commit
    commit_res = git_tools.git_commit("Initial commit")
    assert "Successfully committed changes" in commit_res
    
    # Verify via gitpython
    repo = git.Repo(tmp_path)
    assert not repo.is_dirty()
    assert "Initial commit" in repo.head.commit.message
