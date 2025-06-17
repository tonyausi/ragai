import pytest
from unittest.mock import patch, MagicMock
from app.services.gemini import query_google_gemini


@pytest.fixture
def mock_settings(monkeypatch):
    monkeypatch.setattr("app.services.gemini.settings.GEMINI_API_KEY", "fake-api-key")


def test_query_google_gemini_success(mock_settings):
    mock_response = MagicMock()
    mock_response.text = "Paris"
    with patch("app.services.gemini.genai.Client") as mock_client_cls:
        mock_client = mock_client_cls.return_value
        mock_client.models.generate_content.return_value = mock_response
        result = query_google_gemini("What is the capital of France?")
        assert result == "Paris"


def test_query_google_gemini_exception_logged_and_returns_none(mock_settings):
    with patch("app.services.gemini.genai.Client") as mock_client_cls, patch(
        "app.services.gemini.logger"
    ) as mock_logger:
        mock_client = mock_client_cls.return_value
        mock_client.models.generate_content.side_effect = Exception("API error")
        result = query_google_gemini("What is the capital of France?")
        assert result is None
        assert mock_logger.error.called


def test_query_google_gemini_custom_api_key(monkeypatch):
    mock_response = MagicMock()
    mock_response.text = "Paris"
    with patch("app.services.gemini.genai.Client") as mock_client_cls:
        mock_client = mock_client_cls.return_value
        mock_client.models.generate_content.return_value = mock_response
        result = query_google_gemini(
            "What is the capital of France?", api_key="custom-key"
        )
        mock_client_cls.assert_called_with(api_key="custom-key")
        assert result == "Paris"


def test_query_google_gemini_real_api_key_used():
    result = query_google_gemini("What is the capital of China?")
    print(f"Result: {result}")
