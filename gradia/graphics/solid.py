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
from typing import Optional
import json
from PIL import Image
from gi.repository import Adw, Gtk

from gradia.graphics.background import Background
from gradia.utils.colors import hex_to_rgb, hex_to_rgba, rgba_to_hex, is_light_color
from gradia.constants import rootdir  # pyright: ignore


class SolidBackground(Background):
    def __init__(self, color: str = "#4A90E2", alpha: float = 1.0) -> None:
        self.color = color
        self.alpha = alpha

    @classmethod
    def from_json(cls, json_str: str) -> 'SolidBackground':
        data = json.loads(json_str)
        return cls(
            color=data.get("color", "#4A90E2"),
            alpha=data.get("alpha", 1.0)
        )

    def to_json(self) -> str:
        return json.dumps({
            "type": "solid",
            "color": self.color,
            "alpha": self.alpha
        })

    def get_name(self) -> str:
        return f"solid-{self.color}-{self.alpha}"

    def prepare_image(self, width: int, height: int) -> Image.Image:
        rgb = hex_to_rgb(self.color)
        alpha_value = int(self.alpha * 255)
        return Image.new('RGBA', (width, height), (*rgb, alpha_value))


class ColorPresetButton(Gtk.Button):
    def __init__(self, color: str, alpha: float = 1.0, **kwargs) -> None:
        super().__init__(
            valign=Gtk.Align.CENTER,
            width_request=40,
            height_request=40,
            margin_top=6,
            margin_bottom=6,
            margin_start=6,
            margin_end=6,
            **kwargs
        )
        self.set_focusable(True)
        self.set_can_focus(True)
        self.color = color
        self.alpha = alpha
        self.is_selected = False
        self._apply_style()
        self._setup_checkmark()

    def _apply_style(self) -> None:
        context = self.get_style_context()
        context.add_class("color-button")
        if self.alpha == 0.0:
            context.add_class("transparent-color-button")
        else:
            rgba = hex_to_rgba(self.color, self.alpha)
            provider = Gtk.CssProvider()
            provider.load_from_string(f"""
                button {{
                    background-color: {rgba.to_string()};
                }}
            """)
            context.add_provider(provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)

    def _setup_checkmark(self) -> None:
        self.checkmark = Gtk.Image.new_from_icon_name("object-select-symbolic")
        self.checkmark.set_pixel_size(16)
        self.checkmark.add_css_class("checkmark-icon")

        if is_light_color(self.color):
            self.checkmark.add_css_class("dark")
        else:
             self.checkmark.remove_css_class("dark")

        overlay = Gtk.Overlay(width_request=16, height_request=16)
        overlay.set_child(Gtk.Box())
        overlay.add_overlay(self.checkmark)
        overlay.set_halign(Gtk.Align.CENTER)
        overlay.set_valign(Gtk.Align.CENTER)

        self.set_child(overlay)

    def set_selected(self, selected: bool) -> None:
        self.is_selected = selected
        if selected:
             self.checkmark.add_css_class("visible")
        else:
            self.checkmark.remove_css_class("visible")

@Gtk.Template(resource_path=f"{rootdir}/ui/selectors/solid_selector.ui")
class SolidSelector(Adw.PreferencesGroup):
    __gtype_name__ = "GradiaSolidSelector"
    COMMON_COLORS = [
        "#ffffffff",  # White
        "#fff66151",  # Red
        "#ffe66100",  # Orange
        "#fff6d32d",  # Yellow
        "#ff77767b",  # Gray
        "#ff000000",  # Black
        "#ff33d17a",  # Green
        "#ff3584e4",  # Blue
        "#ffc061cb",  # Purple
        "#00000000"   # Transparent
    ]


    color_button: Gtk.ColorDialogButton = Gtk.Template.Child()
    color_presets_grid: Gtk.Grid = Gtk.Template.Child()

    def __init__(
        self,
        solid: SolidBackground,
        callback: Optional[Callable[[SolidBackground], None]] = None,
        **kwargs
    ) -> None:
        super().__init__(**kwargs)
        self.solid = solid
        self.callback = callback
        self.preset_buttons = []
        self._setup_color_row()
        self._setup_color_presets_row()
        self._update_selected_preset()

    def _setup_color_row(self) -> None:
        self.color_button.set_rgba(hex_to_rgba(self.solid.color, self.solid.alpha))

    def _setup_color_presets_row(self) -> None:
        columns = 5
        for index, color in enumerate(self.COMMON_COLORS):
            hex_color = color.lstrip('#')
            if len(hex_color) == 8:
                alpha_from_hex = int(hex_color[:2], 16) / 255.0
                rgb_hex = hex_color[2:]
            else:
                alpha_from_hex = 1.0
                rgb_hex = hex_color

            full_color = f"#{rgb_hex}"
            button = ColorPresetButton(full_color, alpha_from_hex)
            button.connect("clicked", self._on_common_color_clicked, full_color, alpha_from_hex)

            row_pos = index // columns
            col_pos = index % columns
            self.color_presets_grid.attach(button, col_pos, row_pos, 1, 1)
            self.preset_buttons.append(button)

    def _update_selected_preset(self) -> None:
        current_color = self.solid.color.lower()
        current_alpha = self.solid.alpha

        for button in self.preset_buttons:
            is_match = (button.color.lower() == current_color and
                       abs(button.alpha - current_alpha) < 0.01)
            button.set_selected(is_match)

    @Gtk.Template.Callback()
    def _on_color_changed(self, button: Gtk.ColorDialogButton, *args) -> None:
        rgba = button.get_rgba()
        self.solid.color = rgba_to_hex(rgba)
        self.solid.alpha = rgba.alpha
        self._update_selected_preset()
        if self.callback:
            self.callback(self.solid)

    def _on_common_color_clicked(self, _button: Gtk.Button, color: str, alpha: float) -> None:
        self.solid.color = color
        self.solid.alpha = alpha
        self.color_button.set_rgba(hex_to_rgba(color, alpha))
        self._update_selected_preset()
        if self.callback:
            self.callback(self.solid)

