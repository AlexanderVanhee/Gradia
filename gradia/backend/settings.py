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

from gi.repository import Gio, Gdk, Gtk

class Settings:
    def __init__(self) -> None:
        self._settings = Gio.Settings.new("be.alexandervanhee.gradia")

    """
    Getters/Setters
    """

    @property
    def draw_mode(self) -> str:
        return self._settings.get_string("draw-mode")

    @draw_mode.setter
    def draw_mode(self, value: str) -> None:
        self._settings.set_string("draw-mode", value)

    @property
    def pen_color(self) -> Gdk.RGBA:
        return self._parse_rgba(
            self._settings.get_string("pen-color"),
            fallback=(1.0, 1.0, 1.0, 1.0)
        )

    @pen_color.setter
    def pen_color(self, value: Gdk.RGBA) -> None:
        self._settings.set_string("pen-color", self._rgba_to_string(value))

    @property
    def highlighter_color(self) -> Gdk.RGBA:
        return self._parse_rgba(
            self._settings.get_string("highlighter-color"),
            fallback=(1.0, 1.0, 0.0, 0.5)
        )

    @highlighter_color.setter
    def highlighter_color(self, value: Gdk.RGBA) -> None:
        self._settings.set_string("highlighter-color", self._rgba_to_string(value))

    @property
    def fill_color(self) -> Gdk.RGBA:
        return self._parse_rgba(
            self._settings.get_string("fill-color"),
            fallback=(0.0, 0.0, 0.0, 0.0)
        )

    @fill_color.setter
    def fill_color(self, value: Gdk.RGBA) -> None:
        self._settings.set_string("fill-color", self._rgba_to_string(value))

    @property
    def pen_size(self) -> float:
        return self._settings.get_double("pen-size")

    @pen_size.setter
    def pen_size(self, value: float) -> None:
        self._settings.set_double("pen-size", value)

    @property
    def number_radius(self) -> float:
        return self._settings.get_double("number-radius")

    @number_radius.setter
    def number_radius(self, value: float) -> None:
        self._settings.set_double("number-radius", value)

    @property
    def font(self) -> str:
        return self._settings.get_string("font")

    @font.setter
    def font(self, value: str) -> None:
        self._settings.set_string("font", value)

    @property
    def screenshot_subfolder(self) -> str:
        return self._settings.get_string("screenshot-subfolder")

    @screenshot_subfolder.setter
    def screenshot_subfolder(self, value: str) -> None:
        self._settings.set_string("screenshot-subfolder", value)

    """
    Internal Methods
    """

    def _parse_rgba(self, color_str: str, fallback: tuple[float, float, float, float]) -> Gdk.RGBA:
        rgba = Gdk.RGBA()

        try:
            parts = list(map(float, color_str.split(',')))

            if len(parts) == 4:
                rgba.red, rgba.green, rgba.blue, rgba.alpha = parts
            else:
                rgba.red, rgba.green, rgba.blue, rgba.alpha = fallback
        except (ValueError, IndexError):
            rgba.red, rgba.green, rgba.blue, rgba.alpha = fallback

        return rgba

    def _rgba_to_string(self, rgba: Gdk.RGBA) -> str:
        return f"{rgba.red:.3f},{rgba.green:.3f},{rgba.blue:.3f},{rgba.alpha:.3f}"

    @property
    def export_format(self) -> str:
        return self._settings.get_string("export-format")

    @export_format.setter
    def export_format(self, value: str) -> None:
        self._settings.set_string("export-format", value)

    @property
    def export_compress(self) -> bool:
        return self._settings.get_boolean("export-compress")

    @property
    def delete_screenshots_on_close(self) -> bool:
        return self._settings.get_boolean("trash-screenshots-on-close")

    def bind_switch(self, switch: Gtk.Switch, key: str) -> None:
        if key in self._settings.list_keys():
            self._settings.bind(
                key,
                switch,
                "active",
                Gio.SettingsBindFlags.DEFAULT
            )
        else:
            print(f"Warning: GSettings key '{key}' not found in schema.")
