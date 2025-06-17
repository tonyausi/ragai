import logging
from google import genai
from typing import Union
from app.config.setting import settings

logger = logging.getLogger("celery")


def query_google_gemini(
    query: str,
    model: str = settings.PUBLIC_LLM_MODEL,
    api_key: str = settings.GEMINI_API_KEY,
) -> Union[str, None]:
    """
    Query Google Gemini API with the provided query string.
    Returns the response text or None if an error occurs.
    """
    client = genai.Client(api_key=api_key)
    try:
        response = client.models.generate_content(
            model=model,
            contents=query,
        )
        return response.text
    except Exception as e:
        logger.error(f"Error querying Google Gemini: {e}")
        return None
