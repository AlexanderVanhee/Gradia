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

from gi.repository import Gtk, Gdk, Gio, cairo
from typing import Tuple, List, Optional, Union
from enum import Enum
import math
import re

class DrawingMode(Enum):
    PEN = "pen"
    ARROW = "arrow"
    LINE = "line"
    SQUARE = "square"
    CIRCLE = "circle"
    TEXT = "text"

class DrawingAction:
    def draw(self, cr: cairo.Context, image_to_widget_coords, scale: float):
        raise NotImplementedError

class StrokeAction(DrawingAction):
    def __init__(self, stroke, color, pen_size):
        self.stroke = stroke
        self.color = color
        self.pen_size = pen_size

    def draw(self, cr, image_to_widget_coords, scale):
        if len(self.stroke) < 2:
            return
        coords = [image_to_widget_coords(x, y) for x, y in self.stroke]
        cr.set_source_rgba(*self.color)
        cr.set_line_width(self.pen_size * scale)
        cr.move_to(*coords[0])
        for point in coords[1:]:
            cr.line_to(*point)
        cr.stroke()

class ArrowAction(DrawingAction):
    def __init__(self, start, end, color, arrow_head_size):
        self.start = start
        self.end = end
        self.color = color
        self.arrow_head_size = arrow_head_size

    def draw(self, cr, image_to_widget_coords, scale):
        start_x, start_y = image_to_widget_coords(*self.start)
        end_x, end_y = image_to_widget_coords(*self.end)
        distance = math.hypot(end_x - start_x, end_y - start_y)
        if distance < 2:
            return
        cr.set_source_rgba(*self.color)
        cr.set_line_width(scale)
        cr.move_to(start_x, start_y)
        cr.line_to(end_x, end_y)
        cr.stroke()
        angle = math.atan2(end_y - start_y, end_x - start_x)
        head_len = min(self.arrow_head_size * scale, distance * 0.3)
        head_angle = math.pi / 6
        x1 = end_x - head_len * math.cos(angle - head_angle)
        y1 = end_y - head_len * math.sin(angle - head_angle)
        x2 = end_x - head_len * math.cos(angle + head_angle)
        y2 = end_y - head_len * math.sin(angle + head_angle)
        cr.move_to(end_x, end_y)
        cr.line_to(x1, y1)
        cr.move_to(end_x, end_y)
        cr.line_to(x2, y2)
        cr.stroke()

class LineAction(DrawingAction):
    def __init__(self, start, end, color, width):
        self.start = start
        self.end = end
        self.color = color
        self.width = width

    def draw(self, cr, image_to_widget_coords, scale):
        cr.set_source_rgba(*self.color)
        cr.set_line_width(self.width * scale)
        start_x, start_y = image_to_widget_coords(*self.start)
        end_x, end_y = image_to_widget_coords(*self.end)
        cr.move_to(start_x, start_y)
        cr.line_to(end_x, end_y)
        cr.stroke()

class RectAction(DrawingAction):
    def __init__(self, start, end, color, width, fill_color=None):
        self.start = start
        self.end = end
        self.color = color
        self.width = width
        self.fill_color = fill_color

    def draw(self, cr, image_to_widget_coords, scale):
        x1, y1 = image_to_widget_coords(*self.start)
        x2, y2 = image_to_widget_coords(*self.end)
        rect_x = min(x1, x2)
        rect_y = min(y1, y2)
        rect_w = abs(x2 - x1)
        rect_h = abs(y2 - y1)

        if self.fill_color:
            cr.set_source_rgba(*self.fill_color)
            cr.rectangle(rect_x, rect_y, rect_w, rect_h)
            cr.fill()

        cr.set_source_rgba(*self.color)
        cr.set_line_width(self.width * scale)
        cr.rectangle(rect_x, rect_y, rect_w, rect_h)
        cr.stroke()

class CircleAction(DrawingAction):
    def __init__(self, start, end, color, width, fill_color=None):
        self.start = start
        self.end = end
        self.color = color
        self.width = width
        self.fill_color = fill_color

    def draw(self, cr, image_to_widget_coords, scale):
        x1, y1 = image_to_widget_coords(*self.start)
        x2, y2 = image_to_widget_coords(*self.end)
        cx = (x1 + x2) / 2
        cy = (y1 + y2) / 2
        rx = abs(x2 - x1) / 2
        ry = abs(y2 - y1) / 2
        if rx < 1e-3 or ry < 1e-3:
            return

        cr.save()
        cr.translate(cx, cy)
        cr.scale(rx, ry)
        cr.arc(0, 0, 1, 0, 2 * math.pi)
        cr.restore()

        if self.fill_color:
            cr.set_source_rgba(*self.fill_color)
            cr.fill_preserve()

        cr.set_source_rgba(*self.color)
        cr.set_line_width(self.width * scale)
        cr.stroke()

class DrawingOverlay(Gtk.DrawingArea):
    def __init__(self):
        super().__init__()
        self.set_draw_func(self._on_draw)
        self.set_can_focus(True)
        self.picture_widget = None
        self.drawing_mode = DrawingMode.PEN
        self.pen_size = 3.0
        self.arrow_head_size = 25.0
        self.pen_color = (1.0, 1.0, 1.0, 0.8)
        self.fill_color = None  # None means no fill, otherwise (r, g, b, a) tuple
        self.is_drawing = False
        self.current_stroke = []
        self.start_point = None
        self.end_point = None
        self.actions = []
        self.redo_stack = []
        self._setup_gestures()
        self._setup_actions()

    def set_picture_reference(self, picture):
        self.picture_widget = picture
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

    def _get_scale_factor(self):
        _, _, dw, dh = self._get_image_bounds()
        if not self.picture_widget or not self.picture_widget.get_paintable():
            return 1.0
        img_w = self.picture_widget.get_paintable().get_intrinsic_width()
        return dw / img_w if img_w else 1.0

    def _widget_to_image_coords(self, x, y):
        ox, oy, dw, dh = self._get_image_bounds()
        return ((x - ox) / dw, (y - oy) / dh) if dw and dh else (x, y)

    def _image_to_widget_coords(self, rx, ry):
        ox, oy, dw, dh = self._get_image_bounds()
        return (ox + rx * dw, oy + ry * dh)

    def _is_point_in_image(self, x, y):
        ox, oy, dw, dh = self._get_image_bounds()
        return ox <= x <= ox + dw and oy <= y <= oy + dh

    def _setup_actions(self):
        for mode in DrawingMode:
            action = Gio.SimpleAction.new(f"drawing-mode-{mode.value}", None)
            action.connect("activate", lambda a, p, m=mode: self.set_drawing_mode(m))
            root = self.get_root()
            if hasattr(root, "add_action"):
                root.add_action(action)

    def set_drawing_mode(self, mode: DrawingMode):
        self.drawing_mode = mode
        self.is_drawing = False
        self.current_stroke.clear()
        self.start_point = None
        self.end_point = None
        self.queue_draw()

    def _setup_gestures(self):
        drag = Gtk.GestureDrag.new()
        drag.set_button(1)
        drag.connect("drag-begin", self._on_drag_begin)
        drag.connect("drag-update", self._on_drag_update)
        drag.connect("drag-end", self._on_drag_end)
        self.add_controller(drag)
        motion = Gtk.EventControllerMotion.new()
        motion.connect("motion", self._on_motion)
        self.add_controller(motion)

    def _on_drag_begin(self, gesture, x, y):
        if not self._is_point_in_image(x, y):
            return
        self.grab_focus()
        self.is_drawing = True
        rel = self._widget_to_image_coords(x, y)
        if self.drawing_mode == DrawingMode.PEN:
            self.current_stroke = [rel]
        else:
            self.start_point = rel
            self.end_point = rel

    def _on_drag_update(self, gesture, dx, dy):
        if not self.is_drawing:
            return
        start = gesture.get_start_point()
        cur_x, cur_y = start.x + dx, start.y + dy
        rel = self._widget_to_image_coords(cur_x, cur_y)
        if self.drawing_mode == DrawingMode.PEN:
            self.current_stroke.append(rel)
        else:
            self.end_point = rel
        self.queue_draw()

    def _on_drag_end(self, gesture, dx, dy):
        if not self.is_drawing:
            return
        self.is_drawing = False
        mode = self.drawing_mode
        if mode == DrawingMode.PEN and len(self.current_stroke) > 1:
            self.actions.append(StrokeAction(self.current_stroke.copy(), self.pen_color, self.pen_size))
            self.current_stroke.clear()
        elif self.start_point and self.end_point:
            if mode == DrawingMode.ARROW:
                self.actions.append(ArrowAction(self.start_point, self.end_point, self.pen_color, self.arrow_head_size))
            elif mode == DrawingMode.LINE:
                self.actions.append(LineAction(self.start_point, self.end_point, self.pen_color, self.pen_size))
            elif mode == DrawingMode.SQUARE:
                self.actions.append(RectAction(self.start_point, self.end_point, self.pen_color, self.pen_size, self.fill_color))
            elif mode == DrawingMode.CIRCLE:
                self.actions.append(CircleAction(self.start_point, self.end_point, self.pen_color, self.pen_size, self.fill_color))
            self.start_point = None
            self.end_point = None
        self.redo_stack.clear()
        self.queue_draw()

    def _on_motion(self, controller, x, y):
        name = "crosshair" if self.drawing_mode == DrawingMode.PEN else "cell"
        if not self._is_point_in_image(x, y):
            name = "default"
        self.set_cursor(Gdk.Cursor.new_from_name(name, None))

    def _on_draw(self, area, cr, width, height):
        scale = self._get_scale_factor()
        cr.set_line_cap(cairo.LineCap.ROUND)
        cr.set_line_join(cairo.LineJoin.ROUND)
        ox, oy, dw, dh = self._get_image_bounds()
        cr.rectangle(ox, oy, dw, dh)
        cr.clip()
        for action in self.actions:
            action.draw(cr, self._image_to_widget_coords, scale)
        if self.is_drawing:
            cr.set_source_rgba(*self.pen_color)
            if self.drawing_mode == DrawingMode.PEN and len(self.current_stroke) > 1:
                StrokeAction(self.current_stroke, self.pen_color, self.pen_size).draw(cr, self._image_to_widget_coords, scale)
            elif self.start_point and self.end_point:
                if self.drawing_mode == DrawingMode.ARROW:
                    ArrowAction(self.start_point, self.end_point, self.pen_color, self.arrow_head_size).draw(cr, self._image_to_widget_coords, scale)
                elif self.drawing_mode == DrawingMode.LINE:
                    LineAction(self.start_point, self.end_point, self.pen_color, self.pen_size).draw(cr, self._image_to_widget_coords, scale)
                elif self.drawing_mode == DrawingMode.SQUARE:
                    RectAction(self.start_point, self.end_point, self.pen_color, self.pen_size, self.fill_color).draw(cr, self._image_to_widget_coords, scale)
                elif self.drawing_mode == DrawingMode.CIRCLE:
                    CircleAction(self.start_point, self.end_point, self.pen_color, self.pen_size, self.fill_color).draw(cr, self._image_to_widget_coords, scale)

    def export_to_pixbuf(self):
        """Export only the drawn annotations to a pixbuf with transparent background"""
        if not self.picture_widget or not self.picture_widget.get_paintable():
            return None
        img_w = self.picture_widget.get_paintable().get_intrinsic_width()
        img_h = self.picture_widget.get_paintable().get_intrinsic_height()

        if img_w <= 0 or img_h <= 0:
            return None

        import cairo as cairo_lib

        surface = cairo_lib.ImageSurface(cairo_lib.Format.ARGB32, img_w, img_h)
        cr = cairo_lib.Context(surface)

        cr.set_operator(cairo_lib.Operator.CLEAR)
        cr.paint()
        cr.set_operator(cairo_lib.Operator.OVER)

        def image_coords_to_self(x, y):
            return (x * img_w, y * img_h)
        cr.set_line_cap(cairo_lib.LineCap.ROUND)
        cr.set_line_join(cairo_lib.LineJoin.ROUND)

        for action in self.actions:
            action.draw(cr, image_coords_to_self, 1.0)

        surface.flush()
        return Gdk.pixbuf_get_from_surface(surface, 0, 0, img_w, img_h)


    def clear_drawing(self): self.actions.clear(); self.redo_stack.clear(); self.queue_draw()
    def undo(self):
        if self.actions: self.redo_stack.append(self.actions.pop()); self.queue_draw()
    def redo(self):
        if self.redo_stack: self.actions.append(self.redo_stack.pop()); self.queue_draw()


    def set_pen_color(self, r, g, b, a=1): self.pen_color = (r, g, b, a)
    def set_fill_color(self, r, g, b, a=1): self.fill_color = (r, g, b, a)

    def set_pen_size(self, s): self.pen_size = max(1.0, s)
    def set_arrow_head_size(self, s): self.arrow_head_size = max(5.0, s)
    def set_drawing_visible(self, v): self.set_visible(v)
    def get_drawing_visible(self): return self.get_visible()



