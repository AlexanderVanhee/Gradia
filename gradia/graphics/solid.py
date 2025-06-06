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

from collections.abc import Callable
from typing import Optional
from PIL import Image
from gi.repository import Gtk, Gdk, Adw
from gradia.graphics.background import Background


class SolidBackground(Background):

    def __init__(self, color: str = "#4A90E2", alpha: float = 1.0) -> None:
        self.color = color
        self.alpha = alpha

    def get_name(self) -> str:
        return f"solid-{self.color}-{self.alpha}"

    def _hex_to_rgb(self, hex_color: str) -> tuple[int, int, int]:
        hex_color = hex_color.lstrip('#')
        return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))

    def prepare_image(self, width: int, height: int) -> Image.Image:
        rgb = self._hex_to_rgb(self.color)
        alpha_value = int(self.alpha * 255)
        return Image.new('RGBA', (width, height), (*rgb, alpha_value))


class SolidSelector:

    COMMON_COLORS = [
        "#ffffff",
        "#000000",
        "#f66151",
        "#33d17a",
        "#3584e4",
        "#f6d32d",
        "#c061cb",
        "#33c7de"
    ]

    def __init__(
        self,
        solid: SolidBackground,
        callback: Optional[Callable[[SolidBackground], None]] = None
    ) -> None:
        self.solid = solid
        self.callback = callback
        self.color_button: Optional[Gtk.ColorButton] = None
        self.widget = self._build()

    def _build(self) -> Adw.PreferencesGroup:
        group = Adw.PreferencesGroup(title=_("Solid Color Background"))
        group.add(self._color_row())
        group.add(self._common_colors_row())
        return group

    def _color_row(self) -> Adw.ActionRow:
        row = Adw.ActionRow(title=_("Color"))
        rgba = self._hex_alpha_to_rgba(self.solid.color, self.solid.alpha)
        self.color_button = Gtk.ColorButton(
            rgba=rgba,
            use_alpha=True,
            valign=Gtk.Align.CENTER
        )
        self.color_button.connect("color-set", self._on_color_changed)
        row.add_suffix(self.color_button)
        return row

    def _common_colors_row(self) -> Adw.ActionRow:
        row = Adw.ActionRow()
        row.set_activatable(False)
        row.set_selectable(False)

        grid = Gtk.Grid()
        grid.set_valign(Gtk.Align.CENTER)
        grid.set_halign(Gtk.Align.CENTER)
        grid.set_row_spacing(6)
        grid.set_column_spacing(6)

        columns = 4

        for index, color in enumerate(self.COMMON_COLORS):
            button = Gtk.Button()
            button.set_valign(Gtk.Align.CENTER)
            button.set_size_request(32, 32)
            button.set_margin_top(7)
            button.set_margin_bottom(6.95)

            rgba = self._hex_alpha_to_rgba(color, 1.0)
            css = f"""
            button {{
                background-color: {rgba.to_string()};
                border-radius: 50%;
                border: 1px solid @borders;
            }}
            """

            style_provider = Gtk.CssProvider()
            style_provider.load_from_data(css.encode())
            Gtk.StyleContext.add_provider(
                button.get_style_context(),
                style_provider,
                Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
            )
            button.connect("clicked", self._on_common_color_clicked, color)

            row_pos = index // columns
            col_pos = index % columns
            grid.attach(button, col_pos, row_pos, 1, 1)

        row.set_child(grid)
        return row

    def _on_common_color_clicked(self, button: Gtk.Button, color: str) -> None:
        self.solid.color = color
        self.solid.alpha = 1.0
        if self.color_button:
            self.color_button.set_rgba(self._hex_alpha_to_rgba(color, 1.0))
        if self.callback:
            self.callback(self.solid)

    def _on_color_changed(self, button: Gtk.ColorButton) -> None:
        rgba = button.get_rgba()
        self.solid.color = self._rgba_to_hex(rgba)
        self.solid.alpha = rgba.alpha
        if self.callback:
            self.callback(self.solid)

    def _hex_alpha_to_rgba(self, hex_color: str, alpha: float) -> Gdk.RGBA:
        rgba = Gdk.RGBA()
        rgba.parse(hex_color)
        rgba.alpha = alpha
        return rgba

    def _rgba_to_hex(self, rgba: Gdk.RGBA) -> str:
        r = int(rgba.red * 255)
        g = int(rgba.green * 255)
        b = int(rgba.blue * 255)
        return f"#{r:02x}{g:02x}{b:02x}"
