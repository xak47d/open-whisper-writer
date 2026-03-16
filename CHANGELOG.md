# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

## [Unreleased]

## [1.1.0] - 2026-03-15

### Added
- New models: `large-v3-turbo`, `turbo`, `distil-small.en`, `distil-medium.en`, `distil-large-v2`, `distil-large-v3`, `distil-large-v3.5`.
- New compute types: `bfloat16`, `int8_float16`, `int8_bfloat16`.
- `pyproject.toml` with modern Python packaging (replaces `requirements.txt`).
- PyInstaller spec and build script for standalone binary packaging.
- `.deb` package build script for Debian/Ubuntu.
- Arch Linux PKGBUILD.
- Flatpak manifest and launcher.
- GitHub Actions CI/CD workflows (build on push/PR, release on tag).
- FreeDesktop `.desktop` entry and AppStream metadata.
- Model browser in settings now supports directory selection for CTranslate2 models.
- Settings window now supports `.pt` model files in addition to `.bin`.

### Changed
- Replaced `requirements.txt` with `pyproject.toml`.
- Updated all dependencies to latest compatible versions.
- Upgraded `faster-whisper` from 1.0.2 to >=1.2.1.
- Improved model loading with better compute type handling and graceful CPU fallback for GPU-only quantization types.
- Python 3.10 through 3.14 now supported.
- Reorganised models in config schema (sorted by size: tiny -> distil-large-v3.5).
- Updated README with fork context, installation options, available models table, system dependency documentation, and project structure.
- Issue tracker and contribution links now point to the fork repository.

### Fixed
- CPU fallback now correctly downgrades `int8_float16`/`int8_bfloat16` to `int8` when CUDA is unavailable.

## [1.0.1-fork] - 2026-03-15

### Changed
- Forked from [savbell/whisper-writer](https://github.com/savbell/whisper-writer).
- New settings window to configure WhisperWriter.
- New main window to either start the keyboard listener or open the settings window.
- New continuous recording mode.
- Option to play a sound when transcription finishes.
- Migrated status window from `tkinter` to `PyQt5`.
- Migrated from JSON to YAML for configuration.
- Upgraded to latest versions of `openai` and `faster-whisper`, including support for local API.
- Rewritten `KeyListener` with `evdev` backend support.
- No longer using `keyboard` package to listen for key presses.

## [1.0.1] - 2024-01-28
### Added
- New message to identify whether Whisper was being called using the API or running locally.
- Additional hold-to-talk ([PR #28](https://github.com/savbell/whisper-writer/pull/28)) and press-to-toggle recording methods ([Issue #21](https://github.com/savbell/whisper-writer/issues/21)).
- New configuration options to:
  - Choose recording method (defaulting to voice activity detection).
  - Choose which sound device and sample rate to use.
  - Hide the status window ([PR #28](https://github.com/savbell/whisper-writer/pull/28)).

### Changed
- Migrated from `whisper` to `faster-whisper` ([Issue #11](https://github.com/savbell/whisper-writer/issues/11)).
- Migrated from `pyautogui` to `pynput` ([PR #10](https://github.com/savbell/whisper-writer/pull/10)).
- Migrated from `webrtcvad` to `webrtcvad-wheels` ([PR #17](https://github.com/savbell/whisper-writer/pull/17)).
- Changed default activation key combo from `ctrl+alt+space` to `ctrl+shift+space`.
- Changed to using a local model rather than the API by default.
- Revamped README.md, including new Roadmap, Contributing, and Credits sections.

### Fixed
- Local model is now only loaded once at start-up, rather than every time the activation key combo was pressed.
- Default configuration now auto-chooses compute type for the local model to avoid warnings.
- Graceful degradation to CPU if CUDA isn't available ([PR #30](https://github.com/savbell/whisper-writer/pull/30)).
- Removed long prefix of spaces in transcription ([PR #19](https://github.com/savbell/whisper-writer/pull/19)).

## [1.0.0] - 2023-05-29
### Added
- Initial release of WhisperWriter.
- Added CHANGELOG.md.
- Added Versioning and Known Issues to README.md.

### Changed
- Updated Whisper Python package; the local model is now compatible with Python 3.11.

[Unreleased]: https://github.com/xak47d/open-whisper-writer/compare/v1.1.0...HEAD
[1.1.0]: https://github.com/xak47d/open-whisper-writer/releases/tag/v1.1.0
[1.0.1-fork]: https://github.com/xak47d/open-whisper-writer/compare/v1.0.1...v1.0.1-fork
[1.0.1]: https://github.com/savbell/whisper-writer/releases/tag/v1.0.1
[1.0.0]: https://github.com/savbell/whisper-writer/releases/tag/v1.0.0
