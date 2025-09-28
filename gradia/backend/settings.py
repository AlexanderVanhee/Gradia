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

from gi.repository import Gio, Gdk, Gtk, GLib
from gradia.constants import app_id

class Settings:
    def __init__(self) -> None:
        self._settings = Gio.Settings.new(app_id)

    """
    Getters/Setters
    """

    @property
    def draw_mode(self) -> str:
        return self._settings.get_string("draw-mode")

    @draw_mode.setter
    def draw_mode(self, value: str) -> None:
        self._settings.set_string("draw-mode", value)

    def get_tool_config_item(self, key: str) -> str | None:
        tool_config = self.get_tool_config()
        return tool_config.get(key)

    def set_tool_config_item(self, key: str, value: str) -> None:
        tool_config = self.get_tool_config()
        tool_config[key] = value
        variant = GLib.Variant("a{ss}", tool_config)
        self._settings.set_value("tool-config", variant)

    def get_tool_config(self) -> dict[str, str]:
        variant = self._settings.get_value("tool-config")
        result = {}

        for i in range(variant.n_children()):
            entry = variant.get_child_value(i)

            key_variant = entry.get_child_value(0)
            value_variant = entry.get_child_value(1)

            key = key_variant.unpack()
            value = value_variant.unpack()

            result[key] = value

        return result


    @property
    def screenshot_folder(self) -> str:
        value = self._settings.get_string("screenshot-folder")
        return None if value == "" else value

    @screenshot_folder.setter
    def screenshot_folder(self, value: str) -> None:
        self._settings.set_string("screenshot-folder", value)

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
    def exit_method(self) -> str:
        value = self._settings.get_string("exit-method")
        if value in ("confirm", "copy", "none"):
            return value
        return "confirm"

    @exit_method.setter
    def exit_method(self, value: str) -> None:
        if value not in ("confirm", "copy", "none"):
            value = "confirm"
        self._settings.set_string("exit-method", value)

    @property
    def overwrite_screenshot(self) -> bool:
        return self._settings.get_boolean("overwrite-screenshot")

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

    @property
    def image_rotation(self) -> int:
        return self._settings.get_int("image-rotation")

    @image_rotation.setter
    def image_rotation(self, value: int) -> None:
        self._settings.set_int("image-rotation", value)

    @property
    def image_options_lock(self) -> bool:
        return self._settings.get_boolean("image-options-lock")

    @image_options_lock.setter
    def image_options_lock(self, value: bool) -> None:
        self._settings.set_boolean("image-options-lock", value)

    @property
    def background_mode(self) -> str:
        return self._settings.get_string("background-mode")

    @background_mode.setter
    def background_mode(self, value: str) -> None:
        self._settings.set_string("background-mode", value)

    @property
    def solid_state(self) -> str:
        return self._settings.get_string("solid-state")

    @solid_state.setter
    def solid_state(self, value: str) -> None:
        self._settings.set_string("solid-state", value)

    @property
    def gradient_state(self) -> str:
        return self._settings.get_string("gradient-state")

    @gradient_state.setter
    def gradient_state(self, value: str) -> None:
        self._settings.set_string("gradient-state", value)

    @property
    def image_state(self) -> str:
        return self._settings.get_string("image-state")

    @image_state.setter
    def image_state(self, value: str) -> None:
        self._settings.set_string("image-state", value)

    @property
    def source_snippet_language(self) -> str:
        return self._settings.get_string("source-snippet-language")

    @source_snippet_language.setter
    def source_snippet_language(self, value: str) -> None:
        self._settings.set_string("source-snippet-language", value)

    @property
    def source_snippet_code_text(self) -> str:
        return self._settings.get_string("source-snippet-code-text")

    @source_snippet_code_text.setter
    def source_snippet_code_text(self, value: str) -> None:
        self._settings.set_string("source-snippet-code-text", value)

    @property
    def source_snippet_title(self) -> str:
        return self._settings.get_string("source-snippet-title")

    @source_snippet_title.setter
    def source_snippet_title(self, value: str) -> None:
        self._settings.set_string("source-snippet-title", value)

    @property
    def source_snippet_style_scheme(self) -> str:
        return self._settings.get_string("source-snippet-style-scheme")

    @source_snippet_style_scheme.setter
    def source_snippet_style_scheme(self, value: str) -> None:
        self._settings.set_string("source-snippet-style-scheme", value)

    @property
    def trained_data(self) -> str:
        return self._settings.get_string("trained-data")

    @trained_data.setter
    def trained_data(self, value: str) -> None:
        self._settings.set_string("trained-data", value)

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

    def bind_toggle_group(self, toggle_group, key: str):
        if key not in self._settings.list_keys():
            print(f"Warning: GSettings key '{key}' not found in schema.")
            return

        current = self._settings.get_string(key)
        toggle_group.set_active_name(current)

        def on_toggle_group_changed(toggle_group):
            self._settings.set_string(key, toggle_group.get_active_name())

        toggle_group.connect("notify::active-name", lambda w, p: on_toggle_group_changed(w))
