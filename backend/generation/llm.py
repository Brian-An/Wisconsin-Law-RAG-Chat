from openai import OpenAI
from backend.config import settings
import logging
from typing import Optional

logger = logging.getLogger(__name__)

_openai_client: Optional[OpenAI] = None

def get_openai_client() -> OpenAI:
    global _openai_client

    if _openai_client is None:
        if not settings.OPENAI_API_KEY:
            raise ValueError("OPENAI_API_KEY is not set")
        
        _openai_client = OpenAI(api_key=settings.OPENAI_API_KEY)
        logger.info(f"OpenAI client initialized")
    return _openai_client

def generate_response(
    prompt: str, 
    system_prompt : Optional[str] = None, 
    model: str = "gpt-3.5-turbo", 
    temperature: float = 0.3, 
    max_tokens: Optional[int] = None) -> str:
    
    client = get_openai_client()

    messages = []

    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})

    messages.append({"role": "user", "content": prompt})

    try:
        logger.info(f"Generating response with model {model}")
        response = client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens
        )
        logger.info(f"Response generated with model {model}")
        return response.choices[0].message.content

    except Exception as e:
        logger.error(f"Error generating response with model {model}: {e}")
        raise e