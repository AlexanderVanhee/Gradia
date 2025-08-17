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

from gi.repository import Gtk, Gio, GObject, GLib, Pango
from typing import Optional

class FontDropdown(Gtk.Box):
    __gtype_name__ = "GradiaFontDropdown"
    __gsignals__ = {
        "font-changed": (GObject.SignalFlags.RUN_FIRST, None, (str,))
    }
    selected_font = GObject.Property(
        type=str,
        default="",
        flags=GObject.ParamFlags.READWRITE
    )

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.set_orientation(Gtk.Orientation.VERTICAL)
        self.set_spacing(6)
        self.fonts = self._get_available_fonts()
        self.font_string_list = Gtk.StringList()
        self.font_dropdown = None
        self._updating = False
        self._selected_font_value = ""
        self._setup_font_dropdown()
        self._create_widget()

    def _get_available_fonts(self) -> list[str]:
        widget = Gtk.Label()
        context = widget.get_pango_context()
        font_map = context.get_font_map()
        families = font_map.list_families()
        system_fonts = []
        for family in families:
            font_name = family.get_name()
            system_fonts.append(font_name)
        return sorted(system_fonts)

    def _setup_font_dropdown(self) -> None:
        for font in self.fonts:
            self.font_string_list.append(font)

    def _create_widget(self) -> None:
        self.font_dropdown = Gtk.DropDown(model=self.font_string_list, vexpand=True)
        list_factory = Gtk.SignalListItemFactory()
        list_factory.connect("setup", self._factory_setup_list)
        list_factory.connect("bind", self._factory_bind)
        self.font_dropdown.set_list_factory(list_factory)
        selected_factory = Gtk.SignalListItemFactory()
        selected_factory.connect("setup", self._factory_setup_selected)
        selected_factory.connect("bind", self._factory_bind)
        self.font_dropdown.set_factory(selected_factory)
        self.font_dropdown.connect("notify::selected", self._on_font_selected)
        self.append(self.font_dropdown)

    def _factory_setup_list(self, factory: Gtk.SignalListItemFactory, list_item, *args) -> None:
        label = Gtk.Label(halign=Gtk.Align.START, ellipsize=Pango.EllipsizeMode.NONE)
        label.set_xalign(0)
        list_item.set_child(label)

    def _factory_setup_selected(self, factory: Gtk.SignalListItemFactory, list_item, *args) -> None:
        label = Gtk.Label(halign=Gtk.Align.START, ellipsize=Pango.EllipsizeMode.END, max_width_chars=20)
        label.set_xalign(0)
        list_item.set_child(label)

    def _factory_bind(self, factory: Gtk.SignalListItemFactory, list_item, *args) -> None:
        label = list_item.get_child()
        string_object = list_item.get_item()
        font_name = string_object.get_string()
        label.set_text(font_name)
        attr_list = Pango.AttrList()
        font_desc = Pango.FontDescription.from_string(f"{font_name} 12")
        attr_list.insert(Pango.attr_font_desc_new(font_desc))
        label.set_attributes(attr_list)

    def _on_font_selected(self, dropdown: Gtk.DropDown, _param: GObject.ParamSpec, *args) -> None:
        if self._updating:
            return
        selected_index = dropdown.get_selected()
        if 0 <= selected_index < len(self.fonts):
            font_name = self.fonts[selected_index]
            self._selected_font_value = font_name
            self.emit("font-changed", font_name)

    def do_get_property(self, pspec):
        if pspec.name == "selected-font":
            return self._selected_font_value

    def get_selected_font(self) -> Optional[str]:
        return self._selected_font_value if self._selected_font_value else None

    def set_selected_font(self, font_name: str) -> None:
        if font_name in self.fonts and self._selected_font_value != font_name:
            self._selected_font_value = font_name
            if self.font_dropdown:
                font_index = self.fonts.index(font_name)
                self._updating = True
                self.font_dropdown.set_selected(font_index)
                self._updating = False
            self.notify("selected-font")
