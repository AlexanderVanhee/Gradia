# Copyright (C) 2025 Alexander Vanhee, tfuxu
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

from typing import Optional

from gi.repository import Adw, Gtk

def create_about_dialog(version: str) -> Adw.AboutDialog:
    dialog = Adw.AboutDialog(
        application_name="Gradia",
        version=version,
        comments=_("Make your images ready for the world"),
        website="https://github.com/AlexanderVanhee/Gradia",
        issue_url="https://github.com/AlexanderVanhee/Gradia/issues",
        developer_name="Alexander Vanhee",
        developers=[
            "Alexander Vanhee https://github.com/AlexanderVanhee",
            "tfuxu https://github.com/tfuxu",
        ],
        designers=[
            "drpetrikov https://github.com/drpetrikov"
        ],
        application_icon="be.alexandervanhee.gradia",
        # Translators: This is a place to put your credits (formats: "Name https://example.com" or "Name <email@example.com>", no quotes) and is not meant to be translated literally.
        translator_credits=_("translator-credits"),
        copyright="Copyright © 2025 Alexander Vanhee",
        license_type=Gtk.License.GPL_3_0
    )

    return dialog

def create_shortcuts_dialog(parent: Optional[Gtk.Window] = None) -> Gtk.ShortcutsWindow:
    SHORTCUT_GROUPS = [
        {
            "title": _("File Actions"),
            "shortcuts": [
                (_("Open File"), "<Ctrl>O"),
                (_("Save to File"), "<Ctrl>S"),
                (_("Copy Image to Clipboard"), "<Ctrl>C"),
                (_("Paste From Clipboard"), "<Ctrl>V"),
                (_("Share Image"), "<Ctrl>M"),
            ]
        },
        {
            "title": _("Annotations"),
            "shortcuts": [
                (_("Undo"), "<Ctrl>Z"),
                (_("Redo"), "<Ctrl><Shift>Z"),
                (_("Erase Selected"), "Delete")
            ]
        },
        {
            "title": _("General"),
            "shortcuts": [
                (_("Keyboard Shortcuts"), "<Ctrl>question"),
                (_("Preferences"), "<Ctrl>comma"),
                (_("Toggle Utility Pane"), "F9"),
            ]
        }
    ]

    dialog = Gtk.ShortcutsWindow(transient_for=parent, modal=True)
    section = Gtk.ShortcutsSection()

    for group_data in SHORTCUT_GROUPS:
        group = Gtk.ShortcutsGroup(title=group_data["title"], visible=True)
        for title, accel in group_data["shortcuts"]:
            group.add_shortcut(Gtk.ShortcutsShortcut(
                title=title,
                accelerator=accel
            ))
        section.add_group(group)

    dialog.add_section(section)
    dialog.connect("close-request", lambda dialog: dialog.destroy())

    return dialog
