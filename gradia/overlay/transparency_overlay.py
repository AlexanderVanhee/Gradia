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

from gi.repository import Gtk

class TransparencyBackground(Gtk.DrawingArea):
    def __init__(self):
        super().__init__()
        self.set_draw_func(self._on_draw, None)
        self.picture_widget = None
        self.square_size = 20

    def set_picture_reference(self, picture):
        self.picture_widget = picture
        if picture:
            picture.connect("notify::paintable", lambda *args: self.queue_draw())

    def _get_image_bounds(self):
        if not self.picture_widget or not self.picture_widget.get_paintable():
            return 0, 0, self.get_width(), self.get_height()

        widget_w = self.picture_widget.get_width()
        widget_h = self.picture_widget.get_height()
        img_w = self.picture_widget.get_paintable().get_intrinsic_width()
        img_h = self.picture_widget.get_paintable().get_intrinsic_height()

        if img_w <= 0 or img_h <= 0:
            return 0, 0, widget_w, widget_h

        scale = min(widget_w / img_w, widget_h / img_h)
        disp_w = img_w * scale
        disp_h = img_h * scale
        offset_x = (widget_w - disp_w) / 2
        offset_y = (widget_h - disp_h) / 2

        return offset_x, offset_y, disp_w, disp_h

    def _on_draw(self, area, cr, width, height, user_data):
        """Draw checkerboard pattern only within image bounds"""
        offset_x, offset_y, disp_w, disp_h = self._get_image_bounds()

        light_gray = (0.9, 0.9, 0.9)
        dark_gray = (0.7, 0.7, 0.7)

        start_x = int(offset_x)
        start_y = int(offset_y)
        end_x = int(offset_x + disp_w)
        end_y = int(offset_y + disp_h)

        for y in range(start_y, end_y, self.square_size):
            for x in range(start_x, end_x, self.square_size):
                square_x = (x - start_x) // self.square_size
                square_y = (y - start_y) // self.square_size
                is_light = (square_x + square_y) % 2 == 0
                color = light_gray if is_light else dark_gray
                cr.set_source_rgb(*color)

                square_w = min(self.square_size, end_x - x)
                square_h = min(self.square_size, end_y - y)

                cr.rectangle(x, y, square_w, square_h)
                cr.fill()
