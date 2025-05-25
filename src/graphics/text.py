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

from PIL import Image, ImageDraw, ImageFont
import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Gtk, Gdk, Adw


class Text:
    """Represents text properties and provides functionality to draw text on an image."""

    VALID_GRAVITIES = [
        "northwest", "north", "northeast",
        "west", "center", "east",
        "southwest", "south", "southeast"
    ]

    def __init__(self, text, font_path=None, color="rgb(255,255,255)", size=42, gravity="south"):
        self.text = text
        self.font_path = font_path or "/usr/share/fonts/Adwaita/AdwaitaSans-Regular.ttf"
        self.color = color
        self.size = size
        self.gravity = gravity.lower() if gravity.lower() in self.VALID_GRAVITIES else "south"

    @classmethod
    def get_valid_gravities(cls):
        """Returns the list of valid gravity positions."""
        return cls.VALID_GRAVITIES.copy()

    def apply_to_image(self, img, padding=10):
        """Draw the text onto the provided PIL image with given padding."""
        if not self.text:
            return img

        draw = ImageDraw.Draw(img)
        font = self._load_font()
        fill_color = self._parse_color()
        position = self._calculate_position(draw, font, img.size, padding)

        draw.text(position, self.text, fill=fill_color, font=font)
        return img

    def _load_font(self):
        """Load the font from the font path or fall back to default."""
        try:
            return ImageFont.truetype(self.font_path, self.size)
        except Exception:
            return ImageFont.load_default()

    def _parse_color(self):
        """Parse the RGB color string into an (R, G, B) tuple."""
        if isinstance(self.color, str) and self.color.lower().startswith("rgb("):
            try:
                parts = self.color[4:-1].split(",")
                return tuple(int(p.strip()) for p in parts)
            except Exception:
                pass
        return (255, 255, 255)

    def _calculate_position(self, draw, font, image_size, padding):
        """Calculate the position where text should be drawn on the image."""
        width, height = image_size
        bbox = draw.textbbox((0, 0), self.text, font=font)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]
        offset = padding + 25

        x = self._calculate_horizontal_position(text_width, width, offset)
        y = self._calculate_vertical_position(text_height, height, offset)

        return x, y

    def _calculate_horizontal_position(self, text_width, image_width, offset):
        if "west" in self.gravity:
            return offset
        if "east" in self.gravity:
            return image_width - text_width - offset
        # center or any other case
        return (image_width - text_width) // 2

    def _calculate_vertical_position(self, text_height, image_height, offset):
        if "north" in self.gravity:
            return offset
        if "south" in self.gravity:
            return image_height - text_height - offset
        # center or any other case
        return (image_height - text_height) // 2


class TextSelector:
    GRAVITY_POSITIONS = [
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

    BUTTON_SIZE = 24
    GRID_ROW_SPACING = 6
    GRID_COL_SPACING = 6
    GRID_MARGIN = 6

    SIZE_SPIN_MIN = 10
    SIZE_SPIN_MAX = 100
    SIZE_SPIN_STEP = 1

    def __init__(self, text_obj: Text = None, callback=None):
        self.text_obj = text_obj or Text("")
        self.callback = callback

        self.widget = None
        self.text_entry = None
        self.color_button = None
        self.size_row = None
        self.gravity_buttons = {}
        self.gravity_popover = None
        self.gravity_display_button = None

        self.widget, self.text_entry, self.color_button, self.size_row = self._build_ui()

    def _build_ui(self):
        group = Adw.PreferencesGroup(title="Text Annotation")
        self._build_text_entry(group)
        self._build_color_button(group)
        self._build_size_spin(group)
        self._build_gravity_selector(group)
        return group, self.text_entry, self.color_button, self.size_row

    def _build_text_entry(self, parent):
        row = Adw.ActionRow(title="Text")
        self.text_entry = Gtk.Entry(placeholder_text="Enter text")
        self.text_entry.set_text(self.text_obj.text)
        self.text_entry.set_valign(Gtk.Align.CENTER)
        self.text_entry.connect("changed", self._on_text_changed)
        row.add_suffix(self.text_entry)
        parent.add(row)

    def _build_color_button(self, parent):
        row = Adw.ActionRow(title="Color")
        self.color_button = Gtk.ColorButton()
        rgba = Gdk.RGBA()
        rgba.parse(self.text_obj.color)
        self.color_button.set_valign(Gtk.Align.CENTER)
        self.color_button.set_rgba(rgba)
        self.color_button.connect("color-set", self._on_color_changed)
        row.add_suffix(self.color_button)
        parent.add(row)

    def _build_size_spin(self, parent):
        row = Adw.SpinRow.new_with_range(
            self.SIZE_SPIN_MIN, self.SIZE_SPIN_MAX, self.SIZE_SPIN_STEP
        )

        row.set_title("Size")
        row.set_value(self.text_obj.size)
        row.connect("output", self._on_size_changed)

        self.size_row = row
        parent.add(row)

    def _build_gravity_selector(self, parent):
        action_row = Adw.ActionRow(title="Location")
        self.gravity_display_button = Gtk.Button()
        self.gravity_display_button.set_valign(Gtk.Align.CENTER)
        self._update_gravity_button_display()
        self.gravity_display_button.connect("clicked", self._on_gravity_display_clicked)
        action_row.add_suffix(self.gravity_display_button)
        parent.add(action_row)

    def _on_gravity_display_clicked(self, button):
        if self.gravity_popover:
            self.gravity_popover.popdown()
            self.gravity_popover.unparent()
            self.gravity_popover = None

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

        self.gravity_popover.set_child(grid)
        self.gravity_popover.set_parent(button)
        self.gravity_popover.popup()


    def _on_gravity_button_clicked(self, button, gravity):
        for btn in self.gravity_buttons.values():
            btn.remove_css_class("suggested-action")
        button.add_css_class("suggested-action")
        self.text_obj.gravity = gravity
        self._update_gravity_button_display()
        if self.gravity_popover:
            self.gravity_popover.popdown()
            self.gravity_popover = None
        self._notify_change()

    def _update_gravity_button_display(self):
        icon_name = next(
            (icon for gravity, icon, _, _ in self.GRAVITY_POSITIONS if gravity == self.text_obj.gravity),
            "arrow1-down-symbolic",
        )
        box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        icon = Gtk.Image.new_from_icon_name(icon_name)
        box.append(icon)
        label = Gtk.Label(label=self.text_obj.gravity.title())
        box.append(label)
        self.gravity_display_button.set_child(box)

    def _on_text_changed(self, entry):
        self.text_obj.text = entry.get_text()
        self._notify_change()

    def _on_color_changed(self, button):
        rgba = button.get_rgba()
        self.text_obj.color = f"rgb({int(rgba.red * 255)},{int(rgba.green * 255)},{int(rgba.blue * 255)})"
        self._notify_change()

    def _on_size_changed(self, row: Adw.SpinRow):
        self.text_obj.size = int(row.get_value())
        self._notify_change()

    def _notify_change(self):
        if self.callback:
            self.callback(self.text_obj)
