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
from gi.repository import Adw, Gtk, Gio, Gdk

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


class ColorPickerButton(Gtk.Button):
    def __init__(self, callback: Optional[Callable[[str, float], None]] = None, **kwargs) -> None:
        super().__init__(
            valign=Gtk.Align.CENTER,
            width_request=30,
            height_request=30,
            margin_top=6,
            margin_bottom=6,
            margin_start=6,
            margin_end=6,
            **kwargs
        )
        self.set_focusable(True)
        self.set_can_focus(True)
        self.callback = callback
        self.is_selected = False
        self._setup_icon()
        self._apply_style()

    def _setup_icon(self) -> None:
        self.checkmark = Gtk.Image.new_from_icon_name("object-select-symbolic")
        self.checkmark.set_pixel_size(16)
        self.checkmark.add_css_class("checkmark-icon")


        overlay = Gtk.Overlay(width_request=40, height_request=40)
        overlay.add_overlay(self.checkmark)
        overlay.set_halign(Gtk.Align.CENTER)
        overlay.set_valign(Gtk.Align.CENTER)

        self.set_child(overlay)

    def _apply_style(self) -> None:
        context = self.get_style_context()
        context.add_class("color-button")
        context.add_class("color-picker-button")

    def set_selected(self, selected: bool) -> None:
        self.is_selected = selected
        if selected:
            self.checkmark.add_css_class("visible")
        else:
            self.checkmark.remove_css_class("visible")

    def open_color_picker(self) -> None:
        dialog = Gtk.ColorDialog()
        dialog.choose_rgba(
            parent=self.get_root(),
            initial_color=Gdk.RGBA(red=0.5, green=0.5, blue=0.5, alpha=1.0),
            cancellable=None,
            callback=self._on_color_chosen
        )

    def _on_color_chosen(self, dialog: Gtk.ColorDialog, result: Gio.AsyncResult) -> None:
        try:
            rgba = dialog.choose_rgba_finish(result)
            color_hex = rgba_to_hex(rgba)
            alpha = rgba.alpha

            if self.callback:
                self.callback(color_hex, alpha)
        except Exception as e:
            print(f"Color picker cancelled or error: {e}")


@Gtk.Template(resource_path=f"{rootdir}/ui/selectors/solid_selector.ui")
class SolidSelector(Adw.PreferencesGroup):
    __gtype_name__ = "GradiaSolidSelector"
    COMMON_COLORS = [
        "#fff66151",  # Red
        "#ffe66100",  # Orange
        "#fff6d32d",  # Yellow
        "#ff33d17a",  # Green
        "#ff3584e4",  # Blue

        "#ffc061cb",  # Purple
        "#ffffd1dc",  # Pastel Pink
        "#fffff4d1",  # Pastel Yellow
        "#ffd1ffd1",  # Pastel Green
        "#ffd1f0ff",  # Pastel Cyan

        "#ffffffff",  # White
        "#ff000000",  # Black
        "#ff77767b",  # Gray
        "#00000000",  # Transparent
        "#00000000",  # Custom
    ]

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
        self.color_picker_button = None
        self.custom_color = None
        self.custom_alpha = 1.0
        self._setup_color_presets_row()
        self._update_selected_preset()

    def _setup_color_presets_row(self) -> None:
        columns = 5
        for index, color in enumerate(self.COMMON_COLORS):
            if index == 14:
                self.color_picker_button = ColorPickerButton(self._on_custom_color_picked)
                self.color_picker_button.connect("clicked", self._on_color_picker_clicked)

                row_pos = index // columns
                col_pos = index % columns
                self.color_presets_grid.attach(self.color_picker_button, col_pos, row_pos, 1, 1)
                continue

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

        if self.color_picker_button:
            is_custom_match = (self.custom_color and
                             self.custom_color.lower() == current_color and
                             abs(self.custom_alpha - current_alpha) < 0.01)
            self.color_picker_button.set_selected(is_custom_match)

    def _on_color_picker_clicked(self, button: ColorPickerButton) -> None:
        button.open_color_picker()

    def _on_custom_color_picked(self, color: str, alpha: float) -> None:
        self.custom_color = color
        self.custom_alpha = alpha
        self.solid.color = color
        self.solid.alpha = alpha
        self._update_selected_preset()
        if self.callback:
            self.callback(self.solid)

    def _on_common_color_clicked(self, _button: Gtk.Button, color: str, alpha: float) -> None:
        self.solid.color = color
        self.solid.alpha = alpha
        self._update_selected_preset()
        if self.callback:
            self.callback(self.solid)
