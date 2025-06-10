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
from ctypes import CDLL, POINTER, c_double, c_int, c_uint8
from typing import Optional

from PIL import Image
from gi.repository import Adw, Gtk

from gradia.constants import PREDEFINED_GRADIENTS
from gradia.utils.colors import HexColor, hex_to_rgb, hex_to_rgba, rgba_to_hex


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
        except Exception:
            cls._c_lib = False

    def __init__(self, start_color: HexColor = "#4A90E2", end_color: HexColor = "#50E3C2", angle: int = 0) -> None:
        self.start_color: HexColor = start_color
        self.end_color: HexColor = end_color
        self.angle: int = angle
        self._load_c_lib()

    @classmethod
    def fromIndex(cls, index: int) -> 'GradientBackground':
        if not (0 <= index < len(PREDEFINED_GRADIENTS)):
            raise IndexError(f"Gradient index {index} is out of range.")
        start_color, end_color, angle = PREDEFINED_GRADIENTS[index]
        return cls(start_color=start_color, end_color=end_color, angle=angle)

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


@Gtk.Template(resource_path="/be/alexandervanhee/gradia/ui/selectors/gradient_selector.ui")
class GradientSelector(Adw.PreferencesGroup):
    __gtype_name__ = "GradiaGradientSelector"

    start_color_button: Gtk.ColorDialogButton = Gtk.Template.Child()
    end_color_button: Gtk.ColorDialogButton = Gtk.Template.Child()

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
                can_focus=False
            )

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
            button.get_style_context().add_provider(
                css_provider,
                Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
            )

            button.connect("clicked", self._on_gradient_selected, start, end, angle)
            self.popover_flowbox.append(button)

    def _setup(self) -> None:
        # Set default values for angle adjustment and color buttons
        self.angle_adjustment.set_value(self.gradient.angle)

        self.start_color_button.set_rgba(hex_to_rgba(self.gradient.start_color))
        self.end_color_button.set_rgba(hex_to_rgba(self.gradient.end_color))

    """
    Callbacks
    """

    @Gtk.Template.Callback()
    def _on_start_color_set(self, button: Gtk.ColorButton, *args) -> None:
        self.gradient.start_color = rgba_to_hex(button.get_rgba())
        self._notify()

    @Gtk.Template.Callback()
    def _on_end_color_set(self, button: Gtk.ColorButton, *args) -> None:
        self.gradient.end_color = rgba_to_hex(button.get_rgba())
        self._notify()

    @Gtk.Template.Callback()
    def _on_angle_output(self, row: Adw.SpinRow, *args) -> None:
        self.gradient.angle = int(row.get_value())
        self._notify()

    def _on_gradient_selected(self, _button: Gtk.Button, start: HexColor, end: HexColor, angle: int) -> None:
        self.gradient.start_color = start
        self.gradient.end_color = end
        self.gradient.angle = angle

        self.start_color_button.set_rgba(hex_to_rgba(start))
        self.end_color_button.set_rgba(hex_to_rgba(end))
        self.angle_spin_row.set_value(angle)

        self._notify()

        self.gradient_popover.popdown()

    """
    Internal Methods
    """

    def _notify(self) -> None:
        if self.callback:
            self.callback(self.gradient)
