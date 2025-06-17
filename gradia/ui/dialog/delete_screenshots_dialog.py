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

class DeleteScreenshotsDialog:
    def __init__(self, parent_window: Adw.ApplicationWindow):
        self.parent_window = parent_window
        self.dialog: Optional[Adw.AlertDialog] = None
        self.on_delete_callback: Optional[Callable[[], None]] = None
        self.notification_callback: Optional[Callable[[str], None]] = None
        self.count: int = 0

    def show(self, screenshot_uris: list[str], on_delete_callback: Callable[[], None],
             notification_callback: Callable[[str], None]) -> None:
        if not screenshot_uris:
            notification_callback(_("No screenshots to delete"))
            return

        self.on_delete_callback = on_delete_callback
        self.notification_callback = notification_callback
        self.count = len(screenshot_uris)

        self.dialog = self._create_dialog(screenshot_uris)
        self.dialog.choose(self.parent_window, None, self._on_response)

    def _create_dialog(self, screenshot_uris: list[str]) -> Adw.AlertDialog:
        file_list = self._create_file_list(screenshot_uris)
        heading, body = self._get_dialog_text(len(screenshot_uris))

        dialog = Adw.AlertDialog(
            heading=heading,
            body=body,
            close_response="cancel"
        )

        dialog.set_extra_child(file_list)
        dialog.add_response("cancel", _("Cancel"))
        dialog.add_response("delete", _("Trash"))
        dialog.set_response_appearance("delete", Adw.ResponseAppearance.DESTRUCTIVE)

        return dialog

    def _create_file_list(self, screenshot_uris: list[str]) -> Gtk.ListBox:
        filenames = [
            GLib.filename_display_basename(
                GLib.uri_parse(uri, GLib.UriFlags.NONE).get_path()
            )
            for uri in screenshot_uris
        ]

        file_list = Gtk.ListBox()
        file_list.set_selection_mode(Gtk.SelectionMode.NONE)
        file_list.add_css_class("boxed-list")

        for filename in filenames:
            row = Adw.ActionRow()
            label = Gtk.Label(label=filename, xalign=0)
            label.set_wrap(True)
            label.set_margin_top(6)
            label.set_margin_bottom(6)
            label.set_margin_start(12)
            label.set_margin_end(12)
            row.set_child(label)
            file_list.append(row)

        return file_list

    def _get_dialog_text(self, count: int) -> tuple[str, str]:
        if count == 1:
            heading = _("Trash Screenshot?")
            body = _("Are you sure you want to trash the following file?")
        else:
            heading = _("Trash Screenshots?")
            body = _("Are you sure you want to trash the following files?")

        return heading, body

    def _on_response(self, dialog: Adw.AlertDialog, task: Gio.Task) -> None:
        response = dialog.choose_finish(task)
        if response == "delete" and self.on_delete_callback:
            self.on_delete_callback()
            if self.notification_callback:
                if self.count == 1:
                    self.notification_callback(_("Screenshot moved to trash"))
                else:
                    self.notification_callback(_("Screenshots moved to trash"))
