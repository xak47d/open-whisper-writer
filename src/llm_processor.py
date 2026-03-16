"""LLM post-processing for transcription results.

Supports OpenAI-compatible, Anthropic, and Ollama backends.
"""

import os
import requests
from openai import OpenAI

from utils import ConfigManager


# ---------------------------------------------------------------------------
# Built-in system prompts for each processing mode
# ---------------------------------------------------------------------------

SYSTEM_PROMPTS = {
    'clean_up': (
        "You are a text editor. Clean up the following dictated text: fix grammar, "
        "punctuation, and spelling errors. Remove filler words (um, uh, like, you know). "
        "Keep the original meaning and tone. Output ONLY the corrected text, nothing else."
    ),
    'formal': (
        "You are a professional editor. Rewrite the following dictated text in a clear, "
        "professional, and formal tone. Fix any grammar or punctuation issues. "
        "Output ONLY the rewritten text, nothing else."
    ),
    'translate': (
        "You are a translator. Translate the following text to {target_language}. "
        "Output ONLY the translation, nothing else."
    ),
    'custom': None,  # Uses user-provided prompt
}


def _get_system_prompt():
    """Build the system prompt based on the configured mode."""
    mode = ConfigManager.get_config_value('llm_processing', 'mode') or 'clean_up'

    if mode == 'custom':
        prompt = ConfigManager.get_config_value('llm_processing', 'custom_prompt')
        if not prompt:
            return SYSTEM_PROMPTS['clean_up']
        return prompt

    prompt_template = SYSTEM_PROMPTS.get(mode, SYSTEM_PROMPTS['clean_up'])

    if mode == 'translate':
        target = ConfigManager.get_config_value('llm_processing', 'target_language') or 'English'
        return prompt_template.format(target_language=target)

    return prompt_template


def _get_llm_api_key():
    """Get the LLM API key from env or config."""
    provider = ConfigManager.get_config_value('llm_processing', 'provider') or 'openai'
    env_map = {
        'openai': 'OPENAI_API_KEY',
        'anthropic': 'ANTHROPIC_API_KEY',
    }
    env_key = os.getenv(env_map.get(provider, ''))
    if env_key:
        return env_key
    return ConfigManager.get_config_value('llm_processing', 'api_key')


# ---------------------------------------------------------------------------
# OpenAI-compatible backend
# ---------------------------------------------------------------------------

def _process_openai(text, system_prompt):
    """Process text using an OpenAI-compatible API."""
    api_key = _get_llm_api_key()
    base_url = ConfigManager.get_config_value('llm_processing', 'base_url')
    model = ConfigManager.get_config_value('llm_processing', 'model') or 'gpt-4o-mini'

    client = OpenAI(
        api_key=api_key or None,
        base_url=base_url or 'https://api.openai.com/v1',
    )

    response = client.chat.completions.create(
        model=model,
        messages=[
            {'role': 'system', 'content': system_prompt},
            {'role': 'user', 'content': text},
        ],
        temperature=0.3,
        max_tokens=4096,
    )
    return response.choices[0].message.content.strip()


# ---------------------------------------------------------------------------
# Anthropic backend
# ---------------------------------------------------------------------------

def _process_anthropic(text, system_prompt):
    """Process text using the Anthropic API."""
    try:
        import anthropic
    except ImportError:
        raise ImportError(
            "The 'anthropic' package is required for Anthropic LLM processing. "
            "Install it with: pip install anthropic"
        )

    api_key = _get_llm_api_key()
    if not api_key:
        raise ValueError("Anthropic API key not configured")

    model = ConfigManager.get_config_value('llm_processing', 'model') or 'claude-sonnet-4-20250514'

    client = anthropic.Anthropic(api_key=api_key)
    response = client.messages.create(
        model=model,
        max_tokens=4096,
        system=system_prompt,
        messages=[
            {'role': 'user', 'content': text},
        ],
    )
    return response.content[0].text.strip()


# ---------------------------------------------------------------------------
# Ollama backend
# ---------------------------------------------------------------------------

def _process_ollama(text, system_prompt):
    """Process text using a local Ollama instance."""
    base_url = ConfigManager.get_config_value('llm_processing', 'base_url') or 'http://localhost:11434'
    model = ConfigManager.get_config_value('llm_processing', 'model') or 'llama3'

    resp = requests.post(
        f'{base_url}/api/chat',
        json={
            'model': model,
            'messages': [
                {'role': 'system', 'content': system_prompt},
                {'role': 'user', 'content': text},
            ],
            'stream': False,
        },
        timeout=60,
    )
    resp.raise_for_status()
    return resp.json()['message']['content'].strip()


# ---------------------------------------------------------------------------
# Main dispatcher
# ---------------------------------------------------------------------------

_LLM_DISPATCHERS = {
    'openai': _process_openai,
    'anthropic': _process_anthropic,
    'ollama': _process_ollama,
}


def is_enabled():
    """Check if LLM processing is enabled."""
    return bool(ConfigManager.get_config_value('llm_processing', 'enabled'))


def process(text):
    """Process transcribed text through the configured LLM.

    Returns the original text unchanged if LLM processing is disabled or fails.
    """
    if not text or not text.strip():
        return text

    if not is_enabled():
        return text

    provider = ConfigManager.get_config_value('llm_processing', 'provider') or 'openai'
    dispatcher = _LLM_DISPATCHERS.get(provider)
    if not dispatcher:
        ConfigManager.console_print(f'Unknown LLM provider: {provider}')
        return text

    system_prompt = _get_system_prompt()
    mode = ConfigManager.get_config_value('llm_processing', 'mode') or 'clean_up'

    try:
        ConfigManager.console_print(f'LLM processing ({provider}/{mode})...')
        result = dispatcher(text, system_prompt)
        ConfigManager.console_print(f'LLM result: {result}')
        return result
    except Exception as e:
        ConfigManager.console_print(f'LLM processing failed: {e}')
        return text
