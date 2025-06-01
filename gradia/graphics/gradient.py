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

import ctypes
from ctypes import c_int, c_double, c_uint8, POINTER, CDLL
from collections.abc import Callable
from typing import Optional
from PIL import Image
from gi.repository import Gtk, Gdk, Adw
from gradia.constants import PREDEFINED_GRADIENTS


HexColor = str
RGBTuple = tuple[int, int, int]
CacheKey = tuple[str, str, int, int, int]
GradientPreset = tuple[str, str, int]
CacheInfo = dict[str, int | list[CacheKey] | bool]


class GradientBackground:
    _MAX_CACHE_SIZE: int = 100
    _gradient_cache: dict[CacheKey, Image.Image] = {}
    _c_lib: Optional[CDLL | bool] = None

    @classmethod
    def _load_c_lib(cls) -> None:
        if cls._c_lib :
            return
        
        try:
            from importlib.resources import files
            gradia_path = files('gradia').joinpath('libgradient_gen.so')
            cls._c_lib = ctypes.CDLL(str(gradia_path))

            cls._c_lib.generate_gradient.argtypes = [
                POINTER(c_uint8), c_int, c_int,
                c_int, c_int, c_int,
                c_int, c_int, c_int,
                c_double
            ]
            cls._c_lib.generate_gradient.restype = None
        except Exception as e:
            cls._c_lib = False

    def __init__(self, start_color: HexColor = "#4A90E2", end_color: HexColor = "#50E3C2", angle: int = 0) -> None:
        self.start_color: HexColor = start_color
        self.end_color: HexColor = end_color
        self.angle: int = angle
        self._load_c_lib()

    def get_name(self) -> str:
        return f"gradient-{self.start_color}-{self.end_color}-{self.angle}"

    def _hex_to_rgb(self, hex_color: HexColor) -> RGBTuple:
        hex_color = hex_color.lstrip('#')
        r, g, b = (int(hex_color[i:i+2], 16) for i in (0, 2, 4))
        return (r, g, b)

    def _generate_gradient_c(self, width: int, height: int) -> Image.Image:
        if not self._c_lib or self._c_lib is False:
            raise RuntimeError("C gradient library not loaded")

        start_rgb = self._hex_to_rgb(self.start_color)
        end_rgb = self._hex_to_rgb(self.end_color)
        pixel_count = width * height * 4
        pixel_buffer = (c_uint8 * pixel_count)()

        self._c_lib.generate_gradient(
            pixel_buffer, width, height,
            start_rgb[0], start_rgb[1], start_rgb[2],
            end_rgb[0], end_rgb[1], end_rgb[2],
            float(self.angle)
        )

        return Image.frombytes('RGBA', (width, height), bytes(pixel_buffer))

    def prepare_image(self, width: int, height: int) -> Image.Image:
        cache_key: CacheKey = (self.start_color, self.end_color, self.angle, width, height)

        if cache_key in self._gradient_cache:
            return self._gradient_cache[cache_key].copy()

        self._evict_cache_if_needed()

        image = self._generate_gradient_c(width, height)
        self._gradient_cache[cache_key] = image.copy()
        return image

    def _evict_cache_if_needed(self) -> None:
        if len(self._gradient_cache) >= self._MAX_CACHE_SIZE:
            keys_to_remove = list(self._gradient_cache.keys())[:self._MAX_CACHE_SIZE // 2]
            for key in keys_to_remove:
                del self._gradient_cache[key]

    @classmethod
    def clear_cache(cls) -> None:
        cls._gradient_cache.clear()

    @classmethod
    def get_cache_info(cls) -> CacheInfo:
        return {
            'cache_size': len(cls._gradient_cache),
            'max_cache_size': cls._MAX_CACHE_SIZE,
            'cached_gradients': list(cls._gradient_cache.keys()),
            'c_lib_loaded': cls._c_lib is not None and cls._c_lib is not False
        }


class GradientSelector:

    def __init__(
        self, 
        gradient: GradientBackground, 
        callback: Optional[Callable[[GradientBackground], None]] = None
    ) -> None:
        self.gradient: GradientBackground = gradient
        self.callback: Optional[Callable[[GradientBackground], None]] = callback
        self.popover: Optional[Gtk.Popover] = None
        self.start_color_button: Optional[Gtk.ColorButton] = None
        self.end_color_button: Optional[Gtk.ColorButton] = None
        self.angle_spin_row: Optional[Adw.SpinRow] = None
        self.widget: Adw.PreferencesGroup = self._build()

    def _build(self) -> Adw.PreferencesGroup:
        group = Adw.PreferencesGroup(title=_("Gradient Background"))
        
        icon_button = Gtk.Button(
            icon_name="columns-symbolic",
            tooltip_text=_("Gradient Presets"),
            valign=Gtk.Align.CENTER,
            focusable=False,
            can_focus=False
        )
        icon_button.connect("clicked", self._show_popover)
        icon_button.get_style_context().add_class("flat")
        group.set_header_suffix(icon_button)

        group.add(self._color_row(_("Start Color"), self.gradient.start_color, self._on_start))
        group.add(self._color_row(_("End Color"), self.gradient.end_color, self._on_end))
        group.add(self._angle_row())

        return group

    def _color_row(self, label: str, value: HexColor, handler: Callable[[Gtk.ColorButton], None]) -> Adw.ActionRow:
        row = Adw.ActionRow(title=label)
        button = self._color_button(value, handler)
        row.add_suffix(button)

        if label == _("Start Color"):
            self.start_color_button = button
        elif label == _("End Color"):
            self.end_color_button = button

        return row

    def _color_button(self, hex_color: HexColor, handler: Callable[[Gtk.ColorButton], None]) -> Gtk.ColorButton:
        rgba = self._hex_to_rgba(hex_color)
        button = Gtk.ColorButton(
            rgba=rgba,
            valign=Gtk.Align.CENTER,
            focusable=False,
            can_focus=False
        )
        button.connect("color-set", handler)
        return button

    def _angle_row(self) -> Adw.SpinRow:
        adj = Gtk.Adjustment(
            value=self.gradient.angle, 
            lower=0, 
            upper=360, 
            step_increment=45
        )

        row = Adw.SpinRow(title=_("Angle"), numeric=True, adjustment=adj)
        row.connect("output", self._on_angle)

        self.angle_spin_row = row
        return row

    def _on_start(self, button: Gtk.ColorButton) -> None:
        self.gradient.start_color = self._rgba_to_hex(button.get_rgba())
        self._notify()

    def _on_end(self, button: Gtk.ColorButton) -> None:
        self.gradient.end_color = self._rgba_to_hex(button.get_rgba())
        self._notify()

    def _on_angle(self, row: Adw.SpinRow) -> None:
        self.gradient.angle = int(row.get_value())
        self._notify()

    def _notify(self) -> None:
        if self.callback :
            self.callback(self.gradient)

    def _hex_to_rgba(self, hex_color: HexColor) -> Gdk.RGBA:
        rgba = Gdk.RGBA()
        rgba.parse(hex_color)
        return rgba

    def _rgba_to_hex(self, rgba: Gdk.RGBA) -> HexColor:
        r = int(rgba.red * 255)
        g = int(rgba.green * 255)
        b = int(rgba.blue * 255)
        return f"#{r:02x}{g:02x}{b:02x}"

    def _show_popover(self, button: Gtk.Button) -> None:
        if self.popover :
            self.popover.popdown()
            self.popover = None

        self.popover = Gtk.Popover()
        if self.popover :
            self.popover.set_parent(button)
            self.popover.set_autohide(True)
            self.popover.set_has_arrow(True)

        flowbox = Gtk.FlowBox(
            max_children_per_line=3,
            selection_mode=Gtk.SelectionMode.NONE,
            valign=Gtk.Align.CENTER,
            margin_top=10,
            margin_bottom=10,
            margin_start=10,
            margin_end=10,
            row_spacing=10,
            column_spacing=10,
            homogeneous=True
        )

        for i, (start, end, angle) in enumerate(PREDEFINED_GRADIENTS):
            gradient_name = f"gradient-preview-{i}"

            css = f"""
                button#{gradient_name} {{
                    background-image: linear-gradient({angle}deg, {start}, {end});
                    min-width: 60px;
                    min-height: 40px;
                    background-size: cover;
                    border-radius: 10px;
                    border: 1px solid rgba(0,0,0,0.1);
                    transition: filter 0.3s ease;
                }}
                button#{gradient_name}:hover {{
                    filter: brightness(1.2);
                }}
            """
            css_provider = Gtk.CssProvider()
            css_provider.load_from_string(css)
            Gtk.StyleContext.add_provider_for_display(
                Gdk.Display.get_default(),
                css_provider,
                Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
            )

            button_widget = Gtk.Button(name=gradient_name, focusable=False, can_focus=False)
            button_widget.connect("clicked", self._on_gradient_selected, start, end, angle)
            flowbox.append(button_widget)

        if self.popover :
            self.popover.set_child(flowbox)
            self.popover.popup()

    def _on_gradient_selected(self, button: Gtk.Button, start: HexColor, end: HexColor, angle: int) -> None:
        self.gradient.start_color = start
        self.gradient.end_color = end
        self.gradient.angle = angle

        if self.start_color_button:
            self.start_color_button.set_rgba(self._hex_to_rgba(start))
        if self.end_color_button:
            self.end_color_button.set_rgba(self._hex_to_rgba(end))
        if self.angle_spin_row:
            self.angle_spin_row.set_value(angle)

        self._notify()

        if self.popover:
            self.popover.popdown()
            self.popover = None
