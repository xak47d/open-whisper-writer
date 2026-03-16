"""Modernized settings window for WhisperWriter.

Restructured tabs: Transcription, Recording, Processing, Output, General.
Dynamic show/hide of provider-specific fields when provider dropdowns change.
Multi-provider API key storage in .env file.
Theme-aware styling via the shared theme module.
"""

import os
import sys
from dotenv import set_key, load_dotenv
from PyQt5.QtWidgets import (
    QApplication, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton,
    QComboBox, QCheckBox, QMessageBox, QTabWidget, QWidget, QSizePolicy,
    QSpacerItem, QToolButton, QStyle, QFileDialog, QScrollArea, QGroupBox,
    QTextEdit, QFrame
)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QFont

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from ui.base_window import BaseWindow
from ui.theme import settings_window_qss
from utils import ConfigManager

load_dotenv()


# ---------------------------------------------------------------------------
# Env-key mapping for API keys
# ---------------------------------------------------------------------------

API_KEY_ENV_MAP = {
    # schema path -> env var name
    ('model_options', 'api', 'openai_api_key'): 'OPENAI_API_KEY',
    ('model_options', 'api', 'groq_api_key'): 'GROQ_API_KEY',
    ('model_options', 'api', 'deepgram_api_key'): 'DEEPGRAM_API_KEY',
    ('llm_processing', 'api_key'): 'LLM_API_KEY',
}

# Which provider fields to show for each transcription provider
TRANSCRIPTION_PROVIDER_FIELDS = {
    'openai': ['openai_api_key', 'openai_model', 'openai_base_url'],
    'groq': ['groq_api_key', 'groq_model'],
    'deepgram': ['deepgram_api_key', 'deepgram_model'],
}

# All API fields that can be toggled
ALL_API_FIELDS = set()
for fields in TRANSCRIPTION_PROVIDER_FIELDS.values():
    ALL_API_FIELDS.update(fields)

# Which LLM fields to show for each LLM provider
LLM_PROVIDER_FIELDS = {
    'openai': ['api_key', 'base_url', 'model'],
    'anthropic': ['api_key', 'model'],
    'ollama': ['base_url', 'model'],
}


class SettingsWindow(BaseWindow):
    settings_closed = pyqtSignal()
    settings_saved = pyqtSignal()

    def __init__(self):
        """Initialize the settings window."""
        super().__init__('Settings', 750, 750)
        self.schema = ConfigManager.get_schema()
        self._widgets = {}  # key: (category, [sub_category,] key) -> widget
        self._rows = {}     # key: same tuple -> row QWidget (for show/hide)
        self.init_settings_ui()

    def init_settings_ui(self):
        """Initialize the settings user interface."""
        self.setStyleSheet(settings_window_qss())

        self.tabs = QTabWidget()
        self.main_layout.addWidget(self.tabs)

        self._build_transcription_tab()
        self._build_recording_tab()
        self._build_processing_tab()
        self._build_output_tab()
        self._build_general_tab()

        self._create_buttons()

        # Set initial visibility
        self._on_use_api_changed()
        self._on_transcription_provider_changed()
        self._on_llm_provider_changed()
        self._on_llm_enabled_changed()

    # ===================================================================
    # Tab builders
    # ===================================================================

    def _build_transcription_tab(self):
        """Build the Transcription tab: use_api toggle, common options, provider-specific API fields, local fields."""
        tab = self._make_scrollable_tab('Transcription')

        # --- API / Local toggle ---
        self._add_schema_row(tab, 'model_options', None, 'use_api')

        # --- Common transcription settings ---
        group = QGroupBox('Common Settings')
        group_layout = QVBoxLayout()
        group.setLayout(group_layout)
        for key in ('language', 'temperature', 'initial_prompt'):
            self._add_schema_row(group_layout, 'model_options', 'common', key)
        tab.addWidget(group)

        # --- API provider settings ---
        self._api_group = QGroupBox('Cloud API Settings')
        api_layout = QVBoxLayout()
        self._api_group.setLayout(api_layout)

        self._add_schema_row(api_layout, 'model_options', 'api', 'provider')
        for key in ('openai_api_key', 'openai_model', 'openai_base_url',
                     'groq_api_key', 'groq_model',
                     'deepgram_api_key', 'deepgram_model'):
            self._add_schema_row(api_layout, 'model_options', 'api', key)

        tab.addWidget(self._api_group)

        # --- Local model settings ---
        self._local_group = QGroupBox('Local Model Settings')
        local_layout = QVBoxLayout()
        self._local_group.setLayout(local_layout)
        for key in ('model', 'device', 'compute_type', 'condition_on_previous_text',
                     'vad_filter', 'model_path'):
            self._add_schema_row(local_layout, 'model_options', 'local', key)
        tab.addWidget(self._local_group)

        tab.addSpacerItem(QSpacerItem(20, 40, QSizePolicy.Minimum, QSizePolicy.Expanding))

        # --- Connect dynamic toggles ---
        use_api_widget = self._widgets.get(('model_options', 'use_api'))
        if use_api_widget:
            use_api_widget.stateChanged.connect(lambda: self._on_use_api_changed())

        provider_widget = self._widgets.get(('model_options', 'api', 'provider'))
        if provider_widget:
            provider_widget.currentTextChanged.connect(lambda: self._on_transcription_provider_changed())

    def _build_recording_tab(self):
        """Build the Recording tab."""
        tab = self._make_scrollable_tab('Recording')
        for key in ('activation_key', 'input_backend', 'recording_mode',
                     'sound_device', 'sample_rate', 'silence_duration', 'min_duration'):
            self._add_schema_row(tab, 'recording_options', None, key)
        tab.addSpacerItem(QSpacerItem(20, 40, QSizePolicy.Minimum, QSizePolicy.Expanding))

    def _build_processing_tab(self):
        """Build the Processing tab: LLM post-processing settings."""
        tab = self._make_scrollable_tab('LLM Processing')

        self._add_schema_row(tab, 'llm_processing', None, 'enabled')

        self._llm_settings_group = QGroupBox('LLM Settings')
        llm_layout = QVBoxLayout()
        self._llm_settings_group.setLayout(llm_layout)

        for key in ('provider', 'model', 'api_key', 'base_url', 'mode',
                     'target_language', 'custom_prompt'):
            self._add_schema_row(llm_layout, 'llm_processing', None, key)
        tab.addWidget(self._llm_settings_group)

        tab.addSpacerItem(QSpacerItem(20, 40, QSizePolicy.Minimum, QSizePolicy.Expanding))

        # Connect dynamic toggles
        llm_enabled_widget = self._widgets.get(('llm_processing', 'enabled'))
        if llm_enabled_widget:
            llm_enabled_widget.stateChanged.connect(lambda: self._on_llm_enabled_changed())

        llm_provider_widget = self._widgets.get(('llm_processing', 'provider'))
        if llm_provider_widget:
            llm_provider_widget.currentTextChanged.connect(lambda: self._on_llm_provider_changed())

        llm_mode_widget = self._widgets.get(('llm_processing', 'mode'))
        if llm_mode_widget:
            llm_mode_widget.currentTextChanged.connect(lambda: self._on_llm_mode_changed())

    def _build_output_tab(self):
        """Build the Output tab: output mode + text post-processing."""
        tab = self._make_scrollable_tab('Output')

        group = QGroupBox('Output Mode')
        group_layout = QVBoxLayout()
        group.setLayout(group_layout)
        self._add_schema_row(group_layout, 'post_processing', None, 'output_mode')
        tab.addWidget(group)

        group2 = QGroupBox('Text Post-Processing')
        group2_layout = QVBoxLayout()
        group2.setLayout(group2_layout)
        for key in ('remove_trailing_period', 'add_trailing_space', 'remove_capitalization'):
            self._add_schema_row(group2_layout, 'post_processing', None, key)
        tab.addWidget(group2)

        group3 = QGroupBox('Input Simulation')
        group3_layout = QVBoxLayout()
        group3.setLayout(group3_layout)
        for key in ('input_method', 'writing_key_press_delay'):
            self._add_schema_row(group3_layout, 'post_processing', None, key)
        tab.addWidget(group3)

        tab.addSpacerItem(QSpacerItem(20, 40, QSizePolicy.Minimum, QSizePolicy.Expanding))

    def _build_general_tab(self):
        """Build the General tab: misc settings."""
        tab = self._make_scrollable_tab('General')
        for key in ('print_to_terminal', 'hide_status_window', 'noise_on_completion'):
            self._add_schema_row(tab, 'misc', None, key)
        tab.addSpacerItem(QSpacerItem(20, 40, QSizePolicy.Minimum, QSizePolicy.Expanding))

    # ===================================================================
    # Dynamic visibility
    # ===================================================================

    def _on_use_api_changed(self):
        """Show/hide API vs local model groups."""
        use_api_widget = self._widgets.get(('model_options', 'use_api'))
        use_api = use_api_widget.isChecked() if use_api_widget else False
        self._api_group.setVisible(use_api)
        self._local_group.setVisible(not use_api)

    def _on_transcription_provider_changed(self):
        """Show/hide per-provider API fields."""
        provider_widget = self._widgets.get(('model_options', 'api', 'provider'))
        provider = provider_widget.currentText() if provider_widget else 'openai'
        visible_fields = set(TRANSCRIPTION_PROVIDER_FIELDS.get(provider, []))

        for field in ALL_API_FIELDS:
            row_key = ('model_options', 'api', field)
            row = self._rows.get(row_key)
            if row:
                row.setVisible(field in visible_fields)

    def _on_llm_enabled_changed(self):
        """Show/hide LLM settings group."""
        enabled_widget = self._widgets.get(('llm_processing', 'enabled'))
        enabled = enabled_widget.isChecked() if enabled_widget else False
        self._llm_settings_group.setVisible(enabled)

    def _on_llm_provider_changed(self):
        """Show/hide per-provider LLM fields."""
        provider_widget = self._widgets.get(('llm_processing', 'provider'))
        provider = provider_widget.currentText() if provider_widget else 'openai'
        visible_fields = set(LLM_PROVIDER_FIELDS.get(provider, []))

        for field in ('api_key', 'base_url', 'model'):
            row_key = ('llm_processing', field)
            row = self._rows.get(row_key)
            if row:
                row.setVisible(field in visible_fields)

    def _on_llm_mode_changed(self):
        """Show/hide translate/custom fields based on LLM mode."""
        mode_widget = self._widgets.get(('llm_processing', 'mode'))
        mode = mode_widget.currentText() if mode_widget else 'clean_up'

        lang_row = self._rows.get(('llm_processing', 'target_language'))
        if lang_row:
            lang_row.setVisible(mode == 'translate')

        custom_row = self._rows.get(('llm_processing', 'custom_prompt'))
        if custom_row:
            custom_row.setVisible(mode == 'custom')

    # ===================================================================
    # Widget factory
    # ===================================================================

    def _make_scrollable_tab(self, title):
        """Create a scrollable tab and return its inner layout."""
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        container = QWidget()
        layout = QVBoxLayout()
        layout.setContentsMargins(8, 8, 8, 8)
        container.setLayout(layout)
        scroll.setWidget(container)
        self.tabs.addTab(scroll, title)
        return layout

    def _add_schema_row(self, layout, category, sub_category, key):
        """Add a single setting row (label + widget + help) from the schema."""
        meta = self._get_meta(category, sub_category, key)
        if meta is None:
            return

        # Row container
        row_widget = QWidget()
        row_layout = QHBoxLayout()
        row_layout.setContentsMargins(0, 2, 0, 2)
        row_widget.setLayout(row_layout)

        # Label
        label_text = key.replace('_', ' ').replace('api key', 'API key').capitalize()
        label = QLabel(f'{label_text}:')
        label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        label.setMinimumWidth(180)

        # Input widget
        widget = self._create_input_widget(category, sub_category, key, meta)
        if not widget:
            return

        # Help button
        help_btn = QToolButton()
        help_btn.setIcon(self.style().standardIcon(QStyle.SP_MessageBoxQuestion))
        help_btn.setAutoRaise(True)
        help_btn.setToolTip(meta.get('description', ''))
        help_btn.setCursor(Qt.PointingHandCursor)
        desc = meta.get('description', '')
        help_btn.clicked.connect(lambda _, d=desc: QMessageBox.information(self, 'Info', d))

        row_layout.addWidget(label)
        row_layout.addWidget(widget, 1)
        row_layout.addWidget(help_btn)

        if isinstance(layout, QVBoxLayout):
            layout.addWidget(row_widget)
        else:
            layout.addWidget(row_widget)

        # Store references
        widget_key = (category, sub_category, key) if sub_category else (category, key)
        self._widgets[widget_key] = widget
        self._rows[widget_key] = row_widget

    def _create_input_widget(self, category, sub_category, key, meta):
        """Create the appropriate input widget based on meta type."""
        meta_type = meta.get('type')
        current_value = self._get_current_value(category, sub_category, key, meta)

        if meta_type == 'bool':
            widget = QCheckBox()
            widget.setChecked(bool(current_value))
            return widget

        if meta_type == 'str' and 'options' in meta:
            widget = QComboBox()
            widget.addItems(meta['options'])
            if current_value:
                widget.setCurrentText(str(current_value))
            return widget

        if meta_type == 'str':
            # Special case: API keys -> password mode, load from env
            is_api_key = 'api_key' in key
            # Special case: custom_prompt -> multi-line
            is_multiline = key == 'custom_prompt'

            if is_multiline:
                widget = QTextEdit()
                widget.setMaximumHeight(80)
                widget.setPlainText(str(current_value) if current_value else '')
                return widget

            widget = QLineEdit()
            if is_api_key:
                widget.setEchoMode(QLineEdit.Password)
                # Try to load from env
                env_var = self._env_var_for(category, sub_category, key)
                env_val = os.getenv(env_var) if env_var else None
                widget.setText(env_val or (str(current_value) if current_value else ''))
            elif key == 'model_path':
                container = QWidget()
                container_layout = QHBoxLayout()
                container_layout.setContentsMargins(0, 0, 0, 0)
                container.setLayout(container_layout)
                line_edit = QLineEdit(str(current_value) if current_value else '')
                browse_btn = QPushButton('Browse')
                browse_btn.clicked.connect(lambda _, le=line_edit: self._browse_model_path(le))
                container_layout.addWidget(line_edit, 1)
                container_layout.addWidget(browse_btn)
                # Store the line_edit as the actual value widget
                container._value_widget = line_edit
                return container
            else:
                widget.setText(str(current_value) if current_value else '')
            return widget

        if meta_type in ('int', 'float'):
            widget = QLineEdit()
            widget.setText(str(current_value) if current_value is not None else '')
            return widget

        return None

    def _get_meta(self, category, sub_category, key):
        """Get the schema metadata for a setting."""
        schema = self.schema
        if category not in schema:
            return None
        cat = schema[category]
        if sub_category:
            if sub_category not in cat:
                return None
            sub = cat[sub_category]
            return sub.get(key)
        else:
            item = cat.get(key)
            if isinstance(item, dict) and 'value' in item:
                return item
            return None

    def _get_current_value(self, category, sub_category, key, meta):
        """Get the current config value, falling back to schema default."""
        if sub_category:
            val = ConfigManager.get_config_value(category, sub_category, key)
        else:
            val = ConfigManager.get_config_value(category, key)
        if val is None:
            val = meta.get('value')
        return val

    def _env_var_for(self, category, sub_category, key):
        """Return the environment variable name for a given API key field, or None."""
        if sub_category:
            config_path = (category, sub_category, key)
        else:
            config_path = (category, key)
        return API_KEY_ENV_MAP.get(config_path)

    # ===================================================================
    # Buttons
    # ===================================================================

    def _create_buttons(self):
        """Create reset and save buttons."""
        btn_layout = QHBoxLayout()

        reset_button = QPushButton('Reset to Saved')
        reset_button.clicked.connect(self._reset_settings)
        btn_layout.addWidget(reset_button)

        save_button = QPushButton('Save && Restart')
        save_button.setObjectName('save_button')
        save_button.clicked.connect(self._save_settings)
        btn_layout.addWidget(save_button)

        self.main_layout.addLayout(btn_layout)

    # ===================================================================
    # Save / Reset
    # ===================================================================

    def _save_settings(self):
        """Save all settings to config + .env."""
        # Iterate all registered widgets and write values to ConfigManager
        for widget_key, widget in self._widgets.items():
            meta = self._get_meta_from_key(widget_key)
            if meta is None:
                continue
            value = self._get_widget_value(widget, meta.get('type'))

            # Write API keys to .env, not config
            env_var = API_KEY_ENV_MAP.get(widget_key)
            if env_var:
                key_value = value or ''
                set_key('.env', env_var, key_value)
                os.environ[env_var] = key_value
                # Store None in config so the key isn't in the YAML
                self._set_config_from_key(widget_key, None)
            else:
                self._set_config_from_key(widget_key, value)

        ConfigManager.save_config()
        QMessageBox.information(self, 'Settings Saved',
                                'Settings saved. The application will now restart.')
        self.settings_saved.emit()
        self.close()

    def _reset_settings(self):
        """Reset all widgets to saved config values."""
        ConfigManager.reload_config()
        for widget_key, widget in self._widgets.items():
            meta = self._get_meta_from_key(widget_key)
            if meta is None:
                continue
            if len(widget_key) == 3:
                val = ConfigManager.get_config_value(*widget_key)
            else:
                val = ConfigManager.get_config_value(*widget_key)
            if val is None:
                val = meta.get('value')
            self._set_widget_value(widget, val, meta.get('type'))

        # Re-run visibility toggles
        self._on_use_api_changed()
        self._on_transcription_provider_changed()
        self._on_llm_enabled_changed()
        self._on_llm_provider_changed()
        self._on_llm_mode_changed()

    # ===================================================================
    # Helpers
    # ===================================================================

    def _get_meta_from_key(self, widget_key):
        """Look up schema metadata from a widget key tuple."""
        if len(widget_key) == 3:
            return self._get_meta(widget_key[0], widget_key[1], widget_key[2])
        elif len(widget_key) == 2:
            return self._get_meta(widget_key[0], None, widget_key[1])
        return None

    def _set_config_from_key(self, widget_key, value):
        """Set config value from a widget key tuple."""
        ConfigManager.set_config_value(value, *widget_key)

    def _get_widget_value(self, widget, value_type):
        """Get the typed value from a widget."""
        if isinstance(widget, QCheckBox):
            return widget.isChecked()
        elif isinstance(widget, QComboBox):
            return widget.currentText() or None
        elif isinstance(widget, QTextEdit):
            text = widget.toPlainText()
            return text or None
        elif isinstance(widget, QLineEdit):
            text = widget.text()
            if value_type == 'int':
                return int(text) if text else None
            elif value_type == 'float':
                return float(text) if text else None
            return text or None
        elif isinstance(widget, QWidget) and hasattr(widget, '_value_widget'):
            # model_path container
            return widget._value_widget.text() or None
        return None

    def _set_widget_value(self, widget, value, value_type):
        """Set a widget's displayed value."""
        if isinstance(widget, QCheckBox):
            widget.setChecked(bool(value))
        elif isinstance(widget, QComboBox):
            widget.setCurrentText(str(value) if value else '')
        elif isinstance(widget, QTextEdit):
            widget.setPlainText(str(value) if value else '')
        elif isinstance(widget, QLineEdit):
            # For API key fields, try env first
            widget.setText(str(value) if value is not None else '')
        elif isinstance(widget, QWidget) and hasattr(widget, '_value_widget'):
            widget._value_widget.setText(str(value) if value is not None else '')

    def _browse_model_path(self, line_edit):
        """Open a file dialog to select a model path."""
        file_path = QFileDialog.getExistingDirectory(self, "Select Whisper Model Directory")
        if not file_path:
            file_path, _ = QFileDialog.getOpenFileName(
                self, "Select Whisper Model File", "",
                "Model Files (*.bin *.pt);;CTranslate2 Model (model.bin);;All Files (*)"
            )
        if file_path:
            line_edit.setText(file_path)

    # ===================================================================
    # Close event
    # ===================================================================

    def closeEvent(self, event):
        """Confirm before closing without saving."""
        reply = QMessageBox.question(
            self,
            'Close without saving?',
            'Are you sure you want to close without saving?',
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            ConfigManager.reload_config()
            self.settings_closed.emit()
            super().closeEvent(event)
        else:
            event.ignore()
