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
    def highlighter_size(self) -> float:
        return self._settings.get_double("highlighter-size")

    @highlighter_size.setter
    def highlighter_size(self, value: float) -> None:
        self._settings.set_double("highlighter-size", value)

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

    @property
    def show_close_confirm_dialog(self) -> bool:
        return self._settings.get_boolean("show-close-confirm-dialog")

    @property
    def custom_export_command(self) -> str:
        return self._settings.get_string("custom-export-command")

    @custom_export_command.setter
    def custom_export_command(self, value: str) -> None:
        self._settings.set_string("custom-export-command", value)

    @property
    def provider_name(self) -> str:
        return self._settings.get_string("provider-name")

    @provider_name.setter
    def provider_name(self, value:str) -> None:
        self._settings.set_string("provider-name", value)

    @property
    def show_export_confirm_dialog(self) -> bool:
        return self._settings.get_boolean("show-export-confirm-dialog")

    @property
    def image_padding(self) -> int:
        return self._settings.get_int("image-padding")

    @image_padding.setter
    def image_padding(self, value: int) -> None:
        self._settings.set_int("image-padding", value)

    @property
    def image_corner_radius(self) -> int:
        return self._settings.get_int("image-corner-radius")

    @image_corner_radius.setter
    def image_corner_radius(self, value: int) -> None:
        self._settings.set_int("image-corner-radius", value)

    @property
    def image_aspect_ratio(self) -> str:
        return self._settings.get_string("image-aspect-ratio")

    @image_aspect_ratio.setter
    def image_aspect_ratio(self, value: str) -> None:
        self._settings.set_string("image-aspect-ratio", value)

    @property
    def image_shadow_strength(self) -> int:
        return self._settings.get_int("image-shadow-strength")

    @image_shadow_strength.setter
    def image_shadow_strength(self, value: int) -> None:
        self._settings.set_int("image-shadow-strength", value)

    @property
    def image_auto_balance(self) -> bool:
        return self._settings.get_boolean("image-auto-balance")

    @image_auto_balance.setter
    def image_auto_balance(self, value: bool) -> None:
        self._settings.set_boolean("image-auto-balance", value)

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

    def bind_adjustment(self, adjustment: Gtk.Adjustment, key: str) -> None:
        if key in self._settings.list_keys():
            self._settings.bind(
                key,
                adjustment,
                "value",
                Gio.SettingsBindFlags.DEFAULT
            )
        else:
            print(f"Warning: GSettings key '{key}' not found in schema.")

    def bind_scale(self, scale: Gtk.Scale, key: str) -> None:
        if key in self._settings.list_keys():
            self._settings.bind(
                key,
                scale.get_adjustment(),
                "value",
                Gio.SettingsBindFlags.DEFAULT
            )
        else:
            print(f"Warning: GSettings key '{key}' not found in schema.")

    def bind_spin_row(self, spin_row: object, key: str) -> None:
        if key in self._settings.list_keys():
            self._settings.bind(
                key,
                spin_row,
                "value",
                Gio.SettingsBindFlags.DEFAULT
            )
        else:
            print(f"Warning: GSettings key '{key}' not found in schema.")
