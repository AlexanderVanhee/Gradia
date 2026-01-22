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

from gi.repository import Gtk, GObject
from typing import Optional

class ToggleGroup(Gtk.Box):
    __gtype_name__ = "GradiaToggleGroup"

    active_name = GObject.Property(
        type=str,
        default="",
        flags=GObject.ParamFlags.READWRITE
    )

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.set_orientation(Gtk.Orientation.VERTICAL)
        self._updating = False
        self._active_name_value = ""
        self._toggle_buttons = {}
        self._create_widget()

    def _create_widget(self) -> None:
        flowbox = Gtk.FlowBox()
        flowbox.set_max_children_per_line(4)
        flowbox.set_min_children_per_line(2)
        flowbox.set_homogeneous(True)
        flowbox.set_row_spacing(10)
        flowbox.set_column_spacing(8)

        toggle_data = [
            ("none", "_None"),
            ("solid", "_Solid"),
            ("gradient", "_Gradient"),
            ("image", "_Image")
        ]

        for name, label in toggle_data:
            toggle = Gtk.ToggleButton()
            toggle.set_label(label)
            toggle.set_use_underline(True)
            toggle.connect("toggled", self._on_toggle_changed, name)
            self._toggle_buttons[name] = toggle
            flowbox.append(toggle)

        self.append(flowbox)

    def _on_toggle_changed(self, button: Gtk.ToggleButton, name: str) -> None:
        if self._updating:
            return

        if button.get_active():
            self._updating = True
            for toggle_name, toggle_button in self._toggle_buttons.items():
                if toggle_name != name:
                    toggle_button.set_active(False)
            self._updating = False

            self._active_name_value = name
            self.notify("active-name")
        else:
            if self._active_name_value == name:
                self._updating = True
                button.set_active(True)
                self._updating = False

    def do_get_property(self, pspec):
        if pspec.name == "active-name":
            return self._active_name_value

    def get_active_name(self) -> Optional[str]:
        return self._active_name_value if self._active_name_value else None

    def set_active_name(self, name: str) -> None:
        if name in self._toggle_buttons and self._active_name_value != name:
            self._active_name_value = name
            self._updating = True
            for toggle_name, toggle_button in self._toggle_buttons.items():
                toggle_button.set_active(toggle_name == name)
            self._updating = False
            self.notify("active-name")
