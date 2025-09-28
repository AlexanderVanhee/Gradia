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
        super().__init__(css_name='angle-selector')
        self._outer_radius = 40
        self._inner_radius = 37
        self._handle_size = 20
        self._handle_radius = 10
        self._dragging = False
        self._snap_threshold = 15
        self._exit_threshold = 25

        self.set_size_request(100, 100)
        self.set_can_focus(True)
        self._setup_gestures()
        self.connect("notify::angle", lambda *a: self.queue_draw())

    def do_get_css_name(self):
        return "angle-selector"

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
        return angle_degrees

    def _snap_to_90_degrees(self, angle):
        snap_angles = [0, 90, 180, 270]
        for snap_angle in snap_angles:
            if self.angle == snap_angle:
                distance = abs(angle - snap_angle)
                if distance > 180:
                    distance = 360 - distance
                if distance <= self._exit_threshold:
                    return snap_angle
                else:
                    return angle
        return angle

    def _is_point_in_handle(self, x, y):
        hx, hy = self._get_handle_position()
        dx = x - hx
        dy = y - hy
        distance = math.sqrt(dx * dx + dy * dy)
        return distance <= self._handle_radius + 5

    def _on_click(self, gesture, n_press, x, y):
        if self._is_point_in_handle(x, y):
            return
        new_angle = self._point_to_angle(x, y)
        snapped_angle = self._snap_to_90_degrees(new_angle)
        self.set_angle_internal(snapped_angle)
        self.emit('angle-changed', self.angle)

    def _on_drag_begin(self, gesture, start_x, start_y):
        if self._is_point_in_handle(start_x, start_y):
            self._dragging = True
            self.grab_focus()
        else:
            new_angle = self._point_to_angle(start_x, start_y)
            snapped_angle = self._snap_to_90_degrees(new_angle)
            self.set_angle_internal(snapped_angle)
            self._dragging = True
            self.grab_focus()

    def _on_drag_update(self, gesture, offset_x, offset_y):
        if not self._dragging:
            return
        point = gesture.get_start_point()
        current_x = point.x + offset_x
        current_y = point.y + offset_y
        new_angle = self._point_to_angle(current_x, current_y)
        snapped_angle = self._snap_to_90_degrees(new_angle)
        self.set_angle_internal(snapped_angle)

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
        width, height = allocation.width, allocation.height
        cx, cy = width / 2, height / 2
        context = self.get_style_context()
        bg_color = context.get_color()
        fg_color = context.get_color()
        luminance = 0.299 * bg_color.red + 0.587 * bg_color.green + 0.114 * bg_color.blue
        is_dark = luminance < 0.5

        if not is_dark:
            background_color = Gdk.RGBA(0.32,0.32,0.33,1)
            foreground_color = Gdk.RGBA(0.82,0.82,0.82,1)
            shadow_color = Gdk.RGBA(0,0,0.023,1)
        else:
            background_color = Gdk.RGBA(0.88,0.88,0.88,1)
            foreground_color = Gdk.RGBA(1,1,1,1)
            shadow_color = Gdk.RGBA(0,0,0.023,1)

        self._draw_circle_border(snapshot, cx, cy, self._outer_radius, background_color)
        self._draw_90_degree_lines(snapshot, cx, cy, fg_color)
        self._draw_handle(snapshot, cx, cy, foreground_color, shadow_color)

    def _draw_90_degree_lines(self, snapshot, cx, cy, color):
        line_length = 4
        outer_start = self._outer_radius - 8
        inner_end = outer_start - line_length
        thickness = 1
        angles = [0, 90, 180, 270]
        for angle in angles:
            rad = math.radians(angle - 90)
            start_x = cx + outer_start * math.cos(rad)
            start_y = cy + outer_start * math.sin(rad)
            end_x = cx + inner_end * math.cos(rad)
            end_y = cy + inner_end * math.sin(rad)
            if abs(start_x - end_x) > abs(start_y - end_y):
                line_rect = Graphene.Rect()
                line_rect.init(min(start_x, end_x), cy - thickness/2, abs(end_x - start_x), thickness)
                snapshot.append_color(color, line_rect)
            else:
                line_rect = Graphene.Rect()
                line_rect.init(cx - thickness/2, min(start_y, end_y), thickness, abs(end_y - start_y))
                snapshot.append_color(color, line_rect)

    def _draw_handle(self, snapshot, cx, cy, color ,shadow_color):
        hx, hy = self._get_handle_position()
        angle_to_center = math.atan2(cy - hy, cx - hx)
        rotation_degrees = math.degrees(angle_to_center) - 45
        handle_color = color
        shadow_color1 = Gdk.RGBA(red=shadow_color.red, green=shadow_color.green, blue=shadow_color.blue, alpha=0.1)
        shadow_color2 = Gdk.RGBA(red=shadow_color.red, green=shadow_color.green, blue=shadow_color.blue, alpha=0.2)
        snapshot.save()
        snapshot.translate(Graphene.Point().init(hx, hy))
        snapshot.rotate(rotation_degrees)
        snapshot.translate(Graphene.Point().init(-self._handle_radius, -self._handle_radius))
        handle_rect = Graphene.Rect()
        handle_rect.init(0, 0, self._handle_size, self._handle_size)
        rounded_rect = Gsk.RoundedRect()
        rounded_rect.init(
            handle_rect,
            Graphene.Size().init(self._handle_radius, self._handle_radius),
            Graphene.Size().init(self._handle_radius, self._handle_radius),
            Graphene.Size().init(0, 0),
            Graphene.Size().init(self._handle_radius, self._handle_radius)
        )
        shadow_node1 = Gsk.OutsetShadowNode.new(
            rounded_rect,
            shadow_color1,
            0, 0, 1, 0
        )
        shadow_node2 = Gsk.OutsetShadowNode.new(
            rounded_rect,
            shadow_color2,
            0, 0, 0, 4
        )
        snapshot.append_node(shadow_node1)
        snapshot.append_node(shadow_node2)
        snapshot.push_rounded_clip(rounded_rect)
        snapshot.append_color(handle_color, handle_rect)
        snapshot.pop()
        snapshot.restore()

    def _draw_circle_border(self, snapshot, cx, cy, radius, color):
        border_width = 4
        rect = Graphene.Rect()
        rect.init(cx - radius, cy - radius, radius * 2, radius * 2)
        rounded_rect = Gsk.RoundedRect()
        rounded_rect.init_from_rect(rect, radius)
        widths = [border_width] * 4
        colors = [color] * 4
        snapshot.append_node(
            Gsk.BorderNode.new(rounded_rect, widths, colors)
        )

AngleSelector.set_css_name("angle-selector")

