# Copyright (C) 2025 Alexander Vanhee, tfuxu
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <https://www.gnu.org/licenses/>.
#
# SPDX-License-Identifier: GPL-3.0-or-later
from typing import Any
from gi.repository import Gtk, Gdk, Graphene

class TransparencyBackground(Gtk.Widget):
    __gtype_name__ = "GradiaTransparencyBackground"

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self.picture_widget: Gtk.Picture | None = None
        self.square_size = 20

    def do_snapshot(self, snapshot: Gtk.Snapshot) -> None:
        offset_x, offset_y, display_width, display_height = self._get_image_bounds()

        light_gray = Gdk.RGBA(red=0.9, green=0.9, blue=0.9, alpha=1.0)
        dark_gray = Gdk.RGBA(red=0.7, green=0.7, blue=0.7, alpha=1.0)

        start_x = int(offset_x)
        start_y = int(offset_y)
        end_x = int(offset_x + display_width)
        end_y = int(offset_y + display_height)

        bg_rect = Graphene.Rect.alloc().init(start_x, start_y, display_width, display_height)
        snapshot.append_color(light_gray, bg_rect)

        scale = 1.0
        if self.picture_widget and self.picture_widget.get_paintable():
            image_width = self.picture_widget.get_paintable().get_intrinsic_width()
            image_height = self.picture_widget.get_paintable().get_intrinsic_height()
            if image_width > 0 and image_height > 0:
                scale = min(display_width / image_width, display_height / image_height)

        if scale > 0:
            square_size_scaled = self.square_size * scale
            num_cols = int(display_width // square_size_scaled) + 1
            num_rows = int(display_height // square_size_scaled) + 1

            for row in range(num_rows):
                for col in range(num_cols):
                    if (row + col) % 2 == 1:
                        square_x = start_x + col * square_size_scaled
                        square_y = start_y + row * square_size_scaled
                        square_w = min(square_size_scaled, end_x - square_x)
                        square_h = min(square_size_scaled, end_y - square_y)

                        if square_w > 0 and square_h > 0:
                            square_rect = Graphene.Rect.alloc().init(square_x, square_y, square_w, square_h)
                            snapshot.append_color(dark_gray, square_rect)


    def set_picture_reference(self, picture: Gtk.Picture) -> None:
        self.picture_widget = picture
        if picture:
            picture.connect("notify::paintable", lambda *args: self.queue_draw())

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
