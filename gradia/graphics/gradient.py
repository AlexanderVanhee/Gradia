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

from collections.abc import Callable
import ctypes
import json
from ctypes import CDLL, POINTER, c_double, c_int, c_uint8
from typing import Optional

from PIL import Image
from gi.repository import Adw, Gtk

from gradia.app_constants import PREDEFINED_GRADIENTS
from gradia.graphics.background import Background
from gradia.utils.colors import HexColor, hex_to_rgb, rgba_to_hex, hex_to_rgba
from gradia.constants import rootdir  # pyright: ignore


CacheKey = tuple[str, str, int, int, int]
GradientPreset = tuple[str, str, int]
CacheInfo = dict[str, int | list[CacheKey] | bool]


class GradientBackground(Background):
    _MAX_CACHE_SIZE: int = 100
    _gradient_cache: dict[CacheKey, Image.Image] = {}
    _c_lib: Optional[CDLL | bool] = None

    @classmethod
    def _load_c_lib(cls) -> None:
        if cls._c_lib:
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
        except Exception:
            cls._c_lib = False

    def __init__(
        self,
        start_color: HexColor = "#4A90E2",
        end_color: HexColor = "#50E3C2",
        angle: int = 0
    ) -> None:
        self.start_color: HexColor = start_color
        self.end_color: HexColor = end_color
        self.angle: int = angle
        self._load_c_lib()

    @classmethod
    def from_json(cls, json_str: str) -> 'GradientBackground':
        data = json.loads(json_str)
        return cls(
            start_color=data.get('start_color', "#4A90E2"),
            end_color=data.get('end_color', "#50E3C2"),
            angle=data.get('angle', 0)
        )

    def get_name(self) -> str:
        return f"gradient-{self.start_color}-{self.end_color}-{self.angle}"

    def _generate_gradient_c(self, width: int, height: int) -> Image.Image:
        if not self._c_lib or self._c_lib is False:
            raise RuntimeError("C gradient library not loaded")

        start_rgb = hex_to_rgb(self.start_color)
        end_rgb = hex_to_rgb(self.end_color)
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
    def to_json(self) -> str:
        return json.dumps({
            'start_color': self.start_color,
            'end_color': self.end_color,
            'angle': self.angle
        })

@Gtk.Template(resource_path=f"{rootdir}/ui/selectors/gradient_selector.ui")
class GradientSelector(Adw.PreferencesGroup):
    __gtype_name__ = "GradiaGradientSelector"

    start_color_button: Gtk.Button = Gtk.Template.Child()
    end_color_button: Gtk.Button = Gtk.Template.Child()
    gradient_preview_box: Gtk.Box = Gtk.Template.Child()

    angle_spin_row: Adw.SpinRow = Gtk.Template.Child()
    angle_adjustment: Gtk.Adjustment = Gtk.Template.Child()

    gradient_popover: Gtk.Popover = Gtk.Template.Child()
    popover_flowbox: Gtk.FlowBox = Gtk.Template.Child()

    def __init__(
        self,
        gradient: GradientBackground,
        callback: Optional[Callable[[GradientBackground], None]] = None,
        **kwargs
    ) -> None:
        super().__init__(**kwargs)

        self.gradient: GradientBackground = gradient
        self.callback: Optional[Callable[[GradientBackground], None]] = callback

        self.start_color_dialog = Gtk.ColorDialog()
        self.end_color_dialog = Gtk.ColorDialog()

        self._setup_popover()
        self._setup()

    """
    Setup Methods
    """
    def _setup_popover(self) -> None:
        for i, (start, end, angle) in enumerate(PREDEFINED_GRADIENTS):
            gradient_name = f"gradient-preview-{i}"

            button = Gtk.Button(
                name=gradient_name,
                focusable=False,
                can_focus=False,
                width_request=60,
                height_request=40
            )
            button.add_css_class("gradient-preset")

            self._apply_gradient_to_preset_button(button, start, end, angle)

            button.connect("clicked", self._on_gradient_selected, start, end, angle)
            self.popover_flowbox.append(button)
            self.gradient_popover.set_position(Gtk.PositionType.TOP)

    def _apply_gradient_to_preset_button(self, button: Gtk.Button, start: str, end: str, angle: int) -> None:
        css = f"""
            button.gradient-preset {{
                background-image: linear-gradient({angle}deg, {start}, {end});
            }}
        """

        css_provider = Gtk.CssProvider()
        css_provider.load_from_string(css)
        button.get_style_context().add_provider(
            css_provider,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION + 3
        )

    def _setup(self) -> None:
        self.angle_adjustment.set_value(self.gradient.angle)
        self._update_gradient_preview()
        self._update_color_button_styles()

    def _update_gradient_preview(self) -> None:
        css = f"""
            .gradient-preview {{
                background-image: linear-gradient({self.gradient.angle}deg, {self.gradient.start_color}, {self.gradient.end_color});
            }}
        """
        css_provider = Gtk.CssProvider()
        css_provider.load_from_string(css)
        self.gradient_preview_box.get_style_context().add_provider(
            css_provider,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION + 1
        )

    def _update_color_button_styles(self) -> None:
        start_css = f"""
            button.gradient-color-picker:nth-child(1) {{
                background-color: {self.gradient.start_color};
            }}
        """
        start_css_provider = Gtk.CssProvider()
        start_css_provider.load_from_string(start_css)
        start_context = self.start_color_button.get_style_context()
        start_context.add_provider(start_css_provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION + 2)

        if self.is_light_color(self.gradient.start_color):
            start_context.add_class("dark")
        else:
            start_context.remove_class("dark")

        end_css = f"""
            button.gradient-color-picker:nth-child(2) {{
                background-color: {self.gradient.end_color};
            }}
        """
        end_css_provider = Gtk.CssProvider()
        end_css_provider.load_from_string(end_css)
        end_context = self.end_color_button.get_style_context()
        end_context.add_provider(end_css_provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION + 2)

        if self.is_light_color(self.gradient.end_color):
            end_context.add_class("dark")
        else:
            end_context.remove_class("dark")

    """
    Callbacks
    """
    @Gtk.Template.Callback()
    def _on_start_color_button_clicked(self, button: Gtk.Button) -> None:
        self.start_color_dialog.choose_rgba(
            parent=self.get_root(),
            initial_color=hex_to_rgba(self.gradient.start_color),
            callback=self._on_start_color_selected
        )

    @Gtk.Template.Callback()
    def _on_end_color_button_clicked(self, button: Gtk.Button) -> None:
        self.end_color_dialog.choose_rgba(
            parent=self.get_root(),
            initial_color=hex_to_rgba(self.gradient.end_color),
            callback=self._on_end_color_selected
        )

    def _on_start_color_selected(self, dialog: Gtk.ColorDialog, result) -> None:
        try:
            rgba = dialog.choose_rgba_finish(result)
            self.gradient.start_color = rgba_to_hex(rgba)
            self._update_gradient_preview()
            self._update_color_button_styles()
            self._notify()
        except Exception:
            pass

    def _on_end_color_selected(self, dialog: Gtk.ColorDialog, result) -> None:
        try:
            rgba = dialog.choose_rgba_finish(result)
            self.gradient.end_color = rgba_to_hex(rgba)
            self._update_gradient_preview()
            self._update_color_button_styles()
            self._notify()
        except Exception:
            pass

    def is_light_color(self, hex_color: str) -> bool:
        hex_color = hex_color.lstrip("#")
        r, g, b = [int(hex_color[i:i + 2], 16) for i in (0, 2, 4)]
        luminance = 0.299 * r + 0.587 * g + 0.114 * b
        return luminance > 200

    @Gtk.Template.Callback()
    def _on_angle_output(self, row: Adw.SpinRow, *args) -> None:
        self.gradient.angle = int(row.get_value())
        self._update_gradient_preview()
        self._notify()

    def _on_gradient_selected(self, _button: Gtk.Button, start: HexColor, end: HexColor, angle: int) -> None:
        self.gradient.start_color = start
        self.gradient.end_color = end
        self.gradient.angle = angle

        self.angle_spin_row.set_value(angle)

        self._update_gradient_preview()
        self._update_color_button_styles()
        self._notify()

        self.gradient_popover.popdown()


    """
    Internal Methods
    """

    def _notify(self) -> None:
        if self.callback:
            self.callback(self.gradient)

