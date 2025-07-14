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
from gradia.utils.colors import hex_to_rgb, hex_to_rgba, rgba_to_hex
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


@Gtk.Template(resource_path=f"{rootdir}/ui/selectors/solid_selector.ui")
class SolidSelector(Adw.PreferencesGroup):
    __gtype_name__ = "GradiaSolidSelector"

    CHECKER_LIGHT = "#a8a8a8"
    CHECKER_DARK = "#545454"

    COMMON_COLORS = [
        "#ffffffff",
        "#ff000000",
        "#fff66151",
        "#ff33d17a",
        "#ff3584e4",
        "#fff6d32d",
        "#ffc061cb",
        "#00000000"
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

        self._setup_color_row()
        self._setup_color_presets_row()

    """
    Setup Methods
    """

    def _setup_color_row(self) -> None:
        self.color_button.set_rgba(hex_to_rgba(self.solid.color, self.solid.alpha))

    def _setup_color_presets_row(self) -> None:
        columns = 4
        for index, color in enumerate(self.COMMON_COLORS):
            button = Gtk.Button(
                valign=Gtk.Align.CENTER,
                width_request=32,
                height_request=32,
                margin_top=7,
                margin_bottom=7
            )

            hex_color = color.lstrip('#')

            if len(hex_color) == 8:
                alpha_from_hex = int(hex_color[:2], 16) / 255.0
                rgb_hex = hex_color[2:]
            else:
                alpha_from_hex = 1.0
                rgb_hex = hex_color

            if alpha_from_hex == 0.0:
                css = f"""
                button {{
                    background: linear-gradient(45deg, {self.CHECKER_DARK} 25%, transparent 25%),
                                linear-gradient(-45deg, {self.CHECKER_DARK} 25%, transparent 25%),
                                linear-gradient(45deg, transparent 75%, {self.CHECKER_DARK} 75%),
                                linear-gradient(-45deg, transparent 75%, {self.CHECKER_DARK} 75%);
                    background-size: 20px 20px;
                    background-position: 0 0, 0 10px, 10px -10px, -10px 0px;
                    border-radius: 50%;
                    border: 1px solid @borders;
                }}
                """
            else:
                rgba = hex_to_rgba(f"#{rgb_hex}", alpha_from_hex)
                css = f"""
                button {{
                    background-color: {rgba.to_string()};
                    border-radius: 50%;
                    border: 1px solid @borders;
                }}
                """

            style_provider = Gtk.CssProvider()
            style_provider.load_from_string(css)
            button.get_style_context().add_provider(
                style_provider,
                Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
            )

            button.connect("clicked", self._on_common_color_clicked, f"#{rgb_hex}", alpha_from_hex)

            row_pos = index // columns
            col_pos = index % columns
            self.color_presets_grid.attach(button, col_pos, row_pos, 1, 1)

    """
    Callbacks
    """

    @Gtk.Template.Callback()
    def _on_color_changed(self, button: Gtk.ColorDialogButton, *args) -> None:
        rgba = button.get_rgba()

        self.solid.color = rgba_to_hex(rgba)
        self.solid.alpha = rgba.alpha

        if self.callback:
            self.callback(self.solid)

    def _on_common_color_clicked(self, _button: Gtk.Button, color: str, alpha: float) -> None:
        self.solid.color = color
        self.solid.alpha = alpha

        self.color_button.set_rgba(hex_to_rgba(color, alpha))

        if self.callback:
            self.callback(self.solid)

    """
    Internal Methods
    """
