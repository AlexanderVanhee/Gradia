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

from typing import Any

import cairo
from gi.repository import Gtk

class TransparencyBackground(Gtk.DrawingArea):
    __gtype_name__ = "GradiaTransparencyBackground"

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)

        self.set_draw_func(self._on_draw, None)

        self.picture_widget: Gtk.Picture | None = None
        self.square_size = 20

    """
    Callbacks
    """

    def _on_draw(self, _area: Gtk.DrawingArea, context: cairo.Context, _width: int, _height: int, _user_data: Any) -> None:
        """Draw checkerboard pattern only within image bounds"""

        offset_x, offset_y, display_width, display_height = self._get_image_bounds()

        light_gray = (0.9, 0.9, 0.9)
        dark_gray = (0.7, 0.7, 0.7)

        start_x = int(offset_x)
        start_y = int(offset_y)
        end_x = int(offset_x + display_width)
        end_y = int(offset_y + display_height)

        for y in range(start_y, end_y, self.square_size):
            for x in range(start_x, end_x, self.square_size):
                square_x = (x - start_x) // self.square_size
                square_y = (y - start_y) // self.square_size
                is_light = (square_x + square_y) % 2 == 0

                color = light_gray if is_light else dark_gray
                context.set_source_rgb(*color)

                square_w = min(self.square_size, end_x - x)
                square_h = min(self.square_size, end_y - y)

                context.rectangle(x, y, square_w, square_h)
                context.fill()

    """
    Public Methods
    """

    def set_picture_reference(self, picture: Gtk.Picture) -> None:
        self.picture_widget = picture
        if picture:
            picture.connect("notify::paintable", lambda *args: self.queue_draw())

    """
    Private Methods
    """

    def _get_image_bounds(self) -> tuple[float, float, float, float]:
        if not self.picture_widget or not self.picture_widget.get_paintable():
            return 0, 0, self.get_width(), self.get_height()

        widget_width = self.picture_widget.get_width()
        widget_height = self.picture_widget.get_height()
        image_width = self.picture_widget.get_paintable().get_intrinsic_width()
        image_height = self.picture_widget.get_paintable().get_intrinsic_height()

        if image_width <= 0 or image_height <= 0:
            return 0, 0, widget_width, widget_height

        scale = min(widget_width / image_width, widget_height / image_height)
        display_width = image_width * scale
        display_height = image_height * scale
        offset_x = (widget_width - display_width) / 2
        offset_y = (widget_height - display_height) / 2

        return offset_x, offset_y, display_width, display_height
