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
import cairo
from PIL import Image
from gi.repository import Adw, Gtk
import math
from gradia.app_constants import PREDEFINED_GRADIENTS
from gradia.graphics.background import Background
from gradia.utils.colors import HexColor, hex_to_rgb, rgba_to_hex, hex_to_rgba
from gradia.constants import rootdir  # pyright: ignore


CacheKey = tuple[str, str, int, int, int]
GradientPreset = tuple[str, str, int]
CacheInfo = dict[str, int | list[CacheKey] | bool]

class GradientBackground(Background):
    def __init__(
        self,
        start_color: HexColor = "#4A90E2",
        end_color: HexColor = "#50E3C2",
        angle: int = 0
    ) -> None:
        self.start_color: HexColor = start_color
        self.end_color: HexColor = end_color
        self.angle: int = angle

    @classmethod
    def fromIndex(cls, index: int) -> 'GradientBackground':
        if not (0 <= index < len(PREDEFINED_GRADIENTS)):
            raise IndexError(f"Gradient index {index} is out of range.")
        start_color, end_color, angle = PREDEFINED_GRADIENTS[index]
        return cls(start_color=start_color, end_color=end_color, angle=angle)

    def get_name(self) -> str:
        return f"gradient-{self.start_color}-{self.end_color}-{self.angle}"

    def prepare_cairo_surface(self, width: int, height: int) -> cairo.ImageSurface:
        """Create a Cairo surface with the gradient"""
        surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, width, height)
        ctx = cairo.Context(surface)

        start_rgb = hex_to_rgb(self.start_color)
        end_rgb = hex_to_rgb(self.end_color)

        start_r, start_g, start_b = start_rgb[0]/255, start_rgb[1]/255, start_rgb[2]/255
        end_r, end_g, end_b = end_rgb[0]/255, end_rgb[1]/255, end_rgb[2]/255

        angle_rad = math.radians(self.angle)

        if self.angle == 0:
            x0, y0, x1, y1 = 0, 0, width, 0
        elif self.angle == 90:
            x0, y0, x1, y1 = 0, 0, 0, height
        else:
            cx, cy = width / 2, height / 2
            length = max(width, height)
            dx = math.cos(angle_rad) * length / 2
            dy = math.sin(angle_rad) * length / 2
            x0, y0 = cx - dx, cy - dy
            x1, y1 = cx + dx, cy + dy

        pattern = cairo.LinearGradient(x0, y0, x1, y1)
        pattern.add_color_stop_rgb(0, start_r, start_g, start_b)
        pattern.add_color_stop_rgb(1, end_r, end_g, end_b)

        ctx.set_source(pattern)
        ctx.paint()

        return surface

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
