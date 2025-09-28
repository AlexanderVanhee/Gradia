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
        self.square_size = 10
        self.max_tiles_x = 20
        self.max_tiles_y = 20

    def do_snapshot(self, snapshot: Gtk.Snapshot) -> None:
        offset_x, offset_y, display_width, display_height, square_size_scaled = self._calculate_geometry()

        if display_width <= 0 or display_height <= 0:
            return

        light_gray = Gdk.RGBA(red=0.9, green=0.9, blue=0.9, alpha=1.0)
        dark_gray = Gdk.RGBA(red=0.7, green=0.7, blue=0.7, alpha=1.0)

        bounds = Graphene.Rect.alloc().init(offset_x, offset_y, display_width, display_height)
        snapshot.append_color(light_gray, bounds)

        tile_size = 2 * square_size_scaled
        child_bounds = Graphene.Rect.alloc().init(offset_x, offset_y, tile_size, tile_size)

        snapshot.push_repeat(bounds, child_bounds)
        dark_square_1 = Graphene.Rect.alloc().init(offset_x + square_size_scaled, offset_y,
                                                  square_size_scaled, square_size_scaled)
        snapshot.append_color(dark_gray, dark_square_1)

        dark_square_2 = Graphene.Rect.alloc().init(offset_x, offset_y + square_size_scaled,
                                                  square_size_scaled, square_size_scaled)
        snapshot.append_color(dark_gray, dark_square_2)
        snapshot.pop()

    def set_picture_reference(self, picture: Gtk.Picture) -> None:
        self.picture_widget = picture
        if picture:
            picture.connect("notify::paintable", lambda *args: self.queue_draw())

    def _calculate_geometry(self) -> tuple[float, float, float, float, float]:
        offset_x, offset_y, display_width, display_height = self._get_image_bounds()

        scale = 1.0
        if self.picture_widget and self.picture_widget.get_paintable():
            image_width = self.picture_widget.get_paintable().get_intrinsic_width()
            image_height = self.picture_widget.get_paintable().get_intrinsic_height()
            if image_width > 0 and image_height > 0:
                scale = min(display_width / image_width, display_height / image_height)

        if scale <= 0:
            return offset_x, offset_y, display_width, display_height, 0

        max_tile_width = display_width / self.max_tiles_x
        max_tile_height = display_height / self.max_tiles_y
        square_size_scaled = max(self.square_size * scale, max_tile_width, max_tile_height)

        return offset_x, offset_y, display_width, display_height, square_size_scaled

    def _get_image_bounds(self) -> tuple[float, float, float, float]:
        if not self.picture_widget or not self.picture_widget.get_paintable():
            inset = 2
            return inset, inset, self.get_width() - 2*inset, self.get_height() - 2*inset

        widget_width = self.picture_widget.get_width()
        widget_height = self.picture_widget.get_height()
        image_width = self.picture_widget.get_paintable().get_intrinsic_width()
        image_height = self.picture_widget.get_paintable().get_intrinsic_height()

        if image_width <= 0 or image_height <= 0:
            inset = 2
            return inset, inset, widget_width - 2*inset, widget_height - 2*inset

        scale = min(widget_width / image_width, widget_height / image_height)
        display_width = image_width * scale
        display_height = image_height * scale

        offset_x = (widget_width - display_width) / 2
        offset_y = (widget_height - display_height) / 2

        inset = 2
        return offset_x + inset, offset_y + inset, display_width - 2*inset, display_height - 2*inset
