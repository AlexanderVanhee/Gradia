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

from __future__ import annotations

from PIL import Image, ImageDraw, ImageFont
from PIL.ImageFont import FreeTypeFont

from gi.repository import Gtk, Gdk, Adw

from typing import Optional, Callable, Union


class Text:
    """Represents text properties and provides functionality to draw text on an image."""

    VALID_GRAVITIES: list[str] = [
        "northwest", "north", "northeast",
        "west", "center", "east",
        "southwest", "south", "southeast"
    ]
    
    DEFAULT_FONT_PATH: str = "/usr/share/fonts/Adwaita/AdwaitaSans-Regular.ttf"

    def __init__(
        self, 
        text: str, 
        font_path: str = "", 
        color: str = "rgb(255,255,255)", 
        size: int = 42, 
        gravity: str = "south"
    ) -> None:
        self.text = text
        self.font_path = font_path or self.DEFAULT_FONT_PATH
        self.color = color
        self.size = size
        self.gravity = gravity.lower() if gravity.lower() in self.VALID_GRAVITIES else "south"

    @classmethod
    def get_valid_gravities(cls) -> list[str]:
        """Returns the list of valid gravity positions."""
        return cls.VALID_GRAVITIES.copy()

    def apply_to_image(self, img: Image.Image, padding: int = 10) -> Image.Image:
        """Draw the text onto the provided PIL image with given padding."""
        if not self.text:
            return img

        draw = ImageDraw.Draw(img)
        font = self._load_font()
        fill_color = self._parse_color()
        position = self._calculate_position(draw, font, img.size, padding)

        draw.text(position, self.text, fill=fill_color, font=font)
        return img

    def _load_font(self) -> Union[FreeTypeFont, ImageFont.ImageFont]:
        """Load the font from the font path or fall back to default."""
        try:
            return ImageFont.truetype(self.font_path, self.size)
        except Exception:
            return ImageFont.load_default()

    def _parse_color(self) -> tuple[int, int, int]:
        """Parse the RGB color string into an (R, G, B) tuple."""
        if isinstance(self.color, str) and self.color.lower().startswith("rgb("):
            try:
                parts = self.color[4:-1].split(",")
                r, g, b = (int(p.strip()) for p in parts[:3])
                return (r, g, b)
            except Exception:
                pass
        return (255, 255, 255)

    def _calculate_position(
        self, 
        draw: ImageDraw.ImageDraw, 
        font: Union[FreeTypeFont, ImageFont.ImageFont], 
        image_size: tuple[int, int], 
        padding: int
    ) -> tuple[int, int]:
        """Calculate the position where text should be drawn on the image."""
        width, height = image_size
        bbox = draw.textbbox((0, 0), self.text, font=font)
        text_width = int(bbox[2] - bbox[0])
        text_height = int(bbox[3] - bbox[1])
        offset = padding + 25

        x = self._calculate_horizontal_position(text_width, width, offset)
        y = self._calculate_vertical_position(text_height, height, offset)

        return x, y

    def _calculate_horizontal_position(self, text_width: int, image_width: int, offset: int) -> int:
        if "west" in self.gravity:
            return offset
        if "east" in self.gravity:
            return image_width - text_width - offset
        # center or any other case
        return (image_width - text_width) // 2

    def _calculate_vertical_position(self, text_height: int, image_height: int, offset: int) -> int:
        if "north" in self.gravity:
            return offset
        if "south" in self.gravity:
            return image_height - text_height - offset
        # center or any other case
        return (image_height - text_height) // 2


TextChangedCallback = Callable[[Text], None]


class TextSelector:
    GRAVITY_POSITIONS: list[tuple[str, str, int, int]] = [
        ("northwest", "arrow1-top-left-symbolic", 0, 0),
        ("north", "arrow1-up-symbolic", 1, 0),
        ("northeast", "arrow1-top-right-symbolic", 2, 0),
        ("west", "arrow1-left-symbolic", 0, 1),
        ("center", "circle-anchor-center-symbolic", 1, 1),
        ("east", "arrow1-right-symbolic", 2, 1),
        ("southwest", "arrow1-bottom-left-symbolic", 0, 2),
        ("south", "arrow1-down-symbolic", 1, 2),
        ("southeast", "arrow1-bottom-right-symbolic", 2, 2),
    ]

    BUTTON_SIZE: int = 24
    GRID_ROW_SPACING: int = 6
    GRID_COL_SPACING: int = 6
    GRID_MARGIN: int = 6

    SIZE_SPIN_MIN: int = 10
    SIZE_SPIN_MAX: int = 100
    SIZE_SPIN_STEP: int = 1

    def __init__(self, text_obj: Text | None = None, callback: TextChangedCallback | None = None) -> None:
        self.text_obj = text_obj if text_obj is not None else Text("")
        self.callback = callback
        self.gravity_buttons: dict[str, Gtk.Button] = {}
        self.gravity_popover: Gtk.Popover | None = None

        # Build UI and initialize all widgets
        self.widget, self.text_entry, self.color_button, self.size_row = self._build_ui()
        
        # gravity_display_button is guaranteed to be set by _build_gravity_selector
        self.gravity_display_button: Gtk.Button

    def _build_ui(self) -> tuple[Adw.PreferencesGroup, Gtk.Entry, Gtk.ColorButton, Adw.SpinRow]:
        group = Adw.PreferencesGroup(title=_("Text Annotation"))
        text_entry = self._build_text_entry(group)
        color_button = self._build_color_button(group)
        size_row = self._build_size_spin(group)
        self._build_gravity_selector(group)
        return group, text_entry, color_button, size_row

    def _build_text_entry(self, parent: Adw.PreferencesGroup) -> Gtk.Entry:
        row = Adw.ActionRow(title=_("Text"))
        text_entry = Gtk.Entry(placeholder_text=_("Enter text"))
        text_entry.set_text(self.text_obj.text)
        text_entry.set_valign(Gtk.Align.CENTER)
        text_entry.connect("changed", self._on_text_changed)
        row.add_suffix(text_entry)
        parent.add(row)
        return text_entry

    def _build_color_button(self, parent: Adw.PreferencesGroup) -> Gtk.ColorButton:
        row = Adw.ActionRow(title=_("Color"))
        color_button = Gtk.ColorButton()
        rgba = Gdk.RGBA()
        rgba.parse(self.text_obj.color)
        color_button.set_valign(Gtk.Align.CENTER)
        color_button.set_rgba(rgba)
        color_button.connect("color-set", self._on_color_changed)
        row.add_suffix(color_button)
        parent.add(row)
        return color_button

    def _build_size_spin(self, parent: Adw.PreferencesGroup) -> Adw.SpinRow:
        size_row = Adw.SpinRow.new_with_range(
            self.SIZE_SPIN_MIN, self.SIZE_SPIN_MAX, self.SIZE_SPIN_STEP
        )

        size_row.set_title(_("Size"))
        size_row.set_value(self.text_obj.size)
        size_row.connect("output", self._on_size_changed)

        parent.add(size_row)
        return size_row

    def _build_gravity_selector(self, parent: Adw.PreferencesGroup) -> None:
        action_row = Adw.ActionRow(title=_("Location"))
        self.gravity_display_button = Gtk.Button()
        self.gravity_display_button.set_valign(Gtk.Align.CENTER)
        self._update_gravity_button_display()
        self.gravity_display_button.connect("clicked", self._on_gravity_display_clicked)
        action_row.add_suffix(self.gravity_display_button)
        parent.add(action_row)

    def _on_gravity_display_clicked(self, button: Gtk.Button) -> None:
        self._close_existing_popover()
        self._create_and_show_popover(button)

    def _close_existing_popover(self) -> None:
        if self.gravity_popover is not None:
            self.gravity_popover.popdown()
            self.gravity_popover.unparent()
            self.gravity_popover = None

    def _create_and_show_popover(self, button: Gtk.Button) -> None:
        self.gravity_popover = Gtk.Popover()

        grid = Gtk.Grid(
            row_spacing=self.GRID_ROW_SPACING,
            column_spacing=self.GRID_COL_SPACING,
            margin_top=self.GRID_MARGIN,
            margin_bottom=self.GRID_MARGIN,
            margin_start=self.GRID_MARGIN,
            margin_end=self.GRID_MARGIN,
        )

        self.gravity_buttons = {}

        for gravity, icon_name, col, grid_row in self.GRAVITY_POSITIONS:
            b = Gtk.Button.new_from_icon_name(icon_name=icon_name)
            b.set_size_request(self.BUTTON_SIZE, self.BUTTON_SIZE)
            b.add_css_class("flat")

            if gravity == self.text_obj.gravity:
                b.add_css_class("suggested-action")

            b.connect("clicked", self._on_gravity_button_clicked, gravity)
            grid.attach(b, col, grid_row, 1, 1)
            self.gravity_buttons[gravity] = b

        if self.gravity_popover is not None:
            self.gravity_popover.set_child(grid)
            self.gravity_popover.set_parent(button)
            self.gravity_popover.popup()

    def _on_gravity_button_clicked(self, button: Gtk.Button, gravity: str) -> None:
        self._clear_gravity_button_selection()
        button.add_css_class("suggested-action")
        self.text_obj.gravity = gravity
        self._update_gravity_button_display()
        self._close_existing_popover()
        self._notify_change()

    def _clear_gravity_button_selection(self) -> None:
        for btn in self.gravity_buttons.values():
            btn.remove_css_class("suggested-action")

    def _update_gravity_button_display(self) -> None:
        icon_name = self._get_gravity_icon_name()
        box = self._create_gravity_button_content(icon_name)
        self.gravity_display_button.set_child(box)

    def _get_gravity_icon_name(self) -> str:
        return next(
            (icon for gravity, icon, _, _ in self.GRAVITY_POSITIONS if gravity == self.text_obj.gravity),
            "arrow1-down-symbolic",
        )

    def _create_gravity_button_content(self, icon_name: str) -> Gtk.Box:
        box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        icon = Gtk.Image.new_from_icon_name(icon_name)
        box.append(icon)
        label = Gtk.Label(label=self.text_obj.gravity.title())
        box.append(label)
        return box

    def _on_text_changed(self, entry: Gtk.Entry) -> None:
        self.text_obj.text = entry.get_text()
        self._notify_change()

    def _on_color_changed(self, button: Gtk.ColorButton) -> None:
        rgba = button.get_rgba()
        self.text_obj.color = f"rgb({int(rgba.red * 255)},{int(rgba.green * 255)},{int(rgba.blue * 255)})"
        self._notify_change()

    def _on_size_changed(self, row: Adw.SpinRow) -> None:
        self.text_obj.size = int(row.get_value())
        self._notify_change()

    def _notify_change(self) -> None:
        if self.callback is not None:
            self.callback(self.text_obj)