import os
import sys
import time

# Ensure the src/ directory is on sys.path so bare imports work both when
# running directly (python src/main.py) and when installed as a package
# (entry point "src.main:main").  This must happen before any bare imports.
_src_dir = os.path.dirname(os.path.abspath(__file__))
if _src_dir not in sys.path:
    sys.path.insert(0, _src_dir)

from audioplayer import AudioPlayer
from pynput.keyboard import Controller
from PyQt5.QtCore import QObject, QProcess
from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import QApplication, QSystemTrayIcon, QMenu, QAction, QMessageBox

from key_listener import KeyListener
from result_thread import ResultThread
from ui.main_window import MainWindow
from ui.settings_window import SettingsWindow
from ui.status_window import StatusWindow
from transcription import create_local_model
from input_simulation import InputSimulator
from utils import ConfigManager


class WhisperWriterApp(QObject):
    def __init__(self):
        """
        Initialize the application, opening settings window if no configuration file is found.
        """
        super().__init__()
        self.app = QApplication(sys.argv)
        self.app.setApplicationName('WhisperWriter')
        # Set desktop filename so KDE Wayland can associate the tray icon with
        # the .desktop file and look up the icon from the hicolor theme.
        self.app.setDesktopFileName('whisper-writer')
        # Prefer theme icon (installed to ~/.local/share/icons/hicolor/) for
        # reliable StatusNotifierItem rendering on KDE Wayland; fall back to
        # the bundled asset if the theme icon isn't installed.
        _fallback_icon = QIcon(os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            'assets', 'ww-logo.png'))
        _app_icon = QIcon.fromTheme('whisper-writer', _fallback_icon)
        self.app.setWindowIcon(_app_icon)

        ConfigManager.initialize()

        self.settings_window = SettingsWindow()
        self.settings_window.settings_closed.connect(self.on_settings_closed)
        self.settings_window.settings_saved.connect(self.restart_app)

        if ConfigManager.config_file_exists():
            self.initialize_components()
        else:
            print('No valid configuration file found. Opening settings window...')
            self.settings_window.show()

    def initialize_components(self):
        """
        Initialize the components of the application.
        """
        self.input_simulator = InputSimulator()

        self.key_listener = KeyListener()
        self.key_listener.add_callback("on_activate", self.on_activation)
        self.key_listener.add_callback("on_deactivate", self.on_deactivation)

        model_options = ConfigManager.get_config_section('model_options')
        self.local_model = create_local_model() if not model_options.get('use_api') else None

        self.result_thread = None

        self.main_window = MainWindow()
        self.main_window.openSettings.connect(self.settings_window.show)
        self.main_window.startListening.connect(self.key_listener.start)
        self.main_window.closeApp.connect(self.exit_app)

        # Status bubble (unless hidden)
        self.status_window = None
        if not ConfigManager.get_config_value('misc', 'hide_status_window'):
            self.status_window = StatusWindow()

        self.create_tray_icon()
        self.main_window.show()

    def create_tray_icon(self):
        """
        Create the system tray icon and its context menu with state indicators
        and quick toggles.
        """
        _fallback_icon = QIcon(os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            'assets', 'ww-logo.png'))
        _tray_icon_q = QIcon.fromTheme('whisper-writer', _fallback_icon)
        self.tray_icon = QSystemTrayIcon(_tray_icon_q, self)

        tray_menu = QMenu()

        # --- Status header ---
        self._tray_status_action = QAction('Status: Idle', tray_menu)
        self._tray_status_action.setEnabled(False)
        tray_menu.addAction(self._tray_status_action)

        tray_menu.addSeparator()

        # --- Provider info ---
        provider_label = self._get_provider_label()
        self._tray_provider_action = QAction(provider_label, tray_menu)
        self._tray_provider_action.setEnabled(False)
        tray_menu.addAction(self._tray_provider_action)

        tray_menu.addSeparator()

        # --- Quick toggles ---
        # Output mode toggle
        output_mode = ConfigManager.get_config_value('post_processing', 'output_mode') or 'type'
        self._output_mode_menu = QMenu('Output Mode', tray_menu)
        self._output_mode_actions = {}
        for mode in ('type', 'clipboard', 'type_and_clipboard'):
            action = QAction(mode.replace('_', ' ').title(), self._output_mode_menu)
            action.setCheckable(True)
            action.setChecked(mode == output_mode)
            action.triggered.connect(lambda checked, m=mode: self._set_output_mode(m))
            self._output_mode_menu.addAction(action)
            self._output_mode_actions[mode] = action
        tray_menu.addMenu(self._output_mode_menu)

        # LLM processing toggle
        llm_enabled = ConfigManager.get_config_value('llm_processing', 'enabled') or False
        self._llm_toggle_action = QAction('LLM Processing', tray_menu)
        self._llm_toggle_action.setCheckable(True)
        self._llm_toggle_action.setChecked(llm_enabled)
        self._llm_toggle_action.triggered.connect(self._toggle_llm_processing)
        tray_menu.addAction(self._llm_toggle_action)

        # LLM mode submenu
        llm_mode = ConfigManager.get_config_value('llm_processing', 'mode') or 'clean_up'
        self._llm_mode_menu = QMenu('LLM Mode', tray_menu)
        self._llm_mode_actions = {}
        for mode in ('clean_up', 'formal', 'translate', 'custom'):
            action = QAction(mode.replace('_', ' ').title(), self._llm_mode_menu)
            action.setCheckable(True)
            action.setChecked(mode == llm_mode)
            action.triggered.connect(lambda checked, m=mode: self._set_llm_mode(m))
            self._llm_mode_menu.addAction(action)
            self._llm_mode_actions[mode] = action
        tray_menu.addMenu(self._llm_mode_menu)

        tray_menu.addSeparator()

        # --- Standard actions ---
        show_action = QAction('WhisperWriter Main Menu', tray_menu)
        show_action.triggered.connect(self.main_window.show)
        tray_menu.addAction(show_action)

        settings_action = QAction('Open Settings', tray_menu)
        settings_action.triggered.connect(self.settings_window.show)
        tray_menu.addAction(settings_action)

        exit_action = QAction('Exit', tray_menu)
        exit_action.triggered.connect(self.exit_app)
        tray_menu.addAction(exit_action)

        self.tray_icon.setContextMenu(tray_menu)
        self._update_tray_tooltip()
        self.tray_icon.show()

    def _get_provider_label(self):
        """Build a label showing the current transcription provider + model."""
        use_api = ConfigManager.get_config_value('model_options', 'use_api')
        if use_api:
            provider = ConfigManager.get_config_value('model_options', 'api', 'provider') or 'openai'
            model_field = f'{provider}_model'
            model = ConfigManager.get_config_value('model_options', 'api', model_field) or '?'
            return f'Provider: {provider.title()} / {model}'
        else:
            local_opts = ConfigManager.get_config_section('model_options').get('local', {})
            model = local_opts.get('model_path') or local_opts.get('model') or 'base'
            return f'Provider: Local / {model}'

    def _update_tray_tooltip(self):
        """Update the tray icon tooltip with current config info."""
        provider_label = self._get_provider_label()
        output_mode = ConfigManager.get_config_value('post_processing', 'output_mode') or 'type'
        llm_enabled = ConfigManager.get_config_value('llm_processing', 'enabled') or False
        llm_mode = ConfigManager.get_config_value('llm_processing', 'mode') or 'clean_up'

        tooltip_lines = [
            'WhisperWriter',
            provider_label,
            f'Output: {output_mode.replace("_", " ").title()}',
        ]
        if llm_enabled:
            tooltip_lines.append(f'LLM: {llm_mode.replace("_", " ").title()}')
        self.tray_icon.setToolTip('\n'.join(tooltip_lines))

    def _update_tray_status(self, status):
        """Update the status line in the tray menu."""
        status_map = {
            'idle': 'Idle',
            'recording': 'Recording...',
            'transcribing': 'Transcribing...',
            'processing': 'LLM Processing...',
            'done': 'Done',
            'error': 'Error',
        }
        label = status_map.get(status, status.title())
        if hasattr(self, '_tray_status_action'):
            self._tray_status_action.setText(f'Status: {label}')

    def _set_output_mode(self, mode):
        """Quick-toggle output mode from tray."""
        ConfigManager.set_config_value(mode, 'post_processing', 'output_mode')
        ConfigManager.save_config()
        for m, action in self._output_mode_actions.items():
            action.setChecked(m == mode)
        self._update_tray_tooltip()
        ConfigManager.console_print(f'Output mode changed to: {mode}')

    def _toggle_llm_processing(self, checked):
        """Quick-toggle LLM processing from tray."""
        ConfigManager.set_config_value(checked, 'llm_processing', 'enabled')
        ConfigManager.save_config()
        self._update_tray_tooltip()
        ConfigManager.console_print(f'LLM processing {"enabled" if checked else "disabled"}')

    def _set_llm_mode(self, mode):
        """Quick-toggle LLM mode from tray."""
        ConfigManager.set_config_value(mode, 'llm_processing', 'mode')
        ConfigManager.save_config()
        for m, action in self._llm_mode_actions.items():
            action.setChecked(m == mode)
        self._update_tray_tooltip()
        ConfigManager.console_print(f'LLM mode changed to: {mode}')

    def cleanup(self):
        if self.key_listener:
            self.key_listener.stop()
        if self.input_simulator:
            self.input_simulator.cleanup()

    def exit_app(self):
        """
        Exit the application.
        """
        self.cleanup()
        QApplication.quit()

    def restart_app(self):
        """Restart the application to apply the new settings."""
        self.cleanup()
        QApplication.quit()
        QProcess.startDetached(sys.executable, sys.argv)

    def on_settings_closed(self):
        """
        If settings is closed without saving on first run, initialize the components with default values.
        """
        if not os.path.exists(os.path.join('src', 'config.yaml')):
            QMessageBox.information(
                self.settings_window,
                'Using Default Values',
                'Settings closed without saving. Default values are being used.'
            )
            self.initialize_components()

    def on_activation(self):
        """
        Called when the activation key combination is pressed.
        """
        if self.result_thread and self.result_thread.isRunning():
            recording_mode = ConfigManager.get_config_value('recording_options', 'recording_mode')
            if recording_mode == 'press_to_toggle':
                self.result_thread.stop_recording()
            elif recording_mode == 'continuous':
                self.stop_result_thread()
            return

        self.start_result_thread()

    def on_deactivation(self):
        """
        Called when the activation key combination is released.
        """
        if ConfigManager.get_config_value('recording_options', 'recording_mode') == 'hold_to_record':
            if self.result_thread and self.result_thread.isRunning():
                self.result_thread.stop_recording()

    def start_result_thread(self):
        """
        Start the result thread to record audio and transcribe it.
        """
        if self.result_thread and self.result_thread.isRunning():
            return

        self.result_thread = ResultThread(self.local_model)

        # Connect status signal to bubble + tray
        self.result_thread.statusSignal.connect(self._update_tray_status)
        if self.status_window:
            self.result_thread.statusSignal.connect(self.status_window.updateStatus)
            self.result_thread.audioLevelSignal.connect(self.status_window._on_audio_level)
            self.status_window.closeSignal.connect(self.stop_result_thread)

        self.result_thread.resultSignal.connect(self.on_transcription_complete)
        self.result_thread.start()

    def stop_result_thread(self):
        """
        Stop the result thread.
        """
        if self.result_thread and self.result_thread.isRunning():
            self.result_thread.stop()

    def on_transcription_complete(self, result):
        """
        When the transcription is complete, output the result using the configured
        output mode and start listening for the activation key again.
        """
        # Use the new output() method which respects output_mode config
        self.input_simulator.output(result)

        if ConfigManager.get_config_value('misc', 'noise_on_completion'):
            AudioPlayer(os.path.join('assets', 'beep.wav')).play(block=True)

        if ConfigManager.get_config_value('recording_options', 'recording_mode') == 'continuous':
            self.start_result_thread()
        else:
            self.key_listener.start()

    def run(self):
        """
        Start the application.
        """
        sys.exit(self.app.exec_())


def main():
    """Entry point for the whisper-writer console_scripts command."""
    # Ensure working directory is the project root so relative asset paths resolve
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    os.chdir(project_root)
    app = WhisperWriterApp()
    app.run()


if __name__ == '__main__':
    main()
