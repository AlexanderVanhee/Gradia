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

import cairo
from gi.repository import Adw, Gdk, Gio, Gtk

from gradia.overlay.drawing_actions import *
from gradia.overlay.text_entry_popover import TextEntryPopover

SELECTION_BOX_PADDING = 0
DEFAULT_ARROW_HEAD_SIZE = 25.0
DEFAULT_FONT_SIZE = 22.0
DEFAULT_HIGHLIGHTER_SIZE = 12.0
DEFAULT_PIXELATION_LEVEL = 8

class DrawingOverlay(Gtk.DrawingArea):
    __gtype_name__ = "GradiaDrawingOverlay"

    def __init__(self, **kwargs):
        super().__init__(can_focus=True, **kwargs)

        self.set_draw_func(self._on_draw)

        self.picture_widget = None
        self.drawing_mode = DrawingMode.PEN
        self.pen_size = None # Initialized via drawing_tools_group
        self.pen_color = None # Initialized via drawing_tools_group
        self.arrow_head_size = DEFAULT_ARROW_HEAD_SIZE
        self.font_size = DEFAULT_FONT_SIZE
        self.font_family = None # Initialized via drawing_tools_group
        self.highlighter_size = DEFAULT_HIGHLIGHTER_SIZE
        self.pixelation_level = DEFAULT_PIXELATION_LEVEL
        self.fill_color = None
        self.is_drawing = False
        self.current_stroke = []
        self.start_point = None
        self.end_point = None
        self.actions: list[DrawingAction] = []
        self.redo_stack = []
        self._next_number = 1
        self.number_radius = None # Initialized via drawing_tools_group

        self._selected_action: DrawingAction | None = None
        self.selection_start_pos = None
        self.is_moving_selection = False
        self.move_start_point = None

        self.text_entry_popup = None
        self.text_position = None
        self.is_text_editing = False
        self.live_text = None
        self.editing_text_action = None

        self._setup_gestures()

    def set_picture_reference(self, picture: Gtk.Picture) -> None:
        self.picture_widget = picture
        picture.connect("notify::paintable", lambda *args: self.queue_draw())

    def set_controls_overlay(self, controls_overlay) -> None:
        self.controls_overlay = controls_overlay

    @property
    def selected_action(self) -> DrawingAction | None:
        return self._selected_action

    @selected_action.setter
    def selected_action(self, action: DrawingAction | None) -> None:
        self._selected_action = action
        self.controls_overlay.set_delete_visible(action is not None)

    def _get_image_bounds(self):
        if not self.picture_widget or not hasattr(self.picture_widget, 'get_allocated_width'):
            return 0, 0, self.get_width(), self.get_height()

        if hasattr(self.picture_widget, 'get_root') and self.picture_widget.get_root():
            main_window = self.picture_widget.get_root()
            if hasattr(main_window, 'processed_surface') and main_window.processed_surface:
                img_w = main_window.processed_surface.get_width()
                img_h = main_window.processed_surface.get_height()
            else:
                return 0, 0, self.picture_widget.get_allocated_width(), self.picture_widget.get_allocated_height()
        else:
            return 0, 0, self.picture_widget.get_allocated_width(), self.picture_widget.get_allocated_height()

        widget_w = self.picture_widget.get_allocated_width()
        widget_h = self.picture_widget.get_allocated_height()

        if img_w <= 0 or img_h <= 0:
            return 0, 0, widget_w, widget_h

        scale = min(widget_w / img_w, widget_h / img_h)
        disp_w = img_w * scale
        disp_h = img_h * scale
        offset_x = (widget_w - disp_w) / 2
        offset_y = (widget_h - disp_h) / 2
        return offset_x, offset_y, disp_w, disp_h

    def _get_modified_image_bounds(self):
        if not self.picture_widget or not hasattr(self.picture_widget, 'get_root'):
            return self.get_width(), self.get_height()

        if hasattr(self.picture_widget, 'get_root') and self.picture_widget.get_root():
            main_window = self.picture_widget.get_root()
            if hasattr(main_window, 'processed_surface') and main_window.processed_surface:
                return main_window.processed_surface.get_width(), main_window.processed_surface.get_height()

        return self.picture_widget.get_allocated_width(), self.picture_widget.get_allocated_height()

    def _get_scale_factor(self):
        ox, oy, dw, dh = self._get_image_bounds()
        if not self.picture_widget or not hasattr(self.picture_widget, 'get_root'):
            return 1.0

        if hasattr(self.picture_widget, 'get_root') and self.picture_widget.get_root():
            main_window = self.picture_widget.get_root()
            if hasattr(main_window, 'processed_surface') and main_window.processed_surface:
                img_w = main_window.processed_surface.get_width()
                return dw / img_w if img_w else 1.0

        return 1.0

    def _widget_to_image_coords(self, x, y):
        ox, oy, dw, dh = self._get_image_bounds()
        return ((x - ox) / dw, (y - oy) / dh) if dw and dh else (x, y)

    def _image_to_widget_coords(self, rx, ry):
        ox, oy, dw, dh = self._get_image_bounds()
        return (ox + rx * dw, oy + ry * dh)

    def _is_point_in_image(self, x, y):
        ox, oy, dw, dh = self._get_image_bounds()
        return ox <= x <= ox + dw and oy <= y <= oy + dh

    def _get_background_pixbuf(self):
        """Get the background image as a pixbuf"""
        if not self.picture_widget:
            return None

        paintable = self.picture_widget.get_paintable()
        if isinstance(paintable, Gdk.Texture):
            return Gdk.pixbuf_get_from_texture(paintable)

        return None

    def _setup_actions(self):
        for mode in DrawingMode:
            action = Gio.SimpleAction.new(f"drawing-mode-{mode.value}", None)
            action.connect("activate", lambda a, p, m=mode: self.set_drawing_mode(m))
            root = self.get_root()
            if hasattr(root, "add_action"):
                root.add_action(action)

    def _get_number_actions(self):
        return [action for action in self.actions if isinstance(action, NumberStampAction)]

    def _renumber_actions(self):
        number_actions = self._get_number_actions()
        number_actions.sort(key=lambda action: action.creation_time)

        for i, action in enumerate(number_actions, 1):
            action.number = i

        self._next_number = len(number_actions) + 1

    def remove_selected_action(self) -> bool:
        if self.selected_action and self.selected_action in self.actions:
            was_number_action = isinstance(self.selected_action, NumberStampAction)
            self.actions.remove(self.selected_action)
            self.selected_action = None
            self.redo_stack.clear()

            if was_number_action:
                self._renumber_actions()

            self.queue_draw()
            return True
        return False

    def set_drawing_mode(self, mode: DrawingMode) -> None:
        if self.text_entry_popup:
            self._close_text_entry()

        if mode != DrawingMode.SELECT:
            self.selected_action = None

        self.drawing_mode = mode
        self.is_drawing = False
        self.is_moving_selection = False
        self.current_stroke.clear()
        self.start_point = None
        self.end_point = None
        self.queue_draw()

    def _find_action_at_point(self, x, y):
        for action in reversed(self.actions):
            if action.contains_point(x, y):
                return action
        return None

    def _is_point_in_selection_bounds(self, x, y):
        if not self.selected_action:
            return False

        min_x, min_y, max_x, max_y = self.selected_action.get_bounds()
        padding_img = max(self.pen_size, self.arrow_head_size, self.font_size / 2) / 200.0
        return min_x - padding_img <= x <= max_x + padding_img and min_y - padding_img <= y <= max_y + padding_img

    def _draw_selection_box(self, cr, scale):
        if not self.selected_action:
            return

        min_x, min_y, max_x, max_y = self.selected_action.get_bounds()
        x1, y1 = self._image_to_widget_coords(min_x, min_y)
        x2, y2 = self._image_to_widget_coords(max_x, max_y)

        padding = SELECTION_BOX_PADDING
        x, y = x1 - padding, y1 - padding
        w, h = (x2 - x1) + 2 * padding, (y2 - y1) + 2 * padding

        accent = Adw.StyleManager.get_default().get_accent_color_rgba()
        cr.set_source_rgba(*accent)
        cr.set_line_width(1.0)
        cr.set_dash([5.0, 5.0])
        cr.rectangle(x, y, w, h)
        cr.stroke()
        cr.set_dash([])

    def _setup_gestures(self):
        click = Gtk.GestureClick.new()
        click.set_button(1)
        click.connect("pressed", self._on_click)
        self.add_controller(click)

        drag = Gtk.GestureDrag.new()
        drag.set_button(1)
        drag.connect("drag-begin", self._on_drag_begin)
        drag.connect("drag-update", self._on_drag_update)
        drag.connect("drag-end", self._on_drag_end)
        self.add_controller(drag)

        motion = Gtk.EventControllerMotion.new()
        motion.connect("motion", self._on_motion)
        self.add_controller(motion)

    def _on_click(self, gesture, n_press, x, y):
        if self.drawing_mode == DrawingMode.TEXT and self._is_point_in_image(x, y):
            self.grab_focus()
            if n_press == 1:
                self._show_text_entry(x, y)
        elif self.drawing_mode == DrawingMode.NUMBER and self._is_point_in_image(x, y) and n_press == 1:
            self.grab_focus()
            rel_x, rel_y = self._widget_to_image_coords(x, y)
            number_action = NumberStampAction(
                position=(rel_x, rel_y),
                number=self._next_number, # Assign the current _next_number
                radius=self.number_radius / 1000.0,
                fill_color=self.pen_color
            )

            self.actions.append(number_action)
            self._renumber_actions() # Recalculate numbers based on chronological order
            self.redo_stack.clear()
            self.queue_draw()

        elif self.drawing_mode == DrawingMode.SELECT and self._is_point_in_image(x, y):
            self.grab_focus()
            img_x, img_y = self._widget_to_image_coords(x, y)

            if (n_press == 2 and
                self.selected_action and
                isinstance(self.selected_action, TextAction) and
                self.selected_action.contains_point(img_x, img_y)):
                self._start_text_edit(self.selected_action, x, y)
                return

            if n_press == 1:
                if self.selected_action and not self._is_point_in_selection_bounds(img_x, img_y):
                    self.selected_action = None
                    self.queue_draw()

                action = self._find_action_at_point(img_x, img_y)
                if action and action != self.selected_action:
                    self.selected_action = action
                    self.queue_draw()
                elif not action and self.selected_action:
                    self.selected_action = None
                    self.queue_draw()

    def _start_text_edit(self, text_action, widget_x, widget_y):
        self.editing_text_action = text_action
        self.text_position = text_action.position
        self.is_text_editing = True
        self.live_text = text_action.text

        self.text_entry_popup = TextEntryPopover(
            parent=self,
            on_text_activate=self._on_text_entry_activate,
            on_text_changed=self._on_text_entry_changed,
            on_font_size_changed=self._on_font_size_changed,
            font_size=text_action.font_size,
            initial_text=text_action.text
        )
        self.text_entry_popup.connect("closed", self._on_text_entry_popover_closed)
        self.text_entry_popup.popup_at_widget_coords(self, widget_x, widget_y)

    def _show_text_entry(self, x, y):
        if self.text_entry_popup:
            self.text_entry_popup.popdown()
            self.text_entry_popup = None

        self.text_position = self._widget_to_image_coords(x, y)
        self.is_text_editing = True
        self.live_text = ""
        self.editing_text_action = None

        self.text_entry_popup = TextEntryPopover(
            parent=self,
            on_text_activate=self._on_text_entry_activate,
            on_text_changed=self._on_text_entry_changed,
            on_font_size_changed=self._on_font_size_changed,
            font_size=self.font_size
        )
        self.text_entry_popup.connect("closed", self._on_text_entry_popover_closed)
        self.text_entry_popup.popup_at_widget_coords(self, x, y)

    def _on_font_size_changed(self, spin_button):
        font_size = spin_button.get_value()
        if self.editing_text_action:
            self.editing_text_action.font_size = font_size
        else:
            self.font_size = font_size

        if self.live_text:
            self.queue_draw()

    def _on_text_entry_popover_closed(self, popover):
        if self.text_entry_popup and self.text_position:
            vbox = self.text_entry_popup.get_child()
            if vbox:
                entry = vbox.get_first_child()
                if entry and isinstance(entry, Gtk.Entry):
                    text = entry.get_text().strip()

                    if self.editing_text_action:
                        if text:
                            self.editing_text_action.text = text
                        else:
                            if self.editing_text_action in self.actions:
                                self.actions.remove(self.editing_text_action)
                            if self.selected_action == self.editing_text_action:
                                self.selected_action = None
                        self.redo_stack.clear()
                    else:
                        if text:
                            action = TextAction(
                                self.text_position,
                                text,
                                self.pen_color,
                                self.font_size,
                                self._get_modified_image_bounds(),
                                self.font_family
                            )
                            self.actions.append(action)
                            self.redo_stack.clear()

        self._cleanup_text_entry()
        self.queue_draw()

    def _on_text_entry_changed(self, entry):
        self.live_text = entry.get_text()
        if self.editing_text_action:
            self.editing_text_action.text = self.live_text
        self.queue_draw()

    def _on_text_entry_activate(self, entry):
        self._close_text_entry()
        self.queue_draw()

    def _cleanup_text_entry(self):
        if self.text_entry_popup:
            self.text_entry_popup = None
        self.text_position = None
        self.live_text = None
        self.is_text_editing = False
        self.editing_text_action = None

    def _close_text_entry(self):
        if self.text_entry_popup:
            self.text_entry_popup.popdown()
            self.text_entry_popup = None
        self.text_position = None
        self.live_text = None
        self.is_text_editing = False
        self.editing_text_action = None

    def _on_drag_begin(self, gesture, x, y):
        if self.drawing_mode == DrawingMode.TEXT or self.drawing_mode == DrawingMode.NUMBER or self.text_entry_popup:
            return
        if not self._is_point_in_image(x, y):
            return

        self.grab_focus()
        rel_x, rel_y = self._widget_to_image_coords(x, y)

        if self.drawing_mode == DrawingMode.SELECT:
            if self.selected_action and self._is_point_in_selection_bounds(rel_x, rel_y):
                self.is_moving_selection = True
                self.move_start_point = (rel_x, rel_y)
            else:
                self.selected_action = self._find_action_at_point(rel_x, rel_y)
                if self.selected_action:
                    self.is_moving_selection = True
                    self.move_start_point = (rel_x, rel_y)
            self.queue_draw()
            return

        self.is_drawing = True
        rel = self._widget_to_image_coords(x, y)
        if self.drawing_mode == DrawingMode.PEN or self.drawing_mode == DrawingMode.HIGHLIGHTER:
            self.current_stroke = [rel]
        else:
            self.start_point = rel
            self.end_point = rel

    def _on_drag_update(self, gesture, dx, dy):
        if self.drawing_mode == DrawingMode.TEXT or self.drawing_mode == DrawingMode.NUMBER:
            return

        start = gesture.get_start_point()
        cur_x, cur_y = start.x + dx, start.y + dy
        rel_x, rel_y = self._widget_to_image_coords(cur_x, cur_y)

        if self.drawing_mode == DrawingMode.SELECT and self.is_moving_selection and self.selected_action and self.move_start_point:
            old_x, old_y = self.move_start_point
            delta_x = rel_x - old_x
            delta_y = rel_y - old_y
            self.selected_action.translate(delta_x, delta_y)
            self.move_start_point = (rel_x, rel_y)
            self.queue_draw()
            return

        if not self.is_drawing:
            return

        if self.drawing_mode == DrawingMode.PEN or self.drawing_mode == DrawingMode.HIGHLIGHTER:
            self.current_stroke.append((rel_x, rel_y))
        else:
            self.end_point = (rel_x, rel_y)
        self.queue_draw()

    def _on_drag_end(self, gesture, dx, dy):
        if self.drawing_mode == DrawingMode.TEXT or self.drawing_mode == DrawingMode.NUMBER:
            return

        if self.drawing_mode == DrawingMode.SELECT:
            self.is_moving_selection = False
            self.move_start_point = None
            return

        if not self.is_drawing:
            return

        self.is_drawing = False
        mode = self.drawing_mode
        if (mode == DrawingMode.PEN or mode == DrawingMode.HIGHLIGHTER) and len(self.current_stroke) > 1:
            if mode == DrawingMode.PEN:
                self.actions.append(StrokeAction(self.current_stroke.copy(), self.pen_color, self.pen_size))
            else:
                self.actions.append(HighlighterAction(self.current_stroke.copy(), self.highlighter_color, self.highlighter_size))
            self.current_stroke.clear()
        elif self.start_point and self.end_point:
            if mode == DrawingMode.ARROW:
                self.actions.append(ArrowAction(self.start_point, self.end_point, self.pen_color, self.arrow_head_size, self.pen_size))
            elif mode == DrawingMode.LINE:
                self.actions.append(LineAction(self.start_point, self.end_point, self.pen_color, 0, self.pen_size))
            elif mode == DrawingMode.SQUARE:
                self.actions.append(RectAction(self.start_point, self.end_point, self.pen_color, self.pen_size, self.fill_color))
            elif mode == DrawingMode.CIRCLE:
                self.actions.append(CircleAction(self.start_point, self.end_point, self.pen_color, self.pen_size, self.fill_color))
            elif mode == DrawingMode.CENSOR:
                censor_action = CensorAction(self.start_point, self.end_point, self.pixelation_level, self._get_background_pixbuf())
                self.actions.append(censor_action)

        self.start_point = None
        self.end_point = None
        self.redo_stack.clear()
        self.queue_draw()

    def _on_motion(self, controller, x, y):
        if self.drawing_mode == DrawingMode.TEXT:
            name = "text" if self._is_point_in_image(x, y) else "default"
        elif self.drawing_mode == DrawingMode.NUMBER:
            name = "crosshair" if self._is_point_in_image(x, y) else "default"
        elif self.drawing_mode == DrawingMode.SELECT:
            img_x, img_y = self._widget_to_image_coords(x, y)
            if self.selected_action and self._is_point_in_selection_bounds(img_x, img_y):
                name = "grab"
            elif self._find_action_at_point(img_x, img_y):
                name = "pointer"
            else:
                name = "default"
        elif self.drawing_mode == DrawingMode.CENSOR:
            name = "crosshair" if self._is_point_in_image(x, y) else "default"
        else:
            name = "crosshair" if self.drawing_mode == DrawingMode.PEN or self.drawing_mode == DrawingMode.HIGHLIGHTER else "cell"
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
            if action == self.editing_text_action and self.is_text_editing:
                continue
            action.draw(cr, self._image_to_widget_coords, scale)

        # TODO: Convert to switch...case statements, cuz this looks horrible
        if self.is_drawing and self.drawing_mode != DrawingMode.TEXT and self.drawing_mode != DrawingMode.NUMBER:
            cr.set_source_rgba(*self.pen_color)
            if self.drawing_mode == DrawingMode.PEN and len(self.current_stroke) > 1:
                StrokeAction(self.current_stroke, self.pen_color, self.pen_size).draw(cr, self._image_to_widget_coords, scale)
            elif self.drawing_mode == DrawingMode.HIGHLIGHTER and len(self.current_stroke) > 1:
                HighlighterAction(self.current_stroke, self.highlighter_color, self.highlighter_size).draw(cr, self._image_to_widget_coords, scale)
            elif self.start_point and self.end_point:
                if self.drawing_mode == DrawingMode.ARROW:
                    ArrowAction(self.start_point, self.end_point, self.pen_color, self.arrow_head_size, self.pen_size).draw(cr, self._image_to_widget_coords, scale)
                elif self.drawing_mode == DrawingMode.LINE:
                    LineAction(self.start_point, self.end_point, self.pen_color, 0, self.pen_size).draw(cr, self._image_to_widget_coords, scale)
                elif self.drawing_mode == DrawingMode.SQUARE:
                    RectAction(self.start_point, self.end_point, self.pen_color, self.pen_size, self.fill_color).draw(cr, self._image_to_widget_coords, scale)
                elif self.drawing_mode == DrawingMode.CIRCLE:
                    CircleAction(self.start_point, self.end_point, self.pen_color, self.pen_size, self.fill_color).draw(cr, self._image_to_widget_coords, scale)
                elif self.drawing_mode == DrawingMode.CENSOR:
                    cr.set_source_rgba(0.5, 0.5, 0.5, 0.5)
                    x1, y1 = self._image_to_widget_coords(*self.start_point)
                    x2, y2 = self._image_to_widget_coords(*self.end_point)
                    x, y = min(x1, x2), min(y1, y2)
                    w, h = abs(x2 - x1), abs(y2 - y1)
                    cr.rectangle(x, y, w, h)
                    cr.fill()

        if self.is_text_editing and self.text_position and self.live_text:
            if self.editing_text_action:
                preview = TextAction(
                    self.text_position,
                    self.live_text,
                    self.editing_text_action.color,
                    self.editing_text_action.font_size,
                    self._get_modified_image_bounds(),
                    self.editing_text_action.font_family
                )
            else:
                preview = TextAction(
                    self.text_position,
                    self.live_text,
                    self.pen_color,
                    self.font_size,
                    self._get_modified_image_bounds(),
                    self.font_family
                )
            preview.draw(cr, self._image_to_widget_coords, scale)

        if self.selected_action:
            self._draw_selection_box(cr, scale)

    def export_to_cairo_surface(self) -> cairo.ImageSurface | None:
        base_surface = None
        img_w, img_h = 0, 0

        main_window = self.get_root()
        if hasattr(main_window, 'processed_surface') and main_window.processed_surface:
            base_surface = main_window.processed_surface
            img_w = base_surface.get_width()
            img_h = base_surface.get_height()
        elif self.picture_widget:
            paintable = self.picture_widget.get_paintable()
            if paintable:
                img_w = paintable.get_intrinsic_width()
                img_h = paintable.get_intrinsic_height()
                if img_w <= 0 or img_h <= 0:
                    img_w = self.picture_widget.get_allocated_width()
                    img_h = self.picture_widget.get_allocated_height()

                if img_w <= 0 or img_h <= 0:
                    return None

                temp_surface = cairo.ImageSurface(cairo.Format.ARGB32, img_w, img_h)
                temp_cr = cairo.Context(temp_surface)
                paintable.snapshot(temp_cr, 0, 0, img_w, img_h)
                base_surface = temp_surface

        if not base_surface or img_w <= 0 or img_h <= 0:
            return None

        final_surface = cairo.ImageSurface(cairo.Format.ARGB32, img_w, img_h)
        cr = cairo.Context(final_surface)

        cr.set_operator(cairo.Operator.CLEAR)
        cr.paint()
        cr.set_operator(cairo.Operator.OVER)

        cr.set_source_surface(base_surface, 0, 0)
        cr.paint()

        def image_coords_to_surface_coords(x_norm, y_norm):
            return (x_norm * img_w, y_norm * img_h)

        cr.set_line_cap(cairo.LineCap.ROUND)
        cr.set_line_join(cairo.LineJoin.ROUND)

        for action in self.actions:
            action.draw(cr, image_coords_to_surface_coords, 1.0)

        final_surface.flush()
        return final_surface

    def clear_drawing(self) -> None:
        self._close_text_entry()
        self.actions.clear()
        self.redo_stack.clear()
        self.selected_action = None
        self._next_number = 1
        self.queue_draw()

    def undo(self) -> None:
        if self.actions:
            undone_action = self.actions.pop()
            self.redo_stack.append(undone_action)
            self.selected_action = None

            if isinstance(undone_action, NumberStampAction):
                self._renumber_actions()

            self.queue_draw()

    def redo(self) -> None:
        if self.redo_stack:
            redone_action = self.redo_stack.pop()
            self.actions.append(redone_action)
            self.selected_action = None

            if isinstance(redone_action, NumberStampAction):
                self._renumber_actions()

            self.queue_draw()

    def set_pen_color(self, r: float, g: float, b: float, a: float=1.0) -> None:
        self.pen_color = (r, g, b, a)

    def set_fill_color(self, r: float, g: float, b: float, a: float=1) -> None:
        self.fill_color = (r, g, b, a)

    def set_highlighter_color(self, r: float, g: float, b: float, a: float=1) -> None:
        self.highlighter_color = (r, g, b, a)

    def set_pen_size(self, size: float) -> None:
        self.pen_size = max(1.0, size)

    def set_arrow_head_size(self, size: float) -> None:
        self.arrow_head_size = max(5.0, size)

    def set_font_size(self, size: float) -> None:
        self.font_size = max(8.0, size)

    def set_font_family(self, family: str) -> None:
        self.font_family = family if family else "Sans"

    def set_highlighter_size(self, size: float) -> None:
        self.highlighter_size = max(1.0, size)

    def set_pixelation_level(self, level: int) -> None:
        self.pixelation_level = max(2, int(level))

    def set_drawing_visible(self, is_visible: bool) -> None:
        self.set_visible(is_visible)

    def get_drawing_visible(self) -> bool:
        return self.get_visible()

    def set_number_radius(self, radius: float) -> None:
        self.number_radius = radius

