import pytest
from app.tools.vision import VisionTools

def test_take_screenshot(tmp_path, monkeypatch):
    monkeypatch.setattr("app.tools.vision.settings.workspace_dir", str(tmp_path))
    
    tools = VisionTools()
    result = tools.take_screenshot("screen.png")
    
    assert "successfully saved" in result
    assert (tmp_path / "screen.png").exists()
