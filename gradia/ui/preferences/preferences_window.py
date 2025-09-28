# Copyright (C) 2025 Alexander Vanhee
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.
#
# SPDX-License-Identifier: GPL-3.0-or-later

import os
from pathlib import Path
from gi.repository import Gtk, Adw, GLib, Gio, GObject
from typing import Optional

from gradia.constants import rootdir  # pyright: ignore
from gradia.backend.settings import Settings
from gradia.app_constants import SUPPORTED_EXPORT_FORMATS
from gradia.backend.logger import Logger
from gradia.ui.preferences.provider_selection_window import ProviderListPage
from gradia.ui.preferences.ocr_model_page import OCRModelPage
from gradia.backend.ocr import OCR

logger = Logger()


@Gtk.Template(resource_path=f"{rootdir}/ui/preferences_window.ui")
class PreferencesWindow(Adw.PreferencesDialog):
    __gtype_name__ = 'GradiaPreferencesWindow'

    help_button: Gtk.Button = Gtk.Template.Child()
    save_format_group: Adw.PreferencesGroup = Gtk.Template.Child()
    delete_screenshot_switch: Adw.SwitchRow = Gtk.Template.Child()
    overwrite_screenshot_switch: Adw.SwitchRow = Gtk.Template.Child()
    confirm_upload_switch: Adw.SwitchRow = Gtk.Template.Child()
    save_format_combo: Adw.ComboRow = Gtk.Template.Child()
    provider_name: Gtk.Label = Gtk.Template.Child()
    exiting_combo: Adw.ComboRow = Gtk.Template.Child()
    folder_label: Gtk.Label = Gtk.Template.Child()

    def __init__(self, parent_window: Adw.ApplicationWindow, **kwargs):
        super().__init__(**kwargs)

        self.parent_window = parent_window

        self.settings = Settings()

        self._setup_widgets()
        self._connect_signals()

        shortcut_controller = Gtk.ShortcutController()
        shortcut = Gtk.Shortcut.new(
            Gtk.ShortcutTrigger.parse_string("Escape"),
            Gtk.ShortcutAction.parse_string("action(window.close)")
        )
        shortcut_controller.add_shortcut(shortcut)
        self.add_controller(shortcut_controller)

    def _setup_widgets(self):
        self._setup_save_format_combo()
        self._setup_exiting_combo()
        self._setup_provider_display()
        self._bind_settings()
        self._setup_folder_label()

    def _setup_provider_display(self):
        provider_name = self.settings.provider_name
        if provider_name:
            self.provider_name.set_text(provider_name)
        else:
            self.provider_name.set_text(_("None Selected"))

    def _setup_folder_label(self):
       path = self.settings.screenshot_folder
       if path is None:
           path = "Screenshots"
       self.folder_label.set_text(os.path.basename(path))

    def _setup_save_format_combo(self):
        current_format = self.settings.export_format
        string_list = Gtk.StringList()

        format_keys = list(SUPPORTED_EXPORT_FORMATS.keys())
        self.format_keys = format_keys

        for fmt in format_keys:
            display_name = SUPPORTED_EXPORT_FORMATS[fmt]['shortname']
            string_list.append(display_name)

        self.save_format_combo.set_model(string_list)

        try:
            current_index = format_keys.index(current_format)
            self.save_format_combo.set_selected(current_index)
        except ValueError:
            self.save_format_combo.set_selected(0)

        self.save_format_combo.connect("notify::selected", self._on_save_format_changed)

    def _setup_exiting_combo(self):
        current_exit_method = self.settings.exit_method
        string_list = Gtk.StringList()

        exit_options = [
            ("confirm", _("Ask For Confirmation")),
            ("copy", _("Copy and Close ")),
            ("none", _("Close Instantly"))
        ]
        self.exit_option_keys = [key for key, _ in exit_options]

        for key, display_name in exit_options:
            string_list.append(display_name)

        self.exiting_combo.set_model(string_list)

        try:
            current_index = self.exit_option_keys.index(current_exit_method)
            self.exiting_combo.set_selected(current_index)
        except ValueError:
            self.exiting_combo.set_selected(0)

        self.exiting_combo.connect("notify::selected", self._on_exit_method_changed)

    def _on_save_format_changed(self, combo_row, pspec) -> None:
        selected = combo_row.get_selected()
        if selected < len(self.format_keys):
            self.settings.export_format = self.format_keys[selected]

    def _on_exit_method_changed(self, combo_row, pspec) -> None:
        selected = combo_row.get_selected()
        if selected < len(self.exit_option_keys):
            self.settings.exit_method = self.exit_option_keys[selected]

    def _connect_signals(self):
        self.help_button.connect("activated", self._on_help_button_clicked)

    def _on_help_button_clicked(self, button: Gtk.Button) -> None:
        self.push_subpage(ScreenshotGuidePage(self))

    def _copy_to_clipboard(self, text: str) -> None:
        clipboard = self.get_clipboard()
        clipboard.set(text)
        self.show_toast(_("Copied!"))

    def show_toast(self, message: str) -> None:
        toast = Adw.Toast.new(message)
        toast.set_timeout(2)
        if hasattr(self.parent_window, 'add_toast'):
            self.parent_window.add_toast(toast)

    def _bind_settings(self):
        self.settings.bind_switch(self.delete_screenshot_switch,"trash-screenshots-on-close")
        self.settings.bind_switch(self.confirm_upload_switch,"show-export-confirm-dialog")
        self.settings.bind_switch(self.overwrite_screenshot_switch,"overwrite-screenshot")

    @Gtk.Template.Callback()
    def on_choose_provider_clicked(self, button: Gtk.Button) -> None:
        def handle_selection(name: str, command: str):
            self.provider_name.set_text(name)
            self.settings.provider_name = name
            self.settings.custom_export_command = command
            self.parent_window.update_command_ready()
        self.push_subpage(ProviderListPage(preferences_dialog=self,on_provider_selected=handle_selection))

    @Gtk.Template.Callback()
    def on_folder_row_clicked(self, row: Adw.ActionRow) -> None:
        file_dialog = Gtk.FileDialog()
        def on_folder_selected(dialog, result):
            try:
                folder = dialog.select_folder_finish(result)
                if folder:
                    folder_path = folder.get_path()
                    logger.info(f"Selected folder for home page: {folder_path}")
                    self.folder_label.set_text(os.path.basename(folder_path))
                    self.settings.screenshot_folder = folder_path

                    window = self.parent_window
                    action = window.lookup_action("set-screenshot-folder") if window else None
                    if action:
                        action.activate(GLib.Variant('s', folder_path))

            except GLib.Error:
                pass

        file_dialog.select_folder(
            parent=self.get_root(),
            cancellable=None,
            callback=on_folder_selected
        )

    @Gtk.Template.Callback()
    def on_manage_language_models_clicked(self, row: Adw.ActionRow) -> None:
        self.push_subpage(OCRModelPage(preferences_dialog=self, window=self.get_root()))

@Gtk.Template(resource_path=f"{rootdir}/ui/preferences/screenshot_guide_page.ui")
class ScreenshotGuidePage(Adw.NavigationPage):
    __gtype_name__ = 'GradiaScreenshotGuidePage'

    interactive_entry: Gtk.Entry = Gtk.Template.Child()
    fullscreen_entry: Gtk.Entry = Gtk.Template.Child()
    delayed_entry: Gtk.Entry = Gtk.Template.Child()

    def __init__(self, preferences_dialog, **kwargs):
        super().__init__(**kwargs)
        self.preferences_dialog = preferences_dialog
        self._connect_signals()
        self._setup_command_entries()

    def _is_running_in_flatpak(self) -> bool:
        if os.getenv('FLATPAK_ID'):
            return True
        if Path('/.flatpak-info').exists():
            return True
        if '/app/' in str(Path(__file__).resolve()):
            return True
        return False

    def _get_command_for_screenshot_type(self, screenshot_type: str) -> str:
        if self._is_running_in_flatpak():
            return f"flatpak run be.alexandervanhee.gradia --screenshot={screenshot_type}"
        else:
            return f"gradia --screenshot={screenshot_type}"

    def _connect_signals(self):
        self.interactive_entry.connect("icon-press", self._on_entry_icon_press)
        self.fullscreen_entry.connect("icon-press", self._on_entry_icon_press)
        self.delayed_entry.connect("icon-press", self._on_entry_icon_press)

    def _on_entry_icon_press(self, entry: Gtk.Entry, icon_pos: Gtk.EntryIconPosition) -> None:
        if icon_pos == Gtk.EntryIconPosition.SECONDARY:
            self._copy_to_clipboard(entry.get_text())

    def _copy_to_clipboard(self, text: str) -> None:
        clipboard = self.get_clipboard()
        clipboard.set(text)
        toast = Adw.Toast(title=_("Copied!"), timeout=1.5)
        self.preferences_dialog.add_toast(toast)

    def _setup_command_entries(self):
        interactive_command = self._get_command_for_screenshot_type("INTERACTIVE")
        fullscreen_command = self._get_command_for_screenshot_type("FULL")

        self.interactive_entry.set_text(interactive_command)
        self.fullscreen_entry.set_text(fullscreen_command)
