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

from gi.repository import Gtk, Gdk, Graphene, Gsk, GObject, Adw
import math

class AngleSelector(Gtk.Widget):
    __gtype_name__ = 'GradiaAngleSelector'

    angle = GObject.Property(
        type=int,
        default=0,
        minimum=0,
        maximum=360,
        nick='Angle (degrees)',
        blurb='Angle in degrees between 0 and 360'
    )

    __gsignals__ = {
        'angle-changed': (GObject.SignalFlags.RUN_FIRST, None, (int,))
    }

    def __init__(self):
        super().__init__()
        self._outer_radius = 40
        self._inner_radius = 22.5
        self._handle_radius = 9
        self._dragging = False
        self.set_size_request(100, 100)
        self.set_can_focus(True)
        self._setup_gestures()
        self.connect("notify::angle", lambda *a: self.queue_draw())

    def _setup_gestures(self):
        drag_controller = Gtk.GestureDrag.new()
        drag_controller.connect('drag-begin', self._on_drag_begin)
        drag_controller.connect('drag-update', self._on_drag_update)
        drag_controller.connect('drag-end', self._on_drag_end)
        self.add_controller(drag_controller)

        click_controller = Gtk.GestureClick.new()
        click_controller.connect('pressed', self._on_click)
        self.add_controller(click_controller)

    def _get_center(self):
        allocation = self.get_allocation()
        return allocation.width / 2, allocation.height / 2

    def _get_handle_position(self):
        cx, cy = self._get_center()
        adjusted_angle = self.angle - 90
        rad = math.radians(adjusted_angle)
        x = cx + self._inner_radius * math.cos(rad)
        y = cy + self._inner_radius * math.sin(rad)
        return x, y

    def _point_to_angle(self, x, y):
        cx, cy = self._get_center()
        dx = x - cx
        dy = y - cy
        angle_rad = math.atan2(dy, dx)
        angle_degrees = math.degrees(angle_rad)
        angle_degrees = (angle_degrees + 90) % 360

        if angle_degrees < 0:
            angle_degrees += 360

        return math.radians(angle_degrees)

    def _is_point_in_handle(self, x, y):
        hx, hy = self._get_handle_position()
        dx = x - hx
        dy = y - hy
        distance = math.sqrt(dx * dx + dy * dy)
        return distance <= self._handle_radius + 5

    def _on_click(self, gesture, n_press, x, y):
        if self._is_point_in_handle(x, y):
            return
        new_angle_rad = self._point_to_angle(x, y)
        self.set_angle_internal(math.degrees(new_angle_rad))
        self.emit('angle-changed', self.angle)

    def _on_drag_begin(self, gesture, start_x, start_y):
        if self._is_point_in_handle(start_x, start_y):
            self._dragging = True
            self.grab_focus()
        else:
            new_angle_rad = self._point_to_angle(start_x, start_y)
            self.set_angle_internal(math.degrees(new_angle_rad))
            self._dragging = True
            self.grab_focus()

    def _on_drag_update(self, gesture, offset_x, offset_y):
        if not self._dragging:
            return
        point = gesture.get_start_point()
        current_x = point.x + offset_x
        current_y = point.y + offset_y
        new_angle_rad = self._point_to_angle(current_x, current_y)
        self.set_angle_internal(math.degrees(new_angle_rad))

    def _on_drag_end(self, gesture, offset_x, offset_y):
        self._dragging = False
        self.emit('angle-changed', self.angle)

    def set_angle_internal(self, degrees):
        degrees = degrees % 360
        if abs(self.angle - degrees) > 0.5:
            self.angle = int(round(degrees))
            self.queue_draw()

    def get_angle_radians(self):
        return math.radians(self.angle)

    def set_angle_radians(self, radians_val):
        degrees = math.degrees(radians_val) % 360
        self.set_angle_internal(degrees)

    def do_snapshot(self, snapshot):
        allocation = self.get_allocation()
        width = allocation.width
        height = allocation.height
        cx, cy = width / 2, height / 2
        context = self.get_style_context()
        text_color = context.lookup_color("window_fg_color")[1]
        self._draw_circle_border(snapshot, cx, cy, self._outer_radius, text_color, 4.0)
        hx, hy = self._get_handle_position()
        self._draw_filled_circle(snapshot, hx, hy, self._handle_radius, text_color)

    def _draw_filled_circle(self, snapshot, cx, cy, radius, color):
        rect = Graphene.Rect()
        rect.init(cx - radius, cy - radius, radius * 2, radius * 2)
        rounded_rect = Gsk.RoundedRect()
        rounded_rect.init_from_rect(rect, radius)
        snapshot.push_rounded_clip(rounded_rect)
        snapshot.append_color(color, rect)
        snapshot.pop()

    def _draw_circle_border(self, snapshot, cx, cy, radius, color, line_width):
        rect = Graphene.Rect()
        rect.init(0, 0, self.get_allocated_width(), self.get_allocated_height())
        cairo_ctx = snapshot.append_cairo(rect)
        cairo_ctx.set_source_rgba(color.red, color.green, color.blue, color.alpha)
        cairo_ctx.set_line_width(line_width)
        cairo_ctx.arc(cx, cy, radius, 0, 2 * math.pi)
        cairo_ctx.stroke()
