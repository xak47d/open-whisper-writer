import io
import os
import json
import numpy as np
import soundfile as sf
import requests
from faster_whisper import WhisperModel
from openai import OpenAI

from utils import ConfigManager


# ---------------------------------------------------------------------------
# Provider registry
# ---------------------------------------------------------------------------

PROVIDERS = {
    'openai': {
        'name': 'OpenAI',
        'models': ['whisper-1', 'gpt-4o-transcribe', 'gpt-4o-mini-transcribe'],
        'key_field': 'openai_api_key',
        'model_field': 'openai_model',
    },
    'groq': {
        'name': 'Groq',
        'models': ['whisper-large-v3', 'whisper-large-v3-turbo', 'distil-whisper-large-v3-en'],
        'key_field': 'groq_api_key',
        'model_field': 'groq_model',
    },
    'deepgram': {
        'name': 'Deepgram',
        'models': ['nova-3', 'nova-2'],
        'key_field': 'deepgram_api_key',
        'model_field': 'deepgram_model',
    },
}


# ---------------------------------------------------------------------------
# Local model helpers
# ---------------------------------------------------------------------------

def create_local_model():
    """Create a local model using the faster-whisper library."""
    ConfigManager.console_print('Creating local model...')
    local_model_options = ConfigManager.get_config_section('model_options')['local']
    compute_type = local_model_options['compute_type']
    model_path = local_model_options.get('model_path')

    if compute_type == 'int8':
        device = 'cpu'
        ConfigManager.console_print('Using int8 quantization, forcing CPU usage.')
    elif compute_type in ('int8_float16', 'int8_bfloat16'):
        device = 'cuda'
        ConfigManager.console_print(f'Using {compute_type} quantization, forcing CUDA usage.')
    else:
        device = local_model_options['device']

    model_id = model_path or local_model_options['model']

    try:
        ConfigManager.console_print(f'Loading model: {model_id} (device={device}, compute_type={compute_type})')
        model = WhisperModel(model_id, device=device, compute_type=compute_type)
    except Exception as e:
        ConfigManager.console_print(f'Error initializing WhisperModel: {e}')
        ConfigManager.console_print('Falling back to CPU.')
        fallback_ct = 'int8' if compute_type in ('int8_float16', 'int8_bfloat16') else compute_type
        model = WhisperModel(model_id, device='cpu', compute_type=fallback_ct)

    ConfigManager.console_print('Local model created.')
    return model


# ---------------------------------------------------------------------------
# Local transcription
# ---------------------------------------------------------------------------

def transcribe_local(audio_data, local_model=None):
    """Transcribe audio using a local faster-whisper model."""
    if not local_model:
        local_model = create_local_model()
    model_options = ConfigManager.get_config_section('model_options')

    audio_data_float = audio_data.astype(np.float32) / 32768.0

    response = local_model.transcribe(
        audio=audio_data_float,
        language=model_options['common']['language'],
        initial_prompt=model_options['common']['initial_prompt'],
        condition_on_previous_text=model_options['local']['condition_on_previous_text'],
        temperature=model_options['common']['temperature'],
        vad_filter=model_options['local']['vad_filter'],
    )
    return ''.join(segment.text for segment in response[0])


# ---------------------------------------------------------------------------
# API transcription -- OpenAI & Groq (OpenAI-compatible)
# ---------------------------------------------------------------------------

def _audio_to_wav_bytes(audio_data):
    """Convert int16 numpy audio to in-memory WAV bytes."""
    byte_io = io.BytesIO()
    sample_rate = ConfigManager.get_config_section('recording_options').get('sample_rate') or 16000
    sf.write(byte_io, audio_data, sample_rate, format='wav')
    byte_io.seek(0)
    return byte_io


def _get_api_key(provider_id):
    """Get the API key for a provider from env or config."""
    info = PROVIDERS[provider_id]
    env_map = {
        'openai': 'OPENAI_API_KEY',
        'groq': 'GROQ_API_KEY',
        'deepgram': 'DEEPGRAM_API_KEY',
    }
    env_key = os.getenv(env_map.get(provider_id, ''))
    if env_key:
        return env_key
    return ConfigManager.get_config_value('model_options', 'api', info['key_field'])


def transcribe_openai(audio_data):
    """Transcribe using OpenAI API (or compatible endpoint)."""
    api_opts = ConfigManager.get_config_section('model_options', 'api')
    common = ConfigManager.get_config_section('model_options', 'common')

    client = OpenAI(
        api_key=_get_api_key('openai') or None,
        base_url=api_opts.get('openai_base_url') or 'https://api.openai.com/v1',
    )

    wav_bytes = _audio_to_wav_bytes(audio_data)
    model = api_opts.get('openai_model') or 'gpt-4o-mini-transcribe'

    kwargs = dict(
        model=model,
        file=('audio.wav', wav_bytes, 'audio/wav'),
    )
    # Only pass language/prompt/temperature for whisper-1 (older API)
    # gpt-4o models use a different parameter set but still accept these
    if common.get('language'):
        kwargs['language'] = common['language']
    if common.get('initial_prompt'):
        kwargs['prompt'] = common['initial_prompt']
    if common.get('temperature') is not None:
        kwargs['temperature'] = common['temperature']

    response = client.audio.transcriptions.create(**kwargs)
    return response.text


def transcribe_groq(audio_data):
    """Transcribe using Groq API (OpenAI-compatible)."""
    api_opts = ConfigManager.get_config_section('model_options', 'api')
    common = ConfigManager.get_config_section('model_options', 'common')

    client = OpenAI(
        api_key=_get_api_key('groq') or None,
        base_url='https://api.groq.com/openai/v1',
    )

    wav_bytes = _audio_to_wav_bytes(audio_data)
    model = api_opts.get('groq_model') or 'whisper-large-v3-turbo'

    kwargs = dict(
        model=model,
        file=('audio.wav', wav_bytes, 'audio/wav'),
    )
    if common.get('language'):
        kwargs['language'] = common['language']
    if common.get('initial_prompt'):
        kwargs['prompt'] = common['initial_prompt']
    if common.get('temperature') is not None:
        kwargs['temperature'] = common['temperature']

    response = client.audio.transcriptions.create(**kwargs)
    return response.text


# ---------------------------------------------------------------------------
# API transcription -- Deepgram
# ---------------------------------------------------------------------------

def transcribe_deepgram(audio_data):
    """Transcribe using Deepgram API (REST, not OpenAI-compatible)."""
    api_opts = ConfigManager.get_config_section('model_options', 'api')
    common = ConfigManager.get_config_section('model_options', 'common')

    api_key = _get_api_key('deepgram')
    if not api_key:
        raise ValueError("Deepgram API key not configured")

    model = api_opts.get('deepgram_model') or 'nova-3'
    wav_bytes = _audio_to_wav_bytes(audio_data)

    params = {'model': model}
    if common.get('language'):
        params['language'] = common['language']

    headers = {
        'Authorization': f'Token {api_key}',
        'Content-Type': 'audio/wav',
    }

    resp = requests.post(
        'https://api.deepgram.com/v1/listen',
        params=params,
        headers=headers,
        data=wav_bytes.read(),
        timeout=30,
    )
    resp.raise_for_status()
    result = resp.json()

    # Extract transcript from Deepgram response
    try:
        return result['results']['channels'][0]['alternatives'][0]['transcript']
    except (KeyError, IndexError):
        ConfigManager.console_print(f'Unexpected Deepgram response: {json.dumps(result, indent=2)}')
        return ''


# ---------------------------------------------------------------------------
# Post-processing
# ---------------------------------------------------------------------------

def post_process_transcription(transcription):
    """Apply post-processing to the transcription."""
    transcription = transcription.strip()
    post_processing = ConfigManager.get_config_section('post_processing')

    if post_processing.get('remove_trailing_period') and transcription.endswith('.'):
        transcription = transcription[:-1]
    if post_processing.get('add_trailing_space'):
        transcription += ' '
    if post_processing.get('remove_capitalization'):
        transcription = transcription.lower()

    return transcription


# ---------------------------------------------------------------------------
# Main dispatcher
# ---------------------------------------------------------------------------

_API_DISPATCHERS = {
    'openai': transcribe_openai,
    'groq': transcribe_groq,
    'deepgram': transcribe_deepgram,
}


def transcribe(audio_data, local_model=None):
    """Transcribe audio using the configured provider (API or local)."""
    if audio_data is None:
        return ''

    if ConfigManager.get_config_value('model_options', 'use_api'):
        provider = ConfigManager.get_config_value('model_options', 'api', 'provider') or 'openai'
        dispatcher = _API_DISPATCHERS.get(provider)
        if not dispatcher:
            raise ValueError(f"Unknown transcription provider: {provider}")
        ConfigManager.console_print(f'Transcribing with {PROVIDERS[provider]["name"]}...')
        transcription = dispatcher(audio_data)
    else:
        transcription = transcribe_local(audio_data, local_model)

    return post_process_transcription(transcription)
