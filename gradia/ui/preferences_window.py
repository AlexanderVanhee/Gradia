# preferences_window.py
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

def is_running_in_flatpak() -> bool:
    if os.getenv('FLATPAK_ID'):
        return True
    if Path('/.flatpak-info').exists():
        return True
    if '/app/' in str(Path(__file__).resolve()):
        return True

    return False


def get_command_for_screenshot_type(screenshot_type: str) -> str:
    if is_running_in_flatpak():
        return f"flatpak run be.alexandervanhee.gradia --screenshot={screenshot_type}"
    else:
        return f"gradia --screenshot={screenshot_type}"


@Gtk.Template(resource_path=f"{rootdir}/ui/preferences_window.ui")
class PreferencesWindow(Adw.PreferencesWindow):
    __gtype_name__ = 'GradiaPreferencesWindow'

    location_group: Adw.PreferencesGroup = Gtk.Template.Child()
    folder_expander: Adw.ExpanderRow = Gtk.Template.Child()
    interactive_entry: Gtk.Entry = Gtk.Template.Child()
    interactive_copy_btn: Gtk.Button = Gtk.Template.Child()
    fullscreen_entry: Gtk.Entry = Gtk.Template.Child()
    fullscreen_copy_btn: Gtk.Button = Gtk.Template.Child()
    save_format_combo: Adw.ComboRow = Gtk.Template.Child()
    compress_switch: Adw.SwitchRow = Gtk.Template.Child()
    delete_screenshot_switch: Adw.SwitchRow = Gtk.Template.Child()
    confirm_close_switch: Adw.SwitchRow = Gtk.Template.Child()
    confirm_upload_switch: Adw.SwitchRow = Gtk.Template.Child()
    command_entry: Gtk.Entry = Gtk.Template.Child()
    command_reset: Gtk.Button = Gtk.Template.Child()

    def __init__(self, parent_window: Adw.ApplicationWindow, **kwargs):
        super().__init__(**kwargs)

        self.parent_window = parent_window
        self.set_transient_for(parent_window)

        self.settings = Settings()
        self.folder_finder = ScreenshotFolderFinder()
        self.available_folders = self.folder_finder.get_screenshot_folders()
        self.current_selected_folder = self.folder_finder.get_current_folder()
        self.folder_rows = []

        self._setup_widgets()
        self._connect_signals()

    def _setup_widgets(self):
        self._update_expander_title()
        self._create_folder_rows()
        self._populate_save_format_combo()
        self._setup_command_entries()
        self._bind_settings()

        self.command_entry.set_text(self.settings.custom_export_command)

    def _setup_command_entries(self):
        interactive_command = get_command_for_screenshot_type("INTERACTIVE")
        fullscreen_command = get_command_for_screenshot_type("FULL")

        self.interactive_entry.set_text(interactive_command)
        self.fullscreen_entry.set_text(fullscreen_command)

    def _update_expander_title(self):
        if self.current_selected_folder:
            display_name = next(
                (name for name, folder in self.available_folders if folder == self.current_selected_folder),
                self.current_selected_folder
            )
            self.folder_expander.set_title(_("Selected: {folder}").format(folder=display_name))
            self.folder_expander.set_subtitle(_("Click to change folder"))
        else:
            self.folder_expander.set_title(_("Selected: {folder}").format(folder=_("Root")))
            self.folder_expander.set_subtitle(_("Click to change folder"))

    def _create_folder_rows(self):
        for row in self.folder_rows:
            self.folder_expander.remove(row)
        self.folder_rows.clear()

        for display_name, folder_name in self.available_folders:
            row = Adw.ActionRow()
            row.set_title(display_name)

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

    def _populate_save_format_combo(self):
        string_list = Gtk.StringList()
        current_format = self.settings.export_format

        selected_index = 0

        format_keys = list(SUPPORTED_EXPORT_FORMATS.keys())

        for i, fmt in enumerate(format_keys):
            display_name = SUPPORTED_EXPORT_FORMATS[fmt]['name']
            string_list.append(display_name)

            if fmt == current_format:
                selected_index = i

        self.save_format_combo.set_model(string_list)
        self.save_format_combo.set_selected(selected_index)

    def _on_export_format_changed(self, combo: Adw.ComboRow, pspec):
        selected_index = combo.get_selected()
        if selected_index != Gtk.INVALID_LIST_POSITION:
            format_keys = list(SUPPORTED_EXPORT_FORMATS.keys())

            if selected_index < len(format_keys):
                fmt = format_keys[selected_index]
                self.settings.export_format = fmt
            else:
                logger.info(f"Index {selected_index} out of range for {len(format_keys)} formats")

    def _connect_signals(self):
        self.interactive_copy_btn.connect("clicked",
            lambda btn: self._copy_to_clipboard(self.interactive_entry.get_text()))
        self.fullscreen_copy_btn.connect("clicked",
            lambda btn: self._copy_to_clipboard(self.fullscreen_entry.get_text()))

        self.save_format_combo.connect("notify::selected", self._on_export_format_changed)

        self.command_entry.connect("changed", self._on_command_entry_changed)
        self.command_reset.connect("clicked", self._on_command_reset_clicked)

    def _on_folder_row_activated(self, row: Adw.ActionRow) -> None:
        folder_name = row.folder_name
        self._update_folder_selection(folder_name)

        self.folder_expander.set_expanded(False)

        app = Gio.Application.get_default()
        action = app.lookup_action("set-screenshot-folder") if app else None
        if action:
            action.activate(GLib.Variant('s', folder_name))

    def _update_folder_selection(self, selected_folder: str) -> None:
        self.current_selected_folder = selected_folder
        self.settings.screenshot_subfolder = selected_folder

        for row in self.folder_rows:
            is_selected = row.folder_name == selected_folder
            row.checkmark.set_visible(is_selected)
        self._update_expander_title()

    def _on_command_entry_changed(self, entry: Gtk.Entry) -> None:
        self.settings.custom_export_command = entry.get_text()
        self.parent_window.update_command_ready()

    def _on_command_reset_clicked(self, button: Gtk.Button) -> None:
        self.command_entry.set_text("")
        self.settings.custom_export_command = ""
        self.parent_window.update_command_ready()

    def _copy_to_clipboard(self, text: str) -> None:
        clipboard = self.get_clipboard()
        clipboard.set(text)
        self.show_toast(_("Copied!"))

    def show_toast(self, message: str) -> None:
        toast = Adw.Toast.new(message)
        toast.set_timeout(2)
        self.add_toast(toast)

    def set_current_subfolder(self, subfolder: str) -> None:
        self._update_folder_selection(subfolder)

    def _bind_settings(self):
        self.settings.bind_switch(self.compress_switch,"export-compress")
        self.settings.bind_switch(self.delete_screenshot_switch,"trash-screenshots-on-close")
        self.settings.bind_switch(self.confirm_close_switch,"show-close-confirm-dialog")
        self.settings.bind_switch(self.confirm_upload_switch,"show-export-confirm-dialog")
