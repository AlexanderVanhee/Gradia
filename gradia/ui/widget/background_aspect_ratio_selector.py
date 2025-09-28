# Copyright (C) 2025 tfuxu, Alexander Vanhee
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

from typing import Callable, Optional
from gi.repository import Gtk, Adw, GObject, Gdk


class AspectRatioSelector(Adw.ActionRow):
    __gtype_name__ = "GradiaAspectRatioSelector"
    __gsignals__ = {
        'ratio-changed': (GObject.SignalFlags.RUN_FIRST, None, (str,)),
    }
    __gproperties__ = {
        'aspect-ratio': (str, 'Aspect Ratio', 'The selected aspect ratio value',
                        '', GObject.ParamFlags.READWRITE),
    }

    PRESET_RATIOS = [
        ("Auto", ""),
        ("1:1", "1:1"),
        ("16:9", "16:9"),
        ("4:3", "4:3"),
        ("3:2", "3:2"),
        ("2:3", "2:3"),
        ("3:4", "3:4"),
        ("9:16", "9:16"),
        ("21:9", "21:9"),
        ("1.618:1", "1.618:1"),
    ]

    def __init__(self, callback: Optional[Callable[[str], None]] = None, **kwargs) -> None:
        super().__init__(**kwargs)

        self.callback = callback
        self._current_ratio = ""
        self._custom_ratio = None

        self.set_title(_("Aspect Ratio"))
        self.set_activatable(True)

        suffix_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)

        self.value_label = Gtk.Label(label="Auto")
        suffix_box.append(self.value_label)

        self.dropdown_arrow = Gtk.Image.new_from_icon_name("pan-down-symbolic")
        suffix_box.append(self.dropdown_arrow)

        self.add_suffix(suffix_box)

        self._setup_popover()
        self.connect("activated", self._on_row_activated)

    def do_get_property(self, prop):
        if prop.name == 'aspect-ratio':
            return self._current_ratio
        else:
            raise AttributeError('unknown property %s' % prop.name)

    def do_set_property(self, prop, value):
        if prop.name == 'aspect-ratio':
            self.set_ratio(value)
        else:
            raise AttributeError('unknown property %s' % prop.name)

    def _setup_popover(self) -> None:
        self.popover = Gtk.Popover()
        self.popover.set_parent(self.dropdown_arrow)
        self.popover.set_has_arrow(True)
        self.popover.set_autohide(True)

        main_box = Gtk.Box(
            orientation=Gtk.Orientation.VERTICAL, spacing=12, margin_start=8,
            margin_end=8, margin_top=8, margin_bottom=8
            )
        grid = Gtk.Grid()
        grid.set_row_spacing(8)
        grid.set_column_spacing(8)
        grid.set_column_homogeneous(True)

        row = 0
        col = 0
        for label, value in self.PRESET_RATIOS:
            button = Gtk.Button(label=label)
            button.add_css_class("flat")
            button.set_size_request(80, 36)
            button.connect("clicked", lambda b, v=value, l=label: self._on_preset_selected(v, l))

            grid.attach(button, col, row, 1, 1)

            col += 1
            if col >= 2:
                col = 0
                row += 1

        main_box.append(grid)
        main_box.append(Gtk.Separator())

        custom_label = Gtk.Label(label=_("Custom Ratio"))
        custom_label.set_halign(Gtk.Align.START)
        custom_label.add_css_class("heading")
        main_box.append(custom_label)

        inputs_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)

        width_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        width_label = Gtk.Label(label=_("Width"))
        width_label.set_halign(Gtk.Align.START)
        width_label.add_css_class("caption")
        self.width_input = Gtk.Entry()
        self.width_input.set_input_purpose(Gtk.InputPurpose.NUMBER)
        self.width_input.set_max_length(4)
        self.width_input.set_width_chars(7)
        self.width_input.set_max_width_chars(5)
        width_box.append(width_label)
        width_box.append(self.width_input)

        colon_label = Gtk.Label(label=":")
        colon_label.set_valign(Gtk.Align.END)
        colon_label.set_margin_bottom(8)

        height_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        height_label = Gtk.Label(label=_("Height"))
        height_label.set_halign(Gtk.Align.START)
        height_label.add_css_class("caption")
        self.height_input = Gtk.Entry()
        self.height_input.set_input_purpose(Gtk.InputPurpose.NUMBER)
        self.height_input.set_max_length(4)
        self.height_input.set_width_chars(7)
        self.height_input.set_max_width_chars(5)
        height_box.append(height_label)
        height_box.append(self.height_input)

        inputs_box.append(width_box)
        inputs_box.append(colon_label)
        inputs_box.append(height_box)
        main_box.append(inputs_box)

        set_button = Gtk.Button(label=_("Set"))
        set_button.add_css_class("suggested-action")
        set_button.connect("clicked", self._on_custom_ratio_set)
        main_box.append(set_button)

        self.popover.set_child(main_box)

    def _on_row_activated(self, row) -> None:
        self.popover.popup()

    def _on_preset_selected(self, value: str, label: str) -> None:
        self._current_ratio = value
        self.value_label.set_text(label)
        self._emit_ratio_changed(value)
        self.notify('aspect-ratio')
        self.popover.popdown()

    def _on_custom_ratio_set(self, button: Gtk.Button) -> None:
        width_text = self.width_input.get_text().strip()
        height_text = self.height_input.get_text().strip()

        if not width_text.isdigit() or not height_text.isdigit():
            return

        width = int(width_text)
        height = int(height_text)

        if width <= 0 or height <= 0:
            return

        custom_ratio = f"{width}:{height}"
        self._custom_ratio = custom_ratio
        self._current_ratio = custom_ratio

        self.value_label.set_text(custom_ratio)
        self._emit_ratio_changed(custom_ratio)
        self.notify('aspect-ratio')
        self.popover.popdown()

    def _emit_ratio_changed(self, ratio: str) -> None:
        self.emit('ratio-changed', ratio)
        if self.callback:
            self.callback(ratio)

    def set_ratio(self, ratio: str) -> None:
        self._current_ratio = ratio

        for label, value in self.PRESET_RATIOS:
            if value == ratio:
                self.value_label.set_text(label)
                self.notify('aspect-ratio')
                return

        if ratio and ":" in ratio:
            self._custom_ratio = ratio
            self.value_label.set_text(ratio)
            parts = ratio.split(":")
            if len(parts) == 2:
                self.width_input.set_text(parts[0])
                self.height_input.set_text(parts[1])

        self.notify('aspect-ratio')

    def get_ratio(self) -> str:
        return self._current_ratio

    def dispose(self) -> None:
        if self.popover:
            self.popover.unparent()
        super().dispose()
