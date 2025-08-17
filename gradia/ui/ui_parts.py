# Copyright (C) 2025 Alexander Vanhee, tfuxu
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <https://www.gnu.org/licenses/>.
#
# SPDX-License-Identifier: GPL-3.0-or-later

from typing import Optional
from gi.repository import Adw, Gtk
from gradia import constants


class AboutDialog:
    def __init__(self, version: str):
        self.version = version
        self.dialog = None

    def create(self) -> Adw.AboutDialog:
        self.dialog = Adw.AboutDialog(
            application_name="Gradia",
            version=self.version,
            comments=_("Make your images ready for all"),
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
            application_icon=constants.app_id,
            # Translators: This is a place to put your credits (formats: "Name https://example.com" or "Name <email@example.com>", no quotes) and is not meant to be translated literally.
            translator_credits=_("translator-credits"),
            copyright="Copyright © 2025 Alexander Vanhee",
            license_type=Gtk.License.GPL_3_0
        )

        self.dialog.add_acknowledgement_section(
            _("Code and Design Borrowed from"),
            [
                "Switcheroo https://apps.gnome.org/en-GB/Converter/",
                "Halftone https://github.com/tfuxu/Halftone",
                "Gradience https://github.com/GradienceTeam/Gradience",
                "Emblem https://apps.gnome.org/en-GB/Emblem/",
                "Builder https://apps.gnome.org/en-GB/Builder/",
                None
            ]
        )

        self.dialog.add_acknowledgement_section(
            _("Image Sources"),
            [
                "GNOME backgrounds https://gitlab.gnome.org/GNOME/gnome-backgrounds",
                "Fruit Basket https://unsplash.com/photos/background-pattern-oWr5S1bO2ak",
                None
            ]
        )


        return self.dialog

    def show(self, parent: Optional[Gtk.Window] = None):
        if not self.dialog:
            self.create()
        self.dialog.present(parent)


class ShortcutsDialog:
    def __init__(self, parent: Optional[Gtk.Window] = None):
        self.parent = parent
        self.dialog = None
        self.shortcut_groups = [
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
                    (_("Erase Selected"), "Delete"),
                    (_("Select"),      "0 S"),
                    (_("Pen"),         "1 P"),
                    (_("Text"),        "2 T"),
                    (_("Line"),        "3 L"),
                    (_("Arrow"),       "4 A"),
                    (_("Rectangle"),   "5 R"),
                    (_("Oval"),        "6 O"),
                    (_("Highlighter"), "7 H"),
                    (_("Censor"),      "8 C"),
                    (_("Number"),      "9 N"),
                    (_("Adjust Tool Size"), _("Ctrl + Shift + Mouse Wheel")),
                ]
            },
            {
                "title": _("Cropping"),
                "shortcuts": [
                    (_("Toggle Crop Mode"), "<Ctrl>R"),
                    (_("Reset Crop"), "<Ctrl><Shift>R")
                ]
            },
            {
                "title": _("General"),
                "shortcuts": [
                    (_("Keyboard Shortcuts"), "<Ctrl>question"),
                    (_("Preferences"), "<Ctrl>comma"),
                    (_("Open Source Snippets"), "<Ctrl>P"),
                ]
            },
            {
                "title": _("Zoom Image"),
                "shortcuts": [
                    (_("Zoom In"), "<Ctrl>plus plus"),
                    (_("Zoom Out"), "<Ctrl>minus minus"),
                    (_("Reset Zoom"), "<Ctrl>0 equal"),
                ]
            }
        ]

    def create(self) -> Gtk.ShortcutsWindow:
        self.dialog = Gtk.ShortcutsWindow(transient_for=self.parent, modal=True)
        section = Gtk.ShortcutsSection()

        for group_data in self.shortcut_groups:
            group = Gtk.ShortcutsGroup(title=group_data["title"], visible=True)
            for title, accel in group_data["shortcuts"]:
                if any(word in accel for word in ["Mouse", "Wheel", "Scroll"]) and not accel.startswith("<"):
                    shortcut = Gtk.ShortcutsShortcut(
                        title=title,
                        subtitle=accel
                    )
                else:
                    shortcut = Gtk.ShortcutsShortcut(
                        title=title,
                        accelerator=accel
                    )

                group.add_shortcut(shortcut)
            section.add_group(group)

        self.dialog.add_section(section)
        self.dialog.connect("close-request", lambda dialog: dialog.destroy())
        return self.dialog

    def show(self):
        if not self.dialog:
            self.create()
        self.dialog.present()

    def set_parent(self, parent: Gtk.Window):
        self.parent = parent
        if self.dialog:
            self.dialog.set_transient_for(parent)
