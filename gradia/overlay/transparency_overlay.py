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
        self.drawing_area_widget: Gtk.DrawingArea | None = None
        self.square_size = 20

    def _on_draw(self, area: Gtk.DrawingArea, context: cairo.Context, width: int, height: int, user_data: Any) -> None:
        if not self.drawing_area_widget:
            return

        offset_x, offset_y, display_width, display_height = self._get_image_bounds()
        light_gray = (0.9, 0.9, 0.9)
        dark_gray = (0.7, 0.7, 0.7)

        start_x = max(0, int(offset_x))
        start_y = max(0, int(offset_y))
        end_x = min(width, int(offset_x + display_width))
        end_y = min(height, int(offset_y + display_height))

        if start_x >= end_x or start_y >= end_y:
            return

        for y in range(start_y, end_y, self.square_size):
            for x in range(start_x, end_x, self.square_size):
                square_x = (x - int(offset_x)) // self.square_size
                square_y = (y - int(offset_y)) // self.square_size
                is_light = (square_x + square_y) % 2 == 0
                color = light_gray if is_light else dark_gray

                context.set_source_rgb(*color)
                square_w = min(self.square_size, end_x - x)
                square_h = min(self.square_size, end_y - y)
                context.rectangle(x, y, square_w, square_h)
                context.fill()

    def set_picture_reference(self, drawing_area: Gtk.DrawingArea) -> None:
        if self.drawing_area_widget:
            try:
                self.drawing_area_widget.disconnect_by_func(self._on_drawing_area_changed)
            except:
                pass

        self.drawing_area_widget = drawing_area

        if drawing_area:
            drawing_area.connect("notify", self._on_drawing_area_changed)
            drawing_area.connect("realize", self._on_drawing_area_changed)
            drawing_area.connect("unrealize", self._on_drawing_area_changed)

        self.queue_draw()

    def _on_drawing_area_changed(self, *args) -> None:
        self.queue_draw()

    def _get_image_bounds(self) -> tuple[float, float, float, float]:
        if not self.drawing_area_widget or not hasattr(self.drawing_area_widget, 'get_allocated_width'):
            return 0, 0, self.get_width(), self.get_height()

        if hasattr(self.drawing_area_widget, 'get_root') and self.drawing_area_widget.get_root():
            main_window = self.drawing_area_widget.get_root()
            if hasattr(main_window, 'processed_surface') and main_window.processed_surface:
                img_w = main_window.processed_surface.get_width()
                img_h = main_window.processed_surface.get_height()
            else:
                return 0, 0, self.drawing_area_widget.get_allocated_width(), self.drawing_area_widget.get_allocated_height()
        else:
            return 0, 0, self.drawing_area_widget.get_allocated_width(), self.drawing_area_widget.get_allocated_height()

        widget_w = self.drawing_area_widget.get_allocated_width()
        widget_h = self.drawing_area_widget.get_allocated_height()

        if img_w <= 0 or img_h <= 0:
            return 0, 0, widget_w, widget_h

        scale = min(widget_w / img_w, widget_h / img_h)
        disp_w = img_w * scale
        disp_h = img_h * scale
        offset_x = (widget_w - disp_w) / 2
        offset_y = (widget_h - disp_h) / 2

        return offset_x, offset_y, disp_w, disp_h
