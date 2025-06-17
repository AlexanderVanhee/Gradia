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

from gi.repository import Adw, Gio, GLib, Gtk
from typing import Callable, Optional
from gradia.backend.settings import Settings
from gradia.constants import rootdir  # pyright: ignore

@Gtk.Template(resource_path=f"{rootdir}/ui/confirm_close_dialog.ui")
class ConfirmCloseDialog(Adw.AlertDialog):
    __gtype_name__ = "GradiaConfirmCloseDialog"

    dont_ask_switch: Gtk.CheckButton = Gtk.Template.Child()

    def __init__(self, parent_window: Adw.ApplicationWindow, **kwargs) -> None:
        super().__init__(**kwargs)
        self.parent_window = parent_window
        self.on_confirm_callback: Optional[Callable[[], None]] = None
        self.settings = Settings()
        self._setup_settings_binding()

    """
    Setup Methods
    """

    def _setup_settings_binding(self) -> None:
        """Bind the switch to the settings"""
        self.settings._settings.bind(
            "show-close-confirm-dialog",
            self.dont_ask_switch,
            "active",
            Gio.SettingsBindFlags.INVERT_BOOLEAN
        )

    """
    Public Methods
    """

    def show_dialog(self, on_confirm_callback: Callable[[], None]) -> None:
        """Show the confirmation dialog"""
        self.on_confirm_callback = on_confirm_callback
        self.choose(self.parent_window, None, self._on_response)

    """
    Callbacks
    """

    def _on_response(self, dialog: Adw.AlertDialog, task: Gio.Task) -> None:
        response = dialog.choose_finish(task)
        if response == "close" and self.on_confirm_callback:
            self.on_confirm_callback()
