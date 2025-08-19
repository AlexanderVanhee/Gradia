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

import re
import os
from pathlib import Path
from gi.repository import Gtk, Adw, GLib, Gio
from typing import Optional

from gradia.constants import rootdir  # pyright: ignore
from gradia.backend.settings import Settings
from gradia.app_constants import SUPPORTED_EXPORT_FORMATS
from gradia.backend.logger import Logger
from gradia.ui.provider_selection_window import ProviderListPage

logger = Logger()

class ScreenshotFolderFinder:

    def __init__(self):
        self.pictures_dir = Path(GLib.get_user_special_dir(GLib.USER_DIRECTORY_PICTURES))

    def get_screenshot_folders(self) -> list[tuple[str, str]]:
        folders = [(_("Root"), "")]

        if not self.pictures_dir.exists():
            return folders

        try:
            subdirs = [d for d in self.pictures_dir.iterdir()
                       if d.is_dir() and not d.name.startswith('.')]

            subdirs.sort(key=lambda d: d.name.lower())
            for subdir in subdirs:
                folders.append((subdir.name, subdir.name))

        except PermissionError:
            logger.warning(f"Permission denied accessing {self.pictures_dir}")
        except Exception as e:
            logger.warning(f"Error reading screenshot folders: {e}")

        return folders

    def get_current_folder(self):
        return Settings().screenshot_subfolder

@Gtk.Template(resource_path=f"{rootdir}/ui/preferences_window.ui")
class PreferencesWindow(Adw.PreferencesDialog):
    __gtype_name__ = 'GradiaPreferencesWindow'
    help_button: Gtk.Button = Gtk.Template.Child()


    folder_expander: Adw.ExpanderRow = Gtk.Template.Child()
    folder_label: Gtk.Label = Gtk.Template.Child()
    save_format_group: Adw.PreferencesGroup = Gtk.Template.Child()
    delete_screenshot_switch: Adw.SwitchRow = Gtk.Template.Child()
    confirm_upload_switch: Adw.SwitchRow = Gtk.Template.Child()
    save_format_combo: Adw.ComboRow = Gtk.Template.Child()
    provider_name: Gtk.Label = Gtk.Template.Child()
    exiting_toggle_group = Gtk.Template.Child()


    def __init__(self, parent_window: Adw.ApplicationWindow, **kwargs):
        super().__init__(**kwargs)

        self.parent_window = parent_window

        self.settings = Settings()
        self.folder_finder = ScreenshotFolderFinder()
        self.available_folders = self.folder_finder.get_screenshot_folders()
        self.current_selected_folder = self.folder_finder.get_current_folder()
        self.folder_rows = []
        self.format_toggle_group = None
        self.format_toggles = []

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
        self._update_expander_title()
        self._create_folder_rows()
        self._create_save_format_toggle_group()
        self._setup_provider_display()
        self._bind_settings()

    def _setup_provider_display(self):
        provider_name = self.settings.provider_name
        if provider_name:
            self.provider_name.set_text(provider_name)
        else:
            self.provider_name.set_text(_("None Selected"))

    def _update_expander_title(self):
        if self.current_selected_folder:
            display_name = next(
                (name for name, folder in self.available_folders if folder == self.current_selected_folder),
                self.current_selected_folder
            )
            self.folder_label.set_text(display_name)
        else:
            self.folder_label.set_text(_("Root"))

    def _create_folder_rows(self):
        for row in self.folder_rows:
            self.folder_expander.remove(row)
        self.folder_rows.clear()

        for display_name, folder_name in self.available_folders:
            row = Adw.ActionRow()
            row.set_title(display_name)
            row.add_css_class("monospace")

            checkmark = Gtk.Image()
            checkmark.set_from_icon_name("object-select-symbolic")
            checkmark.set_visible(folder_name == self.current_selected_folder)
            row.add_suffix(checkmark)

            row.folder_name = folder_name
            row.checkmark = checkmark
            row.set_activatable(True)
            row.connect("activated", self._on_folder_row_activated)

            self.folder_expander.add_row(row)
            self.folder_rows.append(row)

    def _create_save_format_toggle_group(self):
        current_format = self.settings.export_format
        toggle_group = Adw.ToggleGroup(valign=Gtk.Align.CENTER)
        toggle_group.add_css_class("round")

        self.format_toggle_group = toggle_group
        self.format_toggles = []

        format_keys = list(SUPPORTED_EXPORT_FORMATS.keys())

        for i, fmt in enumerate(format_keys):
            display_name = SUPPORTED_EXPORT_FORMATS[fmt]['shortname']
            toggle = Adw.Toggle(label=display_name, name=fmt)
            toggle_group.add(toggle)

            self.format_toggles.append(toggle)
            if fmt == current_format:
                toggle_group.set_active_name(fmt)

        toggle_group.connect("notify::active-name", self._on_format_toggle_changed)
        self.save_format_combo.add_suffix(toggle_group)

    def _on_format_toggle_changed(self, toggle_group: Adw.ToggleGroup, pspec) -> None:
        active_name = toggle_group.get_active_name()
        if active_name:
            self.settings.export_format = active_name

    def _connect_signals(self):
        self.help_button.connect("activated", self._on_help_button_clicked)

    def _on_help_button_clicked(self, button: Gtk.Button) -> None:
        self.push_subpage(ScreenshotGuidePage(self))

    def _on_folder_row_activated(self, row: Adw.ActionRow) -> None:
        folder_name = row.folder_name
        self._update_folder_selection(folder_name)

        self.folder_expander.set_expanded(False)

        window = self.parent_window
        action = window.lookup_action("set-screenshot-folder") if window else None
        if action:
            action.activate(GLib.Variant('s', folder_name))

    def _update_folder_selection(self, selected_folder: str) -> None:
        self.current_selected_folder = selected_folder
        self.settings.screenshot_subfolder = selected_folder

        for row in self.folder_rows:
            is_selected = row.folder_name == selected_folder
            row.checkmark.set_visible(is_selected)
        self._update_expander_title()

    def _copy_to_clipboard(self, text: str) -> None:
        clipboard = self.get_clipboard()
        clipboard.set(text)
        self.show_toast(_("Copied!"))

    def show_toast(self, message: str) -> None:
        toast = Adw.Toast.new(message)
        toast.set_timeout(2)
        if hasattr(self.parent_window, 'add_toast'):
            self.parent_window.add_toast(toast)

    def set_current_subfolder(self, subfolder: str) -> None:
        self._update_folder_selection(subfolder)

    def _bind_settings(self):
        self.settings.bind_switch(self.delete_screenshot_switch,"trash-screenshots-on-close")
        self.settings.bind_switch(self.confirm_upload_switch,"show-export-confirm-dialog")
        self.settings.bind_toggle_group(self.exiting_toggle_group,"exit-method")

    @Gtk.Template.Callback()
    def on_choose_provider_clicked(self, button: Gtk.Button) -> None:
        def handle_selection(name: str, command: str):
            self.provider_name.set_text(name)
            self.settings.provider_name = name
            self.settings.custom_export_command = command
            self.parent_window.update_command_ready()
        self.push_subpage(ProviderListPage(preferences_dialog=self,on_provider_selected=handle_selection))

@Gtk.Template(resource_path=f"{rootdir}/ui/preferences/screenshot_guide_page.ui")
class ScreenshotGuidePage(Adw.NavigationPage):
   __gtype_name__ = 'GradiaScreenshotGuidePage'
   interactive_entry: Gtk.Entry = Gtk.Template.Child()
   interactive_copy_btn: Gtk.Button = Gtk.Template.Child()
   fullscreen_entry: Gtk.Entry = Gtk.Template.Child()
   fullscreen_copy_btn: Gtk.Button = Gtk.Template.Child()

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
       self.interactive_copy_btn.connect("clicked",
           lambda btn: self._copy_to_clipboard(self.interactive_entry.get_text()))
       self.fullscreen_copy_btn.connect("clicked",
           lambda btn: self._copy_to_clipboard(self.fullscreen_entry.get_text()))

   def _copy_to_clipboard(self, text: str) -> None:
       clipboard = self.get_clipboard()
       clipboard.set(text)
       toast = Adw.Toast.new(_("Copied!"))
       self.preferences_dialog.add_toast(toast)

   def _setup_command_entries(self):
       interactive_command = self._get_command_for_screenshot_type("INTERACTIVE")
       fullscreen_command = self._get_command_for_screenshot_type("FULL")
       self.interactive_entry.set_text(interactive_command)
       self.fullscreen_entry.set_text(fullscreen_command)
