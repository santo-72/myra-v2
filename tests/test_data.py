import pytest
import pandas as pd
from app.tools.data_analysis import DataAnalysisTools

def test_analyze_csv(tmp_path, monkeypatch):
    monkeypatch.setattr("app.tools.data_analysis.settings.workspace_dir", str(tmp_path))
    data = {"col1": [1, 2, 3], "col2": [4, 5, 6]}
    df = pd.DataFrame(data)
    
    csv_path = tmp_path / "test.csv"
    df.to_csv(csv_path, index=False)
    
    tools = DataAnalysisTools()
    result = tools.analyze_csv_summary("test.csv")
    
    assert "INFO" in result
    assert "STATS" in result
    assert "HEAD" in result

def test_plot_chart(tmp_path, monkeypatch):
    monkeypatch.setattr("app.tools.data_analysis.settings.workspace_dir", str(tmp_path))
    data = {"col1": [1, 2, 3], "col2": [4, 5, 6]}
    df = pd.DataFrame(data)
    
    csv_path = tmp_path / "test.csv"
    df.to_csv(csv_path, index=False)
    
    tools = DataAnalysisTools()
    result = tools.plot_basic_chart("test.csv", "col1", "col2", "bar", "out.png")
    
    assert "Successfully" in result
    assert (tmp_path / "out.png").exists()
