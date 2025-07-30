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

from typing import Any
from gi.repository import Gtk, Gdk, Graphene, Gsk, GObject
import math
import cairo

class CropOverlay(Gtk.Widget):
    __gtype_name__ = "GradiaCropOverlay"

    interactive = GObject.Property(
        type=bool,
        default=False,
        nick="Interactive",
        blurb="Whether the crop overlay allows user interaction"
    )

    aspect_ratio = GObject.Property(
        type=float,
        default=0.0,
        nick="Aspect Ratio",
        blurb="Locked aspect ratio (width/height). 0 means unlocked, 1 means square"
    )

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self.picture_widget: Gtk.Picture | None = None

        self.crop_x = 0.0
        self.crop_y = 0.0
        self.crop_width = 1.0
        self.crop_height = 1.0

        self.handle_size = 18
        self.edge_grab_distance = 8
        self.dragging_handle = None
        self.dragging_edge = None
        self.dragging_area = False
        self.drag_start_x = 0
        self.drag_start_y = 0
        self.drag_start_crop = None

        self.gesture_click = Gtk.GestureClick()
        self.gesture_click.connect("pressed", self._on_button_pressed)
        self.gesture_click.connect("released", self._on_button_released)
        self.add_controller(self.gesture_click)

        self.motion_controller = Gtk.EventControllerMotion()
        self.motion_controller.connect("motion", self._on_motion)
        self.add_controller(self.motion_controller)

        self.set_cursor_from_name("crosshair")

        self.connect("notify::interactive", self._on_interactive_changed)
        self.connect("notify::aspect-ratio", self._on_aspect_ratio_changed)

    def _on_interactive_changed(self, obj, pspec):
        if not self.interactive:
            self.dragging_handle = None
            self.dragging_edge = None
            self.dragging_area = False
            self.set_cursor_from_name("default")
        else:
            self.set_cursor_from_name("crosshair")

        self.queue_draw()

    def _on_aspect_ratio_changed(self, obj, pspec):
        self._apply_aspect_ratio()
        self.queue_draw()

    def _apply_aspect_ratio(self) -> None:
        if self.aspect_ratio <= 0.0 or not self.picture_widget:
            return

        img_x, img_y, img_w, img_h = self._get_image_bounds()
        if img_w <= 0 or img_h <= 0:
            return

        target_rel_aspect = (self.aspect_ratio * img_h) / img_w
        current_rel_aspect = self.crop_width / self.crop_height

        if abs(target_rel_aspect - current_rel_aspect) < 1e-5:
            return

        center_x = self.crop_x + self.crop_width / 2
        center_y = self.crop_y + self.crop_height / 2

        if self.crop_width / target_rel_aspect > self.crop_height:
            new_width = self.crop_height * target_rel_aspect
            self.crop_x = center_x - new_width / 2
            self.crop_width = new_width
        else:
            new_height = self.crop_width / target_rel_aspect
            self.crop_y = center_y - new_height / 2
            self.crop_height = new_height

        self._clamp_crop_rectangle()

    def do_snapshot(self, snapshot: Gtk.Snapshot) -> None:
        if not self.picture_widget or not self.picture_widget.get_paintable():
            return

        width = self.get_width()
        height = self.get_height()
        if width <= 0 or height <= 0:
            return

        img_x, img_y, img_w, img_h = self._get_image_bounds()
        crop_x = img_x + (self.crop_x * img_w)
        crop_y = img_y + (self.crop_y * img_h)
        crop_w = self.crop_width * img_w
        crop_h = self.crop_height * img_h

        self._draw_background_overlay(snapshot, img_x, img_y, img_w, img_h, crop_x, crop_y, crop_w, crop_h)

        if self.interactive:
            self._draw_inner_border(snapshot, crop_x, crop_y, crop_w, crop_h)
            self._draw_corner_lines(snapshot, crop_x, crop_y, crop_w, crop_h)

    def _draw_background_overlay(self, snapshot: Gtk.Snapshot, img_x: float, img_y: float, img_w: float, img_h: float,
                                 crop_x: float, crop_y: float, crop_w: float, crop_h: float) -> None:
        overlay_color = Gdk.RGBA(red=0.2, green=0.2, blue=0.2, alpha=0.6)

        if crop_y > img_y:
            top_overlay = Graphene.Rect.alloc()
            top_overlay.init(img_x-1, img_y-1, img_w+1, crop_y - img_y +1)
            snapshot.append_color(overlay_color, top_overlay)

        if crop_y + crop_h < img_y + img_h:
            bottom_overlay = Graphene.Rect.alloc()
            bottom_overlay.init(img_x-1, crop_y + crop_h, img_w +1, (img_y + img_h) - (crop_y + crop_h))
            snapshot.append_color(overlay_color, bottom_overlay)

        if crop_x > img_x:
            left_overlay = Graphene.Rect.alloc()
            left_overlay.init(img_x-1, crop_y - 0.20, crop_x - img_x +1, crop_h + 0.4)
            snapshot.append_color(overlay_color, left_overlay)

        if crop_x + crop_w < img_x + img_w:
            right_overlay = Graphene.Rect.alloc()
            right_overlay.init(crop_x + crop_w, crop_y - 0.20, (img_x + img_w) - (crop_x + crop_w), crop_h + 0.4)
            snapshot.append_color(overlay_color, right_overlay)

    def _draw_inner_border(self, snapshot: Gtk.Snapshot, crop_x: float, crop_y: float, crop_w: float, crop_h: float) -> None:
        border_color = Gdk.RGBA(red=1.0, green=1.0, blue=1.0, alpha=0.8)
        border_width = 2.0

        top_border = Graphene.Rect.alloc()
        top_border.init(crop_x, crop_y - border_width/2, crop_w, border_width)
        snapshot.append_color(border_color, top_border)

        bottom_border = Graphene.Rect.alloc()
        bottom_border.init(crop_x, crop_y + crop_h - border_width/2, crop_w, border_width)
        snapshot.append_color(border_color, bottom_border)

        left_border = Graphene.Rect.alloc()
        left_border.init(crop_x - border_width/2, crop_y, border_width, crop_h)
        snapshot.append_color(border_color, left_border)

        right_border = Graphene.Rect.alloc()
        right_border.init(crop_x + crop_w - border_width/2, crop_y, border_width, crop_h)
        snapshot.append_color(border_color, right_border)

    def _draw_corner_lines(self, snapshot: Gtk.Snapshot, crop_x: float, crop_y: float, crop_w: float, crop_h: float) -> None:
        corner_color = Gdk.RGBA(red=1.0, green=1.0, blue=1.0, alpha=1.0)
        corner_line_width = 4.0
        corner_line_length = 25.0
        border_width = 0.0
        offset = border_width

        top_left_h = Graphene.Rect.alloc()
        top_left_h.init(crop_x - corner_line_width - offset, crop_y - offset - corner_line_width, corner_line_length + corner_line_width + offset, corner_line_width)
        snapshot.append_color(corner_color, top_left_h)

        top_left_v = Graphene.Rect.alloc()
        top_left_v.init(crop_x - offset - corner_line_width, crop_y - corner_line_width - offset, corner_line_width, corner_line_length + corner_line_width + offset)
        snapshot.append_color(corner_color, top_left_v)

        top_right_h = Graphene.Rect.alloc()
        top_right_h.init(crop_x + crop_w - corner_line_length, crop_y - offset - corner_line_width, corner_line_length + corner_line_width + offset, corner_line_width)
        snapshot.append_color(corner_color, top_right_h)

        top_right_v = Graphene.Rect.alloc()
        top_right_v.init(crop_x + crop_w + offset, crop_y - corner_line_width - offset, corner_line_width, corner_line_length + corner_line_width + offset)
        snapshot.append_color(corner_color, top_right_v)

        bottom_left_h = Graphene.Rect.alloc()
        bottom_left_h.init(crop_x - corner_line_width - offset, crop_y + crop_h + offset, corner_line_length + corner_line_width + offset, corner_line_width)
        snapshot.append_color(corner_color, bottom_left_h)

        bottom_left_v = Graphene.Rect.alloc()
        bottom_left_v.init(crop_x - offset - corner_line_width, crop_y + crop_h - corner_line_length, corner_line_width, corner_line_length + corner_line_width + offset)
        snapshot.append_color(corner_color, bottom_left_v)

        bottom_right_h = Graphene.Rect.alloc()
        bottom_right_h.init(crop_x + crop_w - corner_line_length, crop_y + crop_h + offset, corner_line_length + corner_line_width + offset, corner_line_width)
        snapshot.append_color(corner_color, bottom_right_h)

        bottom_right_v = Graphene.Rect.alloc()
        bottom_right_v.init(crop_x + crop_w + offset, crop_y + crop_h - corner_line_length, corner_line_width, corner_line_length + corner_line_width + offset)
        snapshot.append_color(corner_color, bottom_right_v)

    def _get_handle_at_point(self, x: float, y: float) -> str | None:
        if not self.interactive or not self.picture_widget or not self.picture_widget.get_paintable():
            return None

        img_x, img_y, img_w, img_h = self._get_image_bounds()

        crop_x = img_x + (self.crop_x * img_w)
        crop_y = img_y + (self.crop_y * img_h)
        crop_w = self.crop_width * img_w
        crop_h = self.crop_height * img_h

        half_handle = self.handle_size / 2

        corners = {
            "top-left": (crop_x, crop_y),
            "top-right": (crop_x + crop_w, crop_y),
            "bottom-right": (crop_x + crop_w, crop_y + crop_h),
            "bottom-left": (crop_x, crop_y + crop_h),
        }

        for handle_name, (corner_x, corner_y) in corners.items():
            if (abs(x - corner_x) <= half_handle and
                abs(y - corner_y) <= half_handle):
                return handle_name

        return None

    def _get_edge_at_point(self, x: float, y: float) -> str | None:
        if not self.interactive or not self.picture_widget or not self.picture_widget.get_paintable():
            return None

        img_x, img_y, img_w, img_h = self._get_image_bounds()

        crop_x = img_x + (self.crop_x * img_w)
        crop_y = img_y + (self.crop_y * img_h)
        crop_w = self.crop_width * img_w
        crop_h = self.crop_height * img_h

        if self.aspect_ratio <= 0:
            edges = {
                "top": (crop_x + crop_w/2, crop_y),
                "right": (crop_x + crop_w, crop_y + crop_h/2),
                "bottom": (crop_x + crop_w/2, crop_y + crop_h),
                "left": (crop_x, crop_y + crop_h/2),
            }

            half_handle = self.handle_size / 2
            for edge_name, (edge_x, edge_y) in edges.items():
                if (abs(x - edge_x) <= half_handle and abs(y - edge_y) <= half_handle):
                    return edge_name

        grab_distance = self.edge_grab_distance

        if (crop_x <= x <= crop_x + crop_w and abs(y - crop_y) <= grab_distance):
            return "top"
        if (crop_x <= x <= crop_x + crop_w and abs(y - (crop_y + crop_h)) <= grab_distance):
            return "bottom"
        if (crop_y <= y <= crop_y + crop_h and abs(x - crop_x) <= grab_distance):
            return "left"
        if (crop_y <= y <= crop_y + crop_h and abs(x - (crop_x + crop_w)) <= grab_distance):
            return "right"

        return None

    def _is_point_in_crop_area(self, x: float, y: float) -> bool:
        if not self.interactive or not self.picture_widget or not self.picture_widget.get_paintable():
            return False

        img_x, img_y, img_w, img_h = self._get_image_bounds()

        crop_x = img_x + (self.crop_x * img_w)
        crop_y = img_y + (self.crop_y * img_h)
        crop_w = self.crop_width * img_w
        crop_h = self.crop_height * img_h

        if (crop_x <= x <= crop_x + crop_w and crop_y <= y <= crop_y + crop_h):
            return (self._get_handle_at_point(x, y) is None and
                    self._get_edge_at_point(x, y) is None)

        return False

    def _on_button_pressed(self, gesture: Gtk.GestureClick, n_press: int, x: float, y: float) -> None:
        if not self.interactive:
            return

        handle = self._get_handle_at_point(x, y)
        if handle:
            self.dragging_handle = handle
            self.drag_start_crop = (self.crop_x, self.crop_y, self.crop_width, self.crop_height)
            gesture.set_state(Gtk.EventSequenceState.CLAIMED)
        else:
            edge = self._get_edge_at_point(x, y)
            if edge:
                self.dragging_edge = edge
                self.drag_start_crop = (self.crop_x, self.crop_y, self.crop_width, self.crop_height)
                gesture.set_state(Gtk.EventSequenceState.CLAIMED)
            elif self._is_point_in_crop_area(x, y):
                self.dragging_area = True
                self.drag_start_crop = (self.crop_x, self.crop_y, self.crop_width, self.crop_height)
                gesture.set_state(Gtk.EventSequenceState.CLAIMED)

        if self.dragging_handle or self.dragging_edge or self.dragging_area:
            self.drag_start_x = x
            self.drag_start_y = y

    def _on_button_released(self, gesture: Gtk.GestureClick, n_press: int, x: float, y: float) -> None:
        if not self.interactive:
            return

        self.dragging_handle = None
        self.dragging_edge = None
        self.dragging_area = False
        self.set_cursor_from_name("crosshair")

    def _on_motion(self, controller: Gtk.EventControllerMotion, x: float, y: float) -> None:
        if not self.interactive:
            return

        if (self.dragging_handle or self.dragging_edge or self.dragging_area) and self.drag_start_crop:
            if self.dragging_handle:
                self._update_crop_from_handle_drag(x, y)
            elif self.dragging_edge:
                self._update_crop_from_edge_drag(x, y)
            elif self.dragging_area:
                self._update_crop_from_area_drag(x, y)
            self.queue_draw()
        else:
            self._update_cursor(x, y)

    def _update_cursor(self, x: float, y: float):
        handle = self._get_handle_at_point(x, y)
        if handle:
            if handle == "top-left":
                self.set_cursor_from_name("nw-resize")
            if handle == "top-right":
                self.set_cursor_from_name("ne-resize")
            if handle == "bottom-right":
                self.set_cursor_from_name("se-resize")
            if handle == "bottom-left":
                self.set_cursor_from_name("sw-resize")
            return

        edge = self._get_edge_at_point(x, y)
        if edge:
            if edge in ["top", "bottom"]:
                self.set_cursor_from_name("ns-resize")
            else:
                self.set_cursor_from_name("ew-resize")
        elif self._is_point_in_crop_area(x, y):
            self.set_cursor_from_name("move")
        else:
            self.set_cursor_from_name("crosshair")

    def _update_crop_from_handle_drag(self, x: float, y: float) -> None:
        if not self.drag_start_crop: return
        img_x, img_y, img_w, img_h = self._get_image_bounds()
        if img_w <= 0 or img_h <= 0: return

        dx = (x - self.drag_start_x) / img_w
        dy = (y - self.drag_start_y) / img_h
        start_x, start_y, start_w, start_h = self.drag_start_crop

        if self.aspect_ratio > 0.0:
            target_rel_aspect = (self.aspect_ratio * img_h) / img_w

            if self.dragging_handle == "top-left":
                anchor_x, anchor_y = start_x + start_w, start_y + start_h
                new_w = start_w - dx
                new_h = new_w / target_rel_aspect
                self.crop_x, self.crop_y = anchor_x - new_w, anchor_y - new_h
                self.crop_width, self.crop_height = new_w, new_h
            elif self.dragging_handle == "top-right":
                anchor_x, anchor_y = start_x, start_y + start_h
                new_w = start_w + dx
                new_h = new_w / target_rel_aspect
                self.crop_x, self.crop_y = anchor_x, anchor_y - new_h
                self.crop_width, self.crop_height = new_w, new_h
            elif self.dragging_handle == "bottom-left":
                anchor_x, anchor_y = start_x + start_w, start_y
                new_w = start_w - dx
                new_h = new_w / target_rel_aspect
                self.crop_x, self.crop_y = anchor_x - new_w, anchor_y
                self.crop_width, self.crop_height = new_w, new_h
            elif self.dragging_handle == "bottom-right":
                new_w = start_w + dx
                new_h = new_w / target_rel_aspect
                self.crop_width, self.crop_height = new_w, new_h
        else:
            if self.dragging_handle == "top-left": self.crop_x, self.crop_y, self.crop_width, self.crop_height = start_x + dx, start_y + dy, start_w - dx, start_h - dy
            elif self.dragging_handle == "top-right": self.crop_y, self.crop_width, self.crop_height = start_y + dy, start_w + dx, start_h - dy
            elif self.dragging_handle == "bottom-right": self.crop_width, self.crop_height = start_w + dx, start_h + dy
            elif self.dragging_handle == "bottom-left": self.crop_x, self.crop_width, self.crop_height = start_x + dx, start_w - dx, start_h + dy

        self._clamp_crop_rectangle()

    def _update_crop_from_edge_drag(self, x: float, y: float) -> None:
        if not self.drag_start_crop: return
        img_x, img_y, img_w, img_h = self._get_image_bounds()
        if img_w <= 0 or img_h <= 0: return

        dx = (x - self.drag_start_x) / img_w
        dy = (y - self.drag_start_y) / img_h
        start_x, start_y, start_w, start_h = self.drag_start_crop

        if self.aspect_ratio > 0.0:
            target_rel_aspect = (self.aspect_ratio * img_h) / img_w
            center_x, center_y = start_x + start_w / 2, start_y + start_h / 2

            if self.dragging_edge == "top":
                new_h = start_h - dy
                new_w = new_h * target_rel_aspect
                self.crop_x, self.crop_y = center_x - new_w / 2, start_y + dy
                self.crop_width, self.crop_height = new_w, new_h
            elif self.dragging_edge == "bottom":
                new_h = start_h + dy
                new_w = new_h * target_rel_aspect
                self.crop_x = center_x - new_w / 2
                self.crop_width, self.crop_height = new_w, new_h
            elif self.dragging_edge == "left":
                new_w = start_w - dx
                new_h = new_w / target_rel_aspect
                self.crop_x, self.crop_y = start_x + dx, center_y - new_h / 2
                self.crop_width, self.crop_height = new_w, new_h
            elif self.dragging_edge == "right":
                new_w = start_w + dx
                new_h = new_w / target_rel_aspect
                self.crop_y = center_y - new_h / 2
                self.crop_width, self.crop_height = new_w, new_h
        else:
            if self.dragging_edge == "top": self.crop_y, self.crop_height = start_y + dy, start_h - dy
            elif self.dragging_edge == "bottom": self.crop_height = start_h + dy
            elif self.dragging_edge == "left": self.crop_x, self.crop_width = start_x + dx, start_w - dx
            elif self.dragging_edge == "right": self.crop_width = start_w + dx

        self._clamp_crop_rectangle()

    def _update_crop_from_area_drag(self, x: float, y: float) -> None:
        if not self.drag_start_crop: return
        img_x, img_y, img_w, img_h = self._get_image_bounds()
        if img_w <= 0 or img_h <= 0: return

        dx = (x - self.drag_start_x) / img_w
        dy = (y - self.drag_start_y) / img_h
        start_x, start_y, _, _ = self.drag_start_crop

        self.crop_x = start_x + dx
        self.crop_y = start_y + dy

        self._clamp_crop_rectangle()

    def _clamp_crop_rectangle(self):
        min_dim = 0.2
        self.crop_width = max(min_dim, self.crop_width)
        self.crop_height = max(min_dim, self.crop_height)

        if self.crop_width > 1.0: self.crop_width = 1.0
        if self.crop_height > 1.0: self.crop_height = 1.0

        self.crop_x = max(0, min(1 - self.crop_width, self.crop_x))
        self.crop_y = max(0, min(1 - self.crop_height, self.crop_y))

    def set_picture_reference(self, picture: Gtk.Picture) -> None:
        self.picture_widget = picture
        if picture:
            picture.connect("notify::paintable", lambda *args: self.queue_draw())
            picture.connect("notify::paintable", lambda *args: self._apply_aspect_ratio())

    def _get_image_bounds(self) -> tuple[float, float, float, float]:
        if not self.picture_widget or not self.picture_widget.get_paintable():
            return 0, 0, self.get_width(), self.get_height()

        widget_width = self.picture_widget.get_width()
        widget_height = self.picture_widget.get_height()
        paintable = self.picture_widget.get_paintable()
        image_width = paintable.get_intrinsic_width()
        image_height = paintable.get_intrinsic_height()

        if image_width <= 0 or image_height <= 0:
            return 0, 0, widget_width, widget_height

        scale = min(widget_width / image_width, widget_height / image_height)
        display_width = image_width * scale
        display_height = image_height * scale

        offset_x = (widget_width - display_width) / 2
        offset_y = (widget_height - display_height) / 2

        return offset_x, offset_y, display_width, display_height

    def get_crop_rectangle(self) -> tuple[float, float, float, float]:
        return self.crop_x, self.crop_y, self.crop_width, self.crop_height

    def set_crop_rectangle(self, x: float, y: float, width: float, height: float) -> None:
        self.crop_x = x
        self.crop_y = y
        self.crop_width = width
        self.crop_height = height
        self._clamp_crop_rectangle()
        self.queue_draw()

