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
from typing import Optional, Callable
from gradia.backend.settings import Settings


class FontDropdownController:
    def __init__(self, font_string_list: Gtk.StringList, settings: Settings, window,
                 font_change_callback: Optional[Callable[[str], None]] = None):
        self.font_string_list = font_string_list
        self.settings = settings
        self.font_change_callback = font_change_callback
        self.fonts = self._get_available_fonts()
        self.font_dropdown = None
        self._setup_font_dropdown()
        self.window = window

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

    def create_font_widget(self) -> Gtk.Box:
        font_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)

        self.font_dropdown = Gtk.DropDown(model=self.font_string_list)

        factory = Gtk.SignalListItemFactory()
        factory.connect("setup", self.factory_setup)
        factory.connect("bind", self.factory_bind)
        self.font_dropdown.set_factory(factory)

        self.font_dropdown.connect("notify::selected", self.on_font_selected)

        font_box.append(self.font_dropdown)

        return font_box

    def factory_setup(self, factory: Gtk.SignalListItemFactory, list_item, *args) -> None:
        label = Gtk.Label(halign=Gtk.Align.START)
        list_item.set_child(label)

    def factory_bind(self, factory: Gtk.SignalListItemFactory, list_item, *args) -> None:
        label = list_item.get_child()
        string_object = list_item.get_item()
        font_name = string_object.get_string()
        label.set_text(font_name)

        attr_list = Pango.AttrList()
        font_desc = Pango.FontDescription.from_string(f"{font_name} 12")
        attr_font = Pango.attr_font_desc_new(font_desc)
        attr_list.insert(attr_font)
        label.set_attributes(attr_list)

    def on_font_selected(self, dropdown: Gtk.DropDown, _param: GObject.ParamSpec, *args) -> None:
        selected_index = dropdown.get_selected()
        if 0 <= selected_index < len(self.fonts):
            font_name = self.fonts[selected_index]
            self.settings.font = font_name

            if self.window:
                action = self.window.lookup_action("font")
                if action:
                    action.activate(GLib.Variant('s', font_name))

            if self.font_change_callback:
                self.font_change_callback(font_name)

    def restore_font_selection(self, font_dropdown: Gtk.DropDown = None) -> None:
        saved_font = self.settings.font
        dropdown = font_dropdown or self.font_dropdown
        if saved_font in self.fonts:
            font_index = self.fonts.index(saved_font)
            GLib.idle_add(self._set_font_selection, dropdown, font_index)

    def _set_font_selection(self, font_dropdown: Gtk.DropDown, index: int) -> bool:

        font_dropdown.set_selected(index)
        return False

    def initialize_font_action(self) -> None:
        if self.window:
            action = self.window.lookup_action("font")
            if action:
                action.activate(GLib.Variant('s', self.settings.font))

    def get_selected_font(self) -> Optional[str]:
        if self.font_dropdown:
            selected_index = self.font_dropdown.get_selected()
            if 0 <= selected_index < len(self.fonts):
                return self.fonts[selected_index]
        return None
