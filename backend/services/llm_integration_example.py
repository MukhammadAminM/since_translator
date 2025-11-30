"""
Примеры интеграции с различными LLM провайдерами
Раскомментируйте и используйте нужный вариант в translator.py
"""

import os
from typing import Literal


# ============================================
# ВАРИАНТ 1: OpenAI
# ============================================
async def translate_with_openai(
    text: str,
    source_lang: Literal["ru", "ar", "zh"],
    target_lang: str = "en",
    model: str = "gpt-4o-mini"
) -> str:
    """
    Пример использования OpenAI API для перевода
    """
    try:
        from openai import AsyncOpenAI
        
        client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        
        lang_names = {
            "ru": "Russian",
            "ar": "Arabic", 
            "zh": "Chinese"
        }
        
        system_prompt = (
            f"You are a professional translator. "
            f"Translate the following text from {lang_names[source_lang]} to {target_lang.upper()}. "
            f"Maintain the original formatting, style, and tone. "
            f"Do not add any explanations or comments, only provide the translation."
        )
        
        response = await client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": text}
            ],
            temperature=0.3  # Низкая температура для более точного перевода
        )
        
        return response.choices[0].message.content.strip()
    
    except ImportError:
        raise ImportError("OpenAI library not installed. Run: pip install openai")
    except Exception as e:
        raise Exception(f"OpenAI API error: {str(e)}")


# ============================================
# ВАРИАНТ 2: Anthropic (Claude)
# ============================================
async def translate_with_anthropic(
    text: str,
    source_lang: Literal["ru", "ar", "zh"],
    target_lang: str = "en",
    model: str = "claude-3-5-sonnet-20241022"
) -> str:
    """
    Пример использования Anthropic API для перевода
    """
    try:
        from anthropic import AsyncAnthropic
        
        client = AsyncAnthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
        
        lang_names = {
            "ru": "Russian",
            "ar": "Arabic",
            "zh": "Chinese"
        }
        
        system_prompt = (
            f"You are a professional translator. "
            f"Translate the following text from {lang_names[source_lang]} to {target_lang.upper()}. "
            f"Maintain the original formatting, style, and tone. "
            f"Provide only the translation without any explanations."
        )
        
        message = await client.messages.create(
            model=model,
            max_tokens=4096,
            system=system_prompt,
            messages=[
                {"role": "user", "content": text}
            ]
        )
        
        return message.content[0].text.strip()
    
    except ImportError:
        raise ImportError("Anthropic library not installed. Run: pip install anthropic")
    except Exception as e:
        raise Exception(f"Anthropic API error: {str(e)}")


# ============================================
# ВАРИАНТ 3: Локальная модель (Ollama)
# ============================================
async def translate_with_ollama(
    text: str,
    source_lang: Literal["ru", "ar", "zh"],
    target_lang: str = "en",
    model: str = "llama2"
) -> str:
    """
    Пример использования локальной модели через Ollama
    Требует запущенный Ollama сервер: https://ollama.ai
    """
    try:
        import aiohttp
        
        lang_names = {
            "ru": "Russian",
            "ar": "Arabic",
            "zh": "Chinese"
        }
        
        prompt = (
            f"Translate the following text from {lang_names[source_lang]} to {target_lang.upper()}. "
            f"Maintain the original formatting and style. "
            f"Provide only the translation:\n\n{text}"
        )
        
        async with aiohttp.ClientSession() as session:
            async with session.post(
                "http://localhost:11434/api/generate",
                json={
                    "model": model,
                    "prompt": prompt,
                    "stream": False
                }
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    return data.get("response", "").strip()
                else:
                    raise Exception(f"Ollama API error: {response.status}")
    
    except ImportError:
        raise ImportError("aiohttp library not installed. Run: pip install aiohttp")
    except Exception as e:
        raise Exception(f"Ollama API error: {str(e)}")


# ============================================
# ВАРИАНТ 4: Google Translate API
# ============================================
async def translate_with_google(
    text: str,
    source_lang: Literal["ru", "ar", "zh"],
    target_lang: str = "en"
) -> str:
    """
    Пример использования Google Cloud Translation API
    """
    try:
        from google.cloud import translate_v2 as translate
        
        client = translate.Client()
        
        result = client.translate(
            text,
            source_language=source_lang,
            target_language=target_lang
        )
        
        return result['translatedText']
    
    except ImportError:
        raise ImportError(
            "Google Cloud Translation library not installed. "
            "Run: pip install google-cloud-translate"
        )
    except Exception as e:
        raise Exception(f"Google Translate API error: {str(e)}")

