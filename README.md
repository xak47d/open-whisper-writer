# <img src="./assets/ww-logo.png" alt="WhisperWriter icon" width="25" height="25"> WhisperWriter

![version](https://img.shields.io/badge/version-1.1.0-blue)
![python](https://img.shields.io/badge/python-3.10%2B-blue)
![license](https://img.shields.io/badge/license-GPL--3.0-green)
![platform](https://img.shields.io/badge/platform-Linux-lightgrey)

<p align="center">
    <img src="./assets/ww-demo-image-02.gif" alt="WhisperWriter demo gif" width="340" height="136">
</p>

WhisperWriter is a speech-to-text desktop application that uses [OpenAI's Whisper model](https://openai.com/research/whisper) to auto-transcribe recordings from your microphone and type them into the active window.

> This is a maintained fork of [savbell/whisper-writer](https://github.com/savbell/whisper-writer) with updated dependencies, new model support, Linux packaging, and CI/CD.

## What's New in v1.1.0

- **New models**: `large-v3-turbo`, `turbo`, and five `distil-*` variants for faster inference
- **New compute types**: `bfloat16`, `int8_float16`, `int8_bfloat16`
- **Modern packaging**: PyInstaller binary, `.deb`, Arch Linux PKGBUILD, Flatpak
- **CI/CD**: GitHub Actions workflows for automated builds and releases
- **Dependency refresh**: All packages updated; `requirements.txt` replaced with `pyproject.toml`
- **Python 3.10-3.14** supported

## How It Works

Once started, WhisperWriter runs in the background and waits for a keyboard shortcut (`ctrl+shift+space` by default). When the shortcut is pressed, the app starts recording from your microphone. There are four recording modes:

- **continuous** (default): Transcribes after a pause in speech, then automatically starts recording again. Press the shortcut again to stop.
- **voice_activity_detection**: Transcribes after a pause in speech. Press the shortcut to start a new recording.
- **press_to_toggle**: Records until the shortcut is pressed again.
- **hold_to_record**: Records while the shortcut is held down.

Transcription can run **locally** via [faster-whisper](https://github.com/SYSTRAN/faster-whisper/) or through the [OpenAI API](https://platform.openai.com/docs/guides/speech-to-text). Local mode is the default.

## Available Models

| Model | Parameters | English-only | Speed | Notes |
|-------|-----------|:------------:|-------|-------|
| `tiny` / `tiny.en` | 39M | .en variant | Fastest | Good for quick drafts |
| `base` / `base.en` | 74M | .en variant | Fast | Default; good balance |
| `small` / `small.en` | 244M | .en variant | Moderate | |
| `medium` / `medium.en` | 769M | .en variant | Slow | |
| `large-v1` | 1550M | No | Slowest | Original large model |
| `large-v2` | 1550M | No | Slowest | Improved large |
| `large-v3` | 1550M | No | Slowest | Best accuracy |
| `large-v3-turbo` / `turbo` | 809M | No | Fast | Near large-v3 quality, much faster |
| `distil-small.en` | - | Yes | Fast | Distilled small |
| `distil-medium.en` | - | Yes | Fast | Distilled medium |
| `distil-large-v2` | - | No | Fast | Distilled large-v2 |
| `distil-large-v3` | - | No | Fast | Distilled large-v3 |
| `distil-large-v3.5` | - | No | Fast | Latest distilled model |

## Getting Started

### Prerequisites

- **Python 3.10+**: [python.org/downloads](https://www.python.org/downloads/)
- **Git**: [git-scm.com/downloads](https://git-scm.com/downloads)
- **Linux system packages** (Debian/Ubuntu):
  ```bash
  sudo apt install portaudio19-dev libsndfile1 libxcb-xinerama0 libxkbcommon0
  ```
- **Linux system packages** (Arch/CachyOS):
  ```bash
  sudo pacman -S portaudio libsndfile libxkbcommon
  ```

For audio notification support (`noise_on_completion`), you also need GStreamer and PyGObject:
```bash
# Debian/Ubuntu
sudo apt install python3-gi gstreamer1.0-plugins-base gstreamer1.0-plugins-good

# Arch
sudo pacman -S python-gobject gstreamer gst-plugins-base gst-plugins-good
```

<details>
<summary>GPU acceleration (NVIDIA CUDA)</summary>

To run faster-whisper on your GPU, install the NVIDIA CUDA libraries:

- [cuBLAS for CUDA 12](https://developer.nvidia.com/cublas)
- [cuDNN for CUDA 12](https://developer.nvidia.com/cudnn)

#### Install with pip (Linux)

```bash
pip install nvidia-cublas-cu12 nvidia-cudnn-cu12

export LD_LIBRARY_PATH=$(python3 -c 'import os; import nvidia.cublas.lib; import nvidia.cudnn.lib; print(os.path.dirname(nvidia.cublas.lib.__file__) + ":" + os.path.dirname(nvidia.cudnn.lib.__file__))')
```

#### Download from Purfview's repository (Windows & Linux)

[whisper-standalone-win](https://github.com/Purfview/whisper-standalone-win) provides the required NVIDIA libraries in a [single archive](https://github.com/Purfview/whisper-standalone-win/releases/tag/libs). Extract and place the libraries in a directory on your `PATH`.

#### Docker

The libraries are pre-installed in official NVIDIA CUDA Docker images such as `nvidia/cuda:12.0.0-runtime-ubuntu22.04`.

</details>

### Installation

#### Option A: Pre-built Binary

Download from the [Releases page](https://github.com/xak47d/open-whisper-writer/releases):

```bash
tar xzf whisper-writer-linux-x86_64.tar.gz
cd whisper-writer
./whisper-writer
```

#### Option B: Debian/Ubuntu (.deb)

```bash
sudo apt install ./whisper-writer_1.1.0_amd64.deb
whisper-writer
```

#### Option C: Arch Linux

```bash
# From the PKGBUILD in this repo:
cd packaging/arch
makepkg -si
```

#### Option D: Flatpak

```bash
flatpak install whisper-writer.flatpak
flatpak run io.github.xak47d.whisper-writer
```

#### Option E: From Source

```bash
git clone https://github.com/xak47d/open-whisper-writer
cd open-whisper-writer

python -m venv venv --system-site-packages
source venv/bin/activate

pip install -e .
python run.py
```

> **Note**: `--system-site-packages` is needed so the venv can access system-installed PyGObject (`gi`) for audio notification playback. If you don't use the `noise_on_completion` feature, a regular venv works fine.

For development (includes PyInstaller, pytest, ruff):
```bash
pip install -e ".[dev]"
```

### First Run

On first launch, a Settings window will appear. Configure your preferences and click Save. The main window will open -- press **Start** to activate the keyboard listener. Press your activation key (`ctrl+shift+space` by default) to begin recording.

## Building from Source

```bash
# Install dev dependencies
pip install -e ".[dev]"

# Build standalone binary (PyInstaller)
./scripts/build.sh

# Build .deb package (requires PyInstaller build first)
./scripts/build-deb.sh

# Build Arch package
cd packaging/arch && makepkg -s
```

## Configuration Options

WhisperWriter uses a YAML configuration file. Open the Settings window to configure:

<p align="center">
    <img src="./assets/ww-settings-demo.gif" alt="WhisperWriter Settings window demo gif" width="350" height="350">
</p>

### Model Options

| Option | Default | Description |
|--------|---------|-------------|
| `use_api` | `false` | Use OpenAI API instead of local model |

**Common** (API and local):

| Option | Default | Description |
|--------|---------|-------------|
| `language` | `null` | Language code ([ISO-639-1](https://en.wikipedia.org/wiki/List_of_ISO_639_language_codes)) |
| `temperature` | `0.0` | Transcription randomness (lower = more deterministic) |
| `initial_prompt` | `null` | Prompt to condition the transcription ([guide](https://platform.openai.com/docs/guides/speech-to-text/prompting)) |

**API** ([docs](https://platform.openai.com/docs/api-reference/audio/create?lang=python)):

| Option | Default | Description |
|--------|---------|-------------|
| `model` | `whisper-1` | API model name |
| `base_url` | `https://api.openai.com/v1` | API endpoint (change for [LocalAI](https://localai.io/), etc.) |
| `api_key` | `null` | OpenAI API key (stored in `.env`, not config) |

**Local**:

| Option | Default | Description |
|--------|---------|-------------|
| `model` | `base` | Model name (see [Available Models](#available-models)) |
| `device` | `auto` | `auto`, `cpu`, or `cuda` |
| `compute_type` | `default` | `default`, `float32`, `float16`, `bfloat16`, `int8`, `int8_float16`, `int8_bfloat16` ([quantization docs](https://opennmt.net/CTranslate2/quantization.html)) |
| `condition_on_previous_text` | `true` | Use previous transcription as prompt context |
| `vad_filter` | `false` | Enable Silero VAD to filter silence |
| `model_path` | `null` | Path to a local model directory/file (auto-downloads from HuggingFace if unset) |

### Recording Options

| Option | Default | Description |
|--------|---------|-------------|
| `activation_key` | `ctrl+shift+space` | Keyboard shortcut (separate keys with `+`) |
| `input_backend` | `auto` | Input backend: `auto`, `evdev`, `pynput` |
| `recording_mode` | `continuous` | `continuous`, `voice_activity_detection`, `press_to_toggle`, `hold_to_record` |
| `sound_device` | `null` | Sound device index (run `python -m sounddevice` to list) |
| `sample_rate` | `16000` | Sample rate in Hz |
| `silence_duration` | `900` | Silence threshold in ms before stopping |
| `min_duration` | `100` | Minimum recording length in ms (shorter is discarded) |

### Post-processing Options

| Option | Default | Description |
|--------|---------|-------------|
| `writing_key_press_delay` | `0.005` | Delay in seconds between simulated key presses |
| `remove_trailing_period` | `false` | Remove trailing period from transcription |
| `add_trailing_space` | `true` | Add a space after transcription |
| `remove_capitalization` | `false` | Convert transcription to lowercase |
| `input_method` | `pynput` | Typing method: `pynput`, `ydotool`, `dotool` |

### Miscellaneous Options

| Option | Default | Description |
|--------|---------|-------------|
| `print_to_terminal` | `true` | Print status and transcription to terminal |
| `hide_status_window` | `false` | Hide the recording/transcribing status overlay |
| `noise_on_completion` | `false` | Play a sound when transcription finishes |

## Project Structure

```
open-whisper-writer/
├── run.py                  # Entry point
├── pyproject.toml          # Package metadata and dependencies
├── src/
│   ├── main.py             # WhisperWriterApp (QApplication)
│   ├── transcription.py    # Local and API transcription
│   ├── result_thread.py    # Recording + transcription thread
│   ├── key_listener.py     # Keyboard input (evdev/pynput backends)
│   ├── input_simulation.py # Typing simulation (pynput/ydotool/dotool)
│   ├── utils.py            # ConfigManager (YAML-based)
│   ├── config_schema.yaml  # Configuration schema with defaults
│   └── ui/
│       ├── base_window.py      # Frameless window base class
│       ├── main_window.py      # Start/Settings window
│       ├── settings_window.py  # Tabbed settings editor
│       └── status_window.py    # Recording/transcribing overlay
├── assets/                 # Icons, sounds, demo images
├── scripts/
│   ├── build.sh            # PyInstaller build
│   └── build-deb.sh        # .deb package build
├── packaging/
│   ├── arch/PKGBUILD
│   └── flatpak/
├── .github/workflows/
│   ├── build.yml           # CI: build on push/PR
│   └── release.yml         # CD: release on tag
├── whisper-writer.desktop  # FreeDesktop entry
└── whisper-writer.spec     # PyInstaller spec
```

## Known Issues

See the [Issue Tracker](https://github.com/xak47d/open-whisper-writer/issues). If you encounter a problem, please [open a new issue](https://github.com/xak47d/open-whisper-writer/issues/new).

## Roadmap

- [x] Restructured configuration options
- [x] Updated OpenAI API usage
- [x] PyQt5 GUI
- [x] Standalone binary packaging
- [x] Linux packaging (.deb, PKGBUILD, Flatpak)
- [x] Updated model support (large-v3-turbo, distil variants)
- [x] CI/CD with GitHub Actions
- [ ] Post-processing: simple word replacement (e.g. "gonna" -> "going to")
- [ ] Post-processing: GPT-based instructional post-processing
- [ ] Audio file pipelining

See the [CHANGELOG](CHANGELOG.md) for version history.

## Contributing

Contributions are welcome. Feel free to [open a pull request](https://github.com/xak47d/open-whisper-writer/pulls) or [create an issue](https://github.com/xak47d/open-whisper-writer/issues/new).

## Credits

- [savbell](https://github.com/savbell) for creating the original [whisper-writer](https://github.com/savbell/whisper-writer) project
- [OpenAI](https://openai.com/) for the Whisper model and API
- [Guillaume Klein](https://github.com/guillaumekln) and the [faster-whisper](https://github.com/SYSTRAN/faster-whisper) team
- All [contributors](https://github.com/xak47d/open-whisper-writer/graphs/contributors)

## License

This project is licensed under the GNU General Public License v3.0. See the [LICENSE](LICENSE) file for details.
