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
from gi.repository import Gtk, Gdk, Graphene, Gsk
import math
import cairo

class CropOverlay(Gtk.Widget):
    __gtype_name__ = "GradiaCropOverlay"

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

        self.interaction_enabled = False

        self.gesture_click = Gtk.GestureClick()
        self.gesture_click.connect("pressed", self._on_button_pressed)
        self.gesture_click.connect("released", self._on_button_released)
        self.add_controller(self.gesture_click)

        self.motion_controller = Gtk.EventControllerMotion()
        self.motion_controller.connect("motion", self._on_motion)
        self.add_controller(self.motion_controller)

        self.set_cursor_from_name("crosshair")

    def set_interaction_enabled(self, enabled: bool) -> None:
        self.interaction_enabled = enabled

        if not enabled:
            self.dragging_handle = None
            self.dragging_edge = None
            self.dragging_area = False
            self.set_cursor_from_name("default")
        else:
            self.set_cursor_from_name("crosshair")

        self.queue_draw()

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

        overlay_rect = Graphene.Rect.alloc()
        overlay_rect.init(img_x, img_y, img_w, img_h)

        crop_rect = Graphene.Rect.alloc()
        crop_rect.init(crop_x, crop_y, crop_w, crop_h)

        overlay_color = Gdk.RGBA()
        overlay_color.red = 0.2
        overlay_color.green = 0.2
        overlay_color.blue = 0.2
        overlay_color.alpha = 0.6

        # Top overlay
        if crop_y > img_y:
            top_overlay = Graphene.Rect.alloc()
            top_overlay.init(img_x, img_y-1, img_w, crop_y - img_y +1)
            snapshot.append_color(overlay_color, top_overlay)

        # Bottom overlay
        if crop_y + crop_h < img_y + img_h:
            bottom_overlay = Graphene.Rect.alloc()
            bottom_overlay.init(img_x, crop_y + crop_h, img_w, (img_y + img_h) - (crop_y + crop_h))
            snapshot.append_color(overlay_color, bottom_overlay)

        # Left overlay
        if crop_x > img_x:
            left_overlay = Graphene.Rect.alloc()
            left_overlay.init(img_x, crop_y - 0.20, crop_x - img_x, crop_h + 0.4)
            snapshot.append_color(overlay_color, left_overlay)

       # Right overlay
        if crop_x + crop_w < img_x + img_w:
            right_overlay = Graphene.Rect.alloc()
            right_overlay.init(crop_x + crop_w, crop_y - 0.20, (img_x + img_w) - (crop_x + crop_w), crop_h + 0.4)
            snapshot.append_color(overlay_color, right_overlay)

        if self.interaction_enabled:
            border_color = Gdk.RGBA()
            border_color.red = 1.0
            border_color.green = 1.0
            border_color.blue = 1.0
            border_color.alpha = 0.8

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

            self._draw_corner_handles(snapshot, crop_x, crop_y, crop_w, crop_h)


    def _draw_corner_handles(self, snapshot: Gtk.Snapshot, x: float, y: float, w: float, h: float) -> None:
        handle_size = self.handle_size
        radius = handle_size / 2.0
        corners = [
            (x, y),
            (x + w, y),
            (x + w, y + h),
            (x, y + h),
        ]
        color = Gdk.RGBA(red=1, green=1, blue=1, alpha=1.0)
        for cx, cy in corners:
            rect = Graphene.Rect()
            rect.init(
                cx - radius,
                cy - radius,
                handle_size,
                handle_size
            )
            rounded_rect = Gsk.RoundedRect()
            rounded_rect.init_from_rect(rect, radius)
            snapshot.push_rounded_clip(rounded_rect)
            snapshot.append_color(color, rect)
            snapshot.pop()


    def _get_handle_at_point(self, x: float, y: float) -> str | None:
        if not self.interaction_enabled or not self.picture_widget or not self.picture_widget.get_paintable():
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
        if not self.interaction_enabled or not self.picture_widget or not self.picture_widget.get_paintable():
            return None

        img_x, img_y, img_w, img_h = self._get_image_bounds()

        crop_x = img_x + (self.crop_x * img_w)
        crop_y = img_y + (self.crop_y * img_h)
        crop_w = self.crop_width * img_w
        crop_h = self.crop_height * img_h

        half_handle = self.handle_size / 2

        edges = {
            "top": (crop_x + crop_w/2, crop_y),
            "right": (crop_x + crop_w, crop_y + crop_h/2),
            "bottom": (crop_x + crop_w/2, crop_y + crop_h),
            "left": (crop_x, crop_y + crop_h/2),
        }

        for edge_name, (edge_x, edge_y) in edges.items():
            if (abs(x - edge_x) <= half_handle and
                abs(y - edge_y) <= half_handle):
                return edge_name

        grab_distance = self.edge_grab_distance

        if (crop_x <= x <= crop_x + crop_w and
            abs(y - crop_y) <= grab_distance):
            return "top"

        if (crop_x <= x <= crop_x + crop_w and
            abs(y - (crop_y + crop_h)) <= grab_distance):
            return "bottom"

        if (crop_y <= y <= crop_y + crop_h and
            abs(x - crop_x) <= grab_distance):
            return "left"

        if (crop_y <= y <= crop_y + crop_h and
            abs(x - (crop_x + crop_w)) <= grab_distance):
            return "right"

        return None

    def _is_point_in_crop_area(self, x: float, y: float) -> bool:
        if not self.interaction_enabled or not self.picture_widget or not self.picture_widget.get_paintable():
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
        if not self.interaction_enabled:
            return

        handle = self._get_handle_at_point(x, y)
        if handle:
            self.dragging_handle = handle
            self.dragging_edge = None
            self.dragging_area = False
            self.drag_start_x = x
            self.drag_start_y = y
            self.drag_start_crop = (self.crop_x, self.crop_y, self.crop_width, self.crop_height)
            gesture.set_state(Gtk.EventSequenceState.CLAIMED)
            return

        edge = self._get_edge_at_point(x, y)
        if edge:
            self.dragging_edge = edge
            self.dragging_handle = None
            self.dragging_area = False
            self.drag_start_x = x
            self.drag_start_y = y
            self.drag_start_crop = (self.crop_x, self.crop_y, self.crop_width, self.crop_height)
            gesture.set_state(Gtk.EventSequenceState.CLAIMED)
            return

        if self._is_point_in_crop_area(x, y):
            self.dragging_area = True
            self.dragging_handle = None
            self.dragging_edge = None
            self.drag_start_x = x
            self.drag_start_y = y
            self.drag_start_crop = (self.crop_x, self.crop_y, self.crop_width, self.crop_height)
            gesture.set_state(Gtk.EventSequenceState.CLAIMED)

    def _on_button_released(self, gesture: Gtk.GestureClick, n_press: int, x: float, y: float) -> None:
        if not self.interaction_enabled:
            return

        self.dragging_handle = None
        self.dragging_edge = None
        self.dragging_area = False
        self.set_cursor_from_name("crosshair")

    def _on_motion(self, controller: Gtk.EventControllerMotion, x: float, y: float) -> None:
        if not self.interaction_enabled:
            return

        if ((self.dragging_handle or self.dragging_edge or self.dragging_area) and
            self.drag_start_crop):
            if self.dragging_handle:
                self._update_crop_from_handle_drag(x, y)
            elif self.dragging_edge:
                self._update_crop_from_edge_drag(x, y)
            elif self.dragging_area:
                self._update_crop_from_area_drag(x, y)
            self.queue_draw()
        else:
            handle = self._get_handle_at_point(x, y)
            if handle:
                if handle == "top-left":
                    self.set_cursor_from_name("nw-resize")
                elif handle == "top-right":
                    self.set_cursor_from_name("ne-resize")
                elif handle == "bottom-right":
                    self.set_cursor_from_name("se-resize")
                elif handle == "bottom-left":
                    self.set_cursor_from_name("sw-resize")
            else:
                edge = self._get_edge_at_point(x, y)
                if edge:
                    if edge in ["top", "bottom"]:
                        self.set_cursor_from_name("ns-resize")
                    elif edge in ["left", "right"]:
                        self.set_cursor_from_name("ew-resize")
                elif self._is_point_in_crop_area(x, y):
                    self.set_cursor_from_name("move")
                else:
                    self.set_cursor_from_name("crosshair")

    def _update_crop_from_handle_drag(self, x: float, y: float) -> None:
        if not self.drag_start_crop:
            return

        img_x, img_y, img_w, img_h = self._get_image_bounds()

        dx = (x - self.drag_start_x) / img_w
        dy = (y - self.drag_start_y) / img_h

        start_x, start_y, start_w, start_h = self.drag_start_crop

        if self.dragging_handle == "top-left":
            new_x = max(0, min(start_x + dx, start_x + start_w - 0.1))
            new_y = max(0, min(start_y + dy, start_y + start_h - 0.1))
            self.crop_x = new_x
            self.crop_y = new_y
            self.crop_width = start_w - (new_x - start_x)
            self.crop_height = start_h - (new_y - start_y)
        elif self.dragging_handle == "top-right":
            new_y = max(0, min(start_y + dy, start_y + start_h - 0.1))
            new_w = max(0.1, min(1 - start_x, start_w + dx))
            self.crop_y = new_y
            self.crop_width = new_w
            self.crop_height = start_h - (new_y - start_y)
        elif self.dragging_handle == "bottom-right":
            new_w = max(0.1, min(1 - start_x, start_w + dx))
            new_h = max(0.1, min(1 - start_y, start_h + dy))
            self.crop_width = new_w
            self.crop_height = new_h
        elif self.dragging_handle == "bottom-left":
            new_x = max(0, min(start_x + dx, start_x + start_w - 0.1))
            new_h = max(0.1, min(1 - start_y, start_h + dy))
            self.crop_x = new_x
            self.crop_width = start_w - (new_x - start_x)
            self.crop_height = new_h

        self.crop_x = max(0, min(1 - self.crop_width, self.crop_x))
        self.crop_y = max(0, min(1 - self.crop_height, self.crop_y))
        self.crop_width = max(0.1, min(1 - self.crop_x, self.crop_width))
        self.crop_height = max(0.1, min(1 - self.crop_y, self.crop_height))

    def _update_crop_from_edge_drag(self, x: float, y: float) -> None:
        if not self.drag_start_crop:
            return

        img_x, img_y, img_w, img_h = self._get_image_bounds()

        dx = (x - self.drag_start_x) / img_w
        dy = (y - self.drag_start_y) / img_h

        start_x, start_y, start_w, start_h = self.drag_start_crop

        if self.dragging_edge == "top":
            new_y = max(0, min(start_y + dy, start_y + start_h - 0.1))
            self.crop_y = new_y
            self.crop_height = start_h - (new_y - start_y)
        elif self.dragging_edge == "bottom":
            new_h = max(0.1, min(1 - start_y, start_h + dy))
            self.crop_height = new_h
        elif self.dragging_edge == "left":
            new_x = max(0, min(start_x + dx, start_x + start_w - 0.1))
            self.crop_x = new_x
            self.crop_width = start_w - (new_x - start_x)
        elif self.dragging_edge == "right":
            new_w = max(0.1, min(1 - start_x, start_w + dx))
            self.crop_width = new_w

        self.crop_x = max(0, min(1 - self.crop_width, self.crop_x))
        self.crop_y = max(0, min(1 - self.crop_height, self.crop_y))
        self.crop_width = max(0.1, min(1 - self.crop_x, self.crop_width))
        self.crop_height = max(0.1, min(1 - self.crop_y, self.crop_height))

    def _update_crop_from_area_drag(self, x: float, y: float) -> None:
        if not self.drag_start_crop:
            return

        img_x, img_y, img_w, img_h = self._get_image_bounds()

        dx = (x - self.drag_start_x) / img_w
        dy = (y - self.drag_start_y) / img_h

        start_x, start_y, start_w, start_h = self.drag_start_crop

        new_x = start_x + dx
        new_y = start_y + dy

        new_x = max(0, min(1 - start_w, new_x))
        new_y = max(0, min(1 - start_h, new_y))

        self.crop_x = new_x
        self.crop_y = new_y
        self.crop_width = start_w
        self.crop_height = start_h

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

    def get_crop_rectangle(self) -> tuple[float, float, float, float]:
        return self.crop_x, self.crop_y, self.crop_width, self.crop_height

    def set_crop_rectangle(self, x: float, y: float, width: float, height: float) -> None:
        self.crop_x = max(0, min(1 - width, x))
        self.crop_y = max(0, min(1 - height, y))
        self.crop_width = max(0.1, min(1 - self.crop_x, width))
        self.crop_height = max(0.1, min(1 - self.crop_y, height))
        self.queue_draw()
