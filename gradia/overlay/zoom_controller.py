# Copyright (C) 2025 tfuxu, Alexander Vanhee
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

from gi.repository import Gtk, Gdk, GObject, Graphene, Gsk
from gradia.backend.logger import Logger
import math

logger = Logger()

class ZoomController(Gtk.Widget):
    __gtype_name__ = "GradiaZoomController"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self._zoom_level = 1.0
        self._min_zoom = 0.25
        self._max_zoom = 3.0
        self._pan_x = 0.0
        self._pan_y = 0.0
        self._mouse_x = 0.0
        self._mouse_y = 0.0

        self._picture_overlay = None
        self._drawing_overlay = None
        self._crop_overlay = None
        self._transparency_background = None
        self._picture = None

        self._is_middle_dragging = False
        self._original_cursor = None
        self._debug_enabled = False

        self._setup_gestures()

        self.set_layout_manager(Gtk.BinLayout())
        self.set_focusable(True)
        self.set_can_focus(True)

    def _debug_print(self, message):
        if self._debug_enabled:
            logger.info(f"[ZoomController] {message}")

    def _setup_gestures(self):
        self._zoom_gesture = Gtk.GestureZoom.new()
        self._zoom_gesture.connect("scale-changed", self._on_zoom_changed)
        self.add_controller(self._zoom_gesture)

        self._drag_gesture = Gtk.GestureDrag.new()
        self._drag_gesture.set_button(Gdk.BUTTON_MIDDLE)
        self._drag_gesture.connect("drag-begin", self._on_drag_begin)
        self._drag_gesture.connect("drag-update", self._on_drag_update)
        self._drag_gesture.connect("drag-end", self._on_drag_end)
        self.add_controller(self._drag_gesture)

        self._scroll_controller = Gtk.EventControllerScroll.new(
            Gtk.EventControllerScrollFlags.VERTICAL |
            Gtk.EventControllerScrollFlags.HORIZONTAL
        )
        self._scroll_controller.connect("scroll", self._on_scroll)
        self.add_controller(self._scroll_controller)

        self._motion_controller = Gtk.EventControllerMotion.new()
        self._motion_controller.connect("motion", self._on_motion)
        self.add_controller(self._motion_controller)

        self._click_gesture = Gtk.GestureClick.new()
        self._click_gesture.connect("pressed", self._on_click_pressed)
        self.add_controller(self._click_gesture)

        self._resize_observer = Gtk.EventControllerFocus.new()
        self.add_controller(self._resize_observer)
        self.connect("notify::allocated-width", self._on_size_changed)
        self.connect("notify::allocated-height", self._on_size_changed)

    def _on_size_changed(self, *args):
        self._constrain_pan()
        self.queue_draw()

    def _on_click_pressed(self, gesture, n_press, x, y):
        self.grab_focus()

    def _on_motion(self, controller, x, y):
        self._mouse_x = x
        self._mouse_y = y

    def _on_zoom_changed(self, gesture, scale):
        center_x, center_y = gesture.get_bounding_box_center()
        self._debug_print(f"Gesture zoom at {center_x:.1f}, {center_y:.1f} with scale {scale:.3f}")
        self._zoom_at_point(scale, center_x, center_y)

    def _on_scroll(self, controller, dx, dy):
        modifiers = controller.get_current_event_state()

        if modifiers & Gdk.ModifierType.CONTROL_MASK:
            zoom_factor = 1.1 if dy < 0 else 0.9
            self._debug_print(f"Ctrl+scroll zoom at mouse {self._mouse_x:.1f}, {self._mouse_y:.1f}")
            self._zoom_at_point(zoom_factor, self._mouse_x, self._mouse_y)
            return Gdk.EVENT_STOP
        else:
            if abs(self._zoom_level - 1.0) < 0.01:
                return Gdk.EVENT_PROPAGATE

            scroll_speed = 30.0

            if modifiers & Gdk.ModifierType.SHIFT_MASK:
                self._pan_x -= dy * scroll_speed / self._zoom_level
                self._pan_y -= dx * scroll_speed / self._zoom_level
                self._debug_print(f"Shift+scroll pan by dx={dx:.2f}, dy={dy:.2f} (reversed)")
            else:
                self._pan_y -= dy * scroll_speed / self._zoom_level
                self._pan_x -= dx * scroll_speed / self._zoom_level
                self._debug_print(f"Normal scroll pan by dx={dx:.2f}, dy={dy:.2f}")

            self._constrain_pan()
            self.queue_draw()
            return Gdk.EVENT_STOP

    def _on_drag_begin(self, gesture, start_x, start_y):
        self._drag_start_x = self._pan_x
        self._drag_start_y = self._pan_y
        self._is_middle_dragging = True

        if self._original_cursor is None:
            self._original_cursor = self.get_cursor()

        grab_cursor = Gdk.Cursor.new_from_name("grabbing")
        self.set_cursor(grab_cursor)

    def _on_drag_update(self, gesture, offset_x, offset_y):
        if not self._is_middle_dragging:
            return

        scale_factor = 1.0 / self._zoom_level

        self._pan_x = self._drag_start_x + offset_x * scale_factor
        self._pan_y = self._drag_start_y + offset_y * scale_factor
        self._constrain_pan()
        self.queue_draw()

    def _on_drag_end(self, gesture, offset_x, offset_y):
        self._is_middle_dragging = False
        self.set_cursor(self._original_cursor)

    def _get_content_bounds(self):
        widget_width = self.get_width()
        widget_height = self.get_height()

        if not self._picture:
            return 0, 0, widget_width, widget_height

        paintable = self._picture.get_paintable()
        if not paintable:
            return 0, 0, widget_width, widget_height

        image_width = paintable.get_intrinsic_width()
        image_height = paintable.get_intrinsic_height()

        if image_width <= 0 or image_height <= 0:
            return 0, 0, widget_width, widget_height

        scale = min(widget_width / image_width, widget_height / image_height)
        content_width = image_width * scale
        content_height = image_height * scale

        content_x = (widget_width - content_width) / 2
        content_y = (widget_height - content_height) / 2

        return content_x, content_y, content_width, content_height

    def _get_transformed_bounds(self):
        content_x, content_y, content_width, content_height = self._get_content_bounds()

        center_x = self.get_width() / 2
        center_y = self.get_height() / 2

        rel_x = content_x - center_x
        rel_y = content_y - center_y

        transformed_x = center_x + (rel_x * self._zoom_level) + self._pan_x
        transformed_y = center_y + (rel_y * self._zoom_level) + self._pan_y
        transformed_width = content_width * self._zoom_level
        transformed_height = content_height * self._zoom_level

        return transformed_x, transformed_y, transformed_width, transformed_height

    def _get_image_center_point(self):
        transformed_x, transformed_y, transformed_width, transformed_height = self._get_transformed_bounds()
        center_x = transformed_x + transformed_width / 2
        center_y = transformed_y + transformed_height / 2
        return center_x, center_y

    def _zoom_at_point(self, zoom_factor, center_x, center_y):
        old_zoom = self._zoom_level
        new_zoom = old_zoom * zoom_factor
        new_zoom = max(self._min_zoom, min(self._max_zoom, new_zoom))

        if new_zoom != old_zoom:
            widget_width = self.get_width()
            widget_height = self.get_height()

            self._debug_print(f"Zoom from {old_zoom:.3f} to {new_zoom:.3f} at point {center_x:.1f}, {center_y:.1f}")

            widget_center_x = widget_width / 2
            widget_center_y = widget_height / 2

            old_content_x = center_x - widget_center_x - self._pan_x
            old_content_y = center_y - widget_center_y - self._pan_y

            zoom_ratio = new_zoom / old_zoom
            new_content_x = old_content_x * zoom_ratio
            new_content_y = old_content_y * zoom_ratio

            self._zoom_level = new_zoom

            self._pan_x = center_x - widget_center_x - new_content_x
            self._pan_y = center_y - widget_center_y - new_content_y

            self._constrain_pan()
            self.queue_draw()
            self.notify("zoom-level")

    def _constrain_pan(self):
        widget_width = self.get_width()
        widget_height = self.get_height()

        if widget_width <= 0 or widget_height <= 0:
            return

        old_pan_x, old_pan_y = self._pan_x, self._pan_y

        if self._picture:
            paintable = self._picture.get_paintable()
            if paintable:
                image_width = paintable.get_intrinsic_width()
                image_height = paintable.get_intrinsic_height()

                if image_width > 0 and image_height > 0:
                    content_x, content_y, content_width, content_height = self._get_content_bounds()

                    transformed_width = content_width * self._zoom_level
                    transformed_height = content_height * self._zoom_level

                    overpan_x = widget_width * 0.1
                    overpan_y = widget_height * 0.1

                    if transformed_width > widget_width:
                        max_offset = (transformed_width - widget_width) / 2
                        max_pan_x = max_offset + overpan_x
                        min_pan_x = -max_offset - overpan_x
                    else:
                        max_pan_x = overpan_x
                        min_pan_x = -overpan_x

                    if transformed_height > widget_height:
                        max_offset = (transformed_height - widget_height) / 2
                        max_pan_y = max_offset + overpan_y
                        min_pan_y = -max_offset - overpan_y
                    else:
                        max_pan_y = overpan_y
                        min_pan_y = -overpan_y

                    self._pan_x = max(min_pan_x, min(max_pan_x, self._pan_x))
                    self._pan_y = max(min_pan_y, min(max_pan_y, self._pan_y))

                    if self._debug_enabled and (old_pan_x != self._pan_x or old_pan_y != self._pan_y):
                        self._debug_print(f"Pan constrained from {old_pan_x:.1f}, {old_pan_y:.1f} to {self._pan_x:.1f}, {self._pan_y:.1f}")
                        self._debug_print(f"Pan limits: x[{min_pan_x:.1f}, {max_pan_x:.1f}], y[{min_pan_y:.1f}, {max_pan_y:.1f}]")
                    return

        overpan_x = widget_width / 2
        overpan_y = widget_height / 2

        range_x = max(0, (widget_width * self._zoom_level - widget_width) / 2)
        range_y = max(0, (widget_height * self._zoom_level - widget_height) / 2)

        max_pan_x = range_x + overpan_x
        max_pan_y = range_y + overpan_y

        self._pan_x = max(-max_pan_x, min(max_pan_x, self._pan_x))
        self._pan_y = max(-max_pan_y, min(max_pan_y, self._pan_y))

    def _draw_debug_image_bounds(self, snapshot):
        if not self._debug_enabled:
            return
        transformed_x, transformed_y, transformed_width, transformed_height = self._get_transformed_bounds()
        rect = Graphene.Rect.alloc()
        rect.init(transformed_x, transformed_y, transformed_width, transformed_height)
        color = Gdk.RGBA(red=1.0, green=0.0, blue=0.0, alpha=0.5)
        snapshot.append_color(color, rect)

    def do_snapshot(self, snapshot):
        width = self.get_width()
        height = self.get_height()

        if width <= 0 or height <= 0:
            return

        transform = Gsk.Transform()
        transform = transform.translate(Graphene.Point.alloc().init(
            width / 2 + self._pan_x,
            height / 2 + self._pan_y
        ))
        transform = transform.scale(self._zoom_level, self._zoom_level)
        transform = transform.translate(Graphene.Point.alloc().init(
            -width / 2,
            -height / 2
        ))

        snapshot.save()
        snapshot.transform(transform)

        child = self.get_first_child()
        while child:
            self.snapshot_child(child, snapshot)
            child = child.get_next_sibling()

        snapshot.restore()

        self._draw_debug_image_bounds(snapshot)

    def set_child_widgets(self, picture_overlay, drawing_overlay, crop_overlay,
                          transparency_background, picture):
        child = self.get_first_child()
        while child:
            next_child = child.get_next_sibling()
            child.unparent()
            child = next_child

        self._picture_overlay = picture_overlay
        self._drawing_overlay = drawing_overlay
        self._crop_overlay = crop_overlay
        self._transparency_background = transparency_background
        self._picture = picture

        if picture_overlay:
            picture_overlay.set_parent(self)

    def zoom_in(self, factor=1.2):
        center_x, center_y = self._get_image_center_point()
        self._debug_print(f"Zoom in button pressed, zooming at image center {center_x:.1f}, {center_y:.1f}")
        self._zoom_at_point(factor, center_x, center_y)

    def zoom_out(self, factor=0.8):
        center_x, center_y = self._get_image_center_point()
        self._debug_print(f"Zoom out button pressed, zooming at image center {center_x:.1f}, {center_y:.1f}")
        self._zoom_at_point(factor, center_x, center_y)

    def reset_zoom(self):
        self._debug_print("Reset zoom called")
        self._zoom_level = 1.0
        self._pan_x = 0.0
        self._pan_y = 0.0
        self.queue_draw()
        self.notify("zoom-level")

    def fit_to_window(self):
        if not self._picture:
            return

        paintable = self._picture.get_paintable()
        if not paintable:
            return

        widget_width = self.get_width()
        widget_height = self.get_height()
        image_width = paintable.get_intrinsic_width()
        image_height = paintable.get_intrinsic_height()

        if widget_width <= 0 or widget_height <= 0 or image_width <= 0 or image_height <= 0:
            return

        scale_x = widget_width / image_width
        scale_y = widget_height / image_height
        scale = min(scale_x, scale_y)

        self._debug_print(f"Fit to window: scale {scale:.3f}")
        self._zoom_level = scale
        self._pan_x = 0.0
        self._pan_y = 0.0
        self.queue_draw()
        self.notify("zoom-level")

    @GObject.Property(type=float, default=1.0)
    def zoom_level(self):
        return self._zoom_level

    @zoom_level.setter
    def zoom_level(self, value):
        new_zoom = max(self._min_zoom, min(self._max_zoom, value))
        if new_zoom != self._zoom_level:
            self._zoom_level = new_zoom
            self._constrain_pan()
            self.queue_draw()
            self.notify("zoom-level")

    @GObject.Property(type=float, default=0.5)
    def min_zoom(self):
        return self._min_zoom

    @min_zoom.setter
    def min_zoom(self, value):
        self._min_zoom = value

    @GObject.Property(type=float, default=2.0)
    def max_zoom(self):
        return self._max_zoom

    @max_zoom.setter
    def max_zoom(self, value):
        self._max_zoom = value
