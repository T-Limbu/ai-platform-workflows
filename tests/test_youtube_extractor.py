import pytest
import os
import sys
import json
from unittest.mock import patch, MagicMock

# Add the root directory to sys.path to allow importing from connectors
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from connectors.youtube.extractor import get_video_id, main
from google.genai.errors import APIError

def test_get_video_id():
    assert get_video_id("https://www.youtube.com/watch?v=dQw4w9WgXcQ") == "dQw4w9WgXcQ"
    assert get_video_id("https://youtu.be/dQw4w9WgXcQ") == "dQw4w9WgXcQ"
    assert get_video_id("https://www.youtube.com/embed/dQw4w9WgXcQ") == "dQw4w9WgXcQ"
    assert get_video_id("https://www.youtube.com/watch?v=dQw4w9WgXcQ&t=42s") == "dQw4w9WgXcQ"
    
    with pytest.raises(ValueError):
        get_video_id("https://www.example.com")

@patch('os.environ.get')
def test_missing_api_key(mock_env_get, capsys):
    mock_env_get.return_value = None
    test_args = ["extractor.py", "--url", "https://www.youtube.com/watch?v=dQw4w9WgXcQ"]
    with patch.object(sys, 'argv', test_args):
        with pytest.raises(SystemExit) as e:
            main()
        assert e.value.code == 1
        captured = capsys.readouterr()
        assert "GEMINI_API_KEY environment variable is not set" in captured.err

@patch('connectors.youtube.extractor.genai.Client')
@patch('os.environ.get')
def test_successful_extraction_json(mock_env_get, mock_client, tmp_path):
    mock_env_get.side_effect = lambda k, default=None: "fake_key" if k == "GEMINI_API_KEY" else default
    
    mock_instance = MagicMock()
    mock_client.return_value = mock_instance
    mock_response = MagicMock()
    mock_response.text = '{"status": "success"}'
    mock_instance.models.generate_content.return_value = mock_response

    # Change working directory so output.json goes to tmp_path
    original_cwd = os.getcwd()
    os.chdir(tmp_path)
    
    try:
        test_args = ["extractor.py", "--url", "https://www.youtube.com/watch?v=dQw4w9WgXcQ", "--format", "json"]
        with patch.object(sys, 'argv', test_args):
            main()
        
        assert os.path.exists("output.json")
        with open("output.json", "r") as f:
            data = json.load(f)
            assert data["status"] == "success"
    finally:
        os.chdir(original_cwd)

@patch('connectors.youtube.extractor.genai.Client')
@patch('os.environ.get')
def test_successful_extraction_markdown(mock_env_get, mock_client, tmp_path):
    mock_env_get.side_effect = lambda k, default=None: "fake_key" if k == "GEMINI_API_KEY" else default
    
    mock_instance = MagicMock()
    mock_client.return_value = mock_instance
    mock_response = MagicMock()
    mock_response.text = '# Hello\\nMarkdown'
    mock_instance.models.generate_content.return_value = mock_response

    original_cwd = os.getcwd()
    os.chdir(tmp_path)
    
    try:
        test_args = ["extractor.py", "--url", "https://www.youtube.com/watch?v=dQw4w9WgXcQ", "--format", "markdown"]
        with patch.object(sys, 'argv', test_args):
            main()
        
        assert os.path.exists("output.md")
        with open("output.md", "r") as f:
            content = f.read()
            assert "Markdown" in content
    finally:
        os.chdir(original_cwd)

@patch('connectors.youtube.extractor.genai.Client')
@patch('os.environ.get')
def test_model_fallback(mock_env_get, mock_client, tmp_path):
    mock_env_get.side_effect = lambda k, default=None: "fake_key" if k == "GEMINI_API_KEY" else default
    
    mock_instance = MagicMock()
    mock_client.return_value = mock_instance
    
    # First call fails with 503, second call succeeds
    def mock_generate(*args, **kwargs):
        if kwargs.get('model') == 'gemini-3.8-flash':
            raise APIError(503, {"error": {"message": "503 Service Unavailable", "code": 503}})
        
        response = MagicMock()
        response.text = '{"status": "fallback_success"}'
        return response
        
    mock_instance.models.generate_content.side_effect = mock_generate

    original_cwd = os.getcwd()
    os.chdir(tmp_path)
    
    try:
        test_args = ["extractor.py", "--url", "https://www.youtube.com/watch?v=dQw4w9WgXcQ"]
        with patch.object(sys, 'argv', test_args):
            main()
            
        assert os.path.exists("output.json")
        with open("output.json", "r") as f:
            data = json.load(f)
            assert data["status"] == "fallback_success"
    finally:
        os.chdir(original_cwd)


@patch('connectors.youtube.extractor.genai.Client')
def test_output_delimiter_survives_eof_line(mock_client, tmp_path, monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "fake_key")
    gh_output = tmp_path / "gh_output.txt"
    monkeypatch.setenv("GITHUB_OUTPUT", str(gh_output))
    monkeypatch.chdir(tmp_path)

    text = "first line\nEOF\nextra_output=pwned\nlast line"
    mock_response = MagicMock()
    mock_response.text = text
    mock_client.return_value.models.generate_content.return_value = mock_response

    with patch.object(sys, 'argv', ["extractor.py", "--url", "https://www.youtube.com/watch?v=dQw4w9WgXcQ", "--format", "markdown"]):
        main()

    lines = gh_output.read_text(encoding="utf-8").split("\n")
    start = next(i for i, l in enumerate(lines) if l.startswith("extracted_content<<"))
    delimiter = lines[start].split("<<", 1)[1]
    assert delimiter != "EOF"
    end = lines.index(delimiter, start + 1)
    assert "\n".join(lines[start + 1:end]) == text
