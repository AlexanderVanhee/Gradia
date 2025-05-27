from gi.repository import Gtk, Gdk, Gio, cairo
from typing import Tuple, List, Optional, Union
from enum import Enum
import math

class DrawingMode(Enum):
    PEN = "pen"
    ARROW = "arrow"

class DrawingAction:
    def draw(self, cr: cairo.Context, image_to_widget_coords):
        raise NotImplementedError

class StrokeAction(DrawingAction):
    def __init__(self, stroke: List[Tuple[float, float]], color: Tuple[float, float, float, float], pen_size: float):
        self.stroke = stroke
        self.color = color
        self.pen_size = pen_size

    def draw(self, cr: cairo.Context, image_to_widget_coords):
        if len(self.stroke) < 2:
            return

        coords = [image_to_widget_coords(x, y) for x, y in self.stroke]

        cr.set_source_rgba(*self.color)
        cr.move_to(*coords[0])
        for point in coords[1:]:
            cr.line_to(*point)
        cr.stroke()

class ArrowAction(DrawingAction):
    def __init__(self, start: Tuple[float, float], end: Tuple[float, float], color: Tuple[float, float, float, float], arrow_head_size: float):
        self.start = start
        self.end = end
        self.color = color
        self.arrow_head_size = arrow_head_size

    def draw(self, cr: cairo.Context, image_to_widget_coords):
        start_x, start_y = image_to_widget_coords(*self.start)
        end_x, end_y = image_to_widget_coords(*self.end)

        distance = math.hypot(end_x - start_x, end_y - start_y)
        if distance < 2:
            return

        cr.set_source_rgba(*self.color)
        cr.move_to(start_x, start_y)
        cr.line_to(end_x, end_y)
        cr.stroke()

        angle = math.atan2(end_y - start_y, end_x - start_x)
        head_len = min(self.arrow_head_size, distance * 0.3)
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

class DrawingOverlay(Gtk.DrawingArea):
    def __init__(self):
        super().__init__()
        self.set_draw_func(self._on_draw)
        self.set_can_focus(True)

        self.picture_widget: Optional[Gtk.Picture] = None

        # Drawing state
        self.drawing_mode = DrawingMode.PEN
        self.pen_size = 3.0
        self.arrow_head_size = 12.0
        self.pen_color = (1.0, 1.0, 1.0, 0.8)
        self.is_drawing = False

        # In-progress data
        self.current_stroke: List[Tuple[float, float]] = []
        self.current_arrow_start: Optional[Tuple[float, float]] = None
        self.current_arrow_end: Optional[Tuple[float, float]] = None

        # Drawing history
        self.actions: List[DrawingAction] = []
        self.redo_stack: List[DrawingAction] = []

        self._setup_gestures()
        self._setup_actions()

    # Coordinate helpers
    def set_picture_reference(self, picture: Gtk.Picture):
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
        pen = Gio.SimpleAction.new("drawing-mode-pen", None)
        pen.connect("activate", lambda a, p: self.set_drawing_mode(DrawingMode.PEN))
        arrow = Gio.SimpleAction.new("drawing-mode-arrow", None)
        arrow.connect("activate", lambda a, p: self.set_drawing_mode(DrawingMode.ARROW))
        root = self.get_root()
        if hasattr(root, "add_action"):
            root.add_action(pen)
            root.add_action(arrow)

    def set_drawing_mode(self, mode: DrawingMode):
        self.drawing_mode = mode
        self.is_drawing = False
        self.current_stroke.clear()
        self.current_arrow_start = None
        self.current_arrow_end = None
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
        elif self.drawing_mode == DrawingMode.ARROW:
            self.current_arrow_start = rel
            self.current_arrow_end = rel

    def _on_drag_update(self, gesture, dx, dy):
        if not self.is_drawing:
            return
        start = gesture.get_start_point()
        cur_x, cur_y = start.x + dx, start.y + dy
        rel = self._widget_to_image_coords(cur_x, cur_y)
        if self.drawing_mode == DrawingMode.PEN:
            self.current_stroke.append(rel)
        elif self.drawing_mode == DrawingMode.ARROW:
            self.current_arrow_end = rel
        self.queue_draw()

    def _on_drag_end(self, gesture, dx, dy):
        if not self.is_drawing:
            return
        self.is_drawing = False
        if self.drawing_mode == DrawingMode.PEN and len(self.current_stroke) > 1:
            self.actions.append(StrokeAction(self.current_stroke.copy(), self.pen_color, self.pen_size))
            self.redo_stack.clear()
            self.current_stroke.clear()
        elif self.drawing_mode == DrawingMode.ARROW and self.current_arrow_start and self.current_arrow_end:
            start_px = self._image_to_widget_coords(*self.current_arrow_start)
            end_px = self._image_to_widget_coords(*self.current_arrow_end)
            if math.hypot(end_px[0] - start_px[0], end_px[1] - start_px[1]) > 5:
                self.actions.append(ArrowAction(self.current_arrow_start, self.current_arrow_end, self.pen_color, self.arrow_head_size))
                self.redo_stack.clear()
            self.current_arrow_start = None
            self.current_arrow_end = None
        self.queue_draw()

    def _on_motion(self, controller, x, y):
        name = "crosshair" if self.drawing_mode == DrawingMode.PEN else "cell"
        if not self._is_point_in_image(x, y):
            name = "default"
        self.set_cursor(Gdk.Cursor.new_from_name(name, None))

    def _on_draw(self, area, cr, width, height):
        cr.set_line_cap(cairo.LineCap.ROUND)
        cr.set_line_join(cairo.LineJoin.ROUND)
        cr.set_line_width(self.pen_size)
        ox, oy, dw, dh = self._get_image_bounds()
        cr.rectangle(ox, oy, dw, dh)
        cr.clip()

        for action in self.actions:
            action.draw(cr, self._image_to_widget_coords)

        if self.is_drawing:
            cr.set_source_rgba(*self.pen_color)
            if self.drawing_mode == DrawingMode.PEN and len(self.current_stroke) > 1:
                StrokeAction(self.current_stroke, self.pen_color, self.pen_size).draw(cr, self._image_to_widget_coords)
            elif self.drawing_mode == DrawingMode.ARROW and self.current_arrow_start and self.current_arrow_end:
                ArrowAction(self.current_arrow_start, self.current_arrow_end, self.pen_color, self.arrow_head_size).draw(cr, self._image_to_widget_coords)


    # API
    def export_to_pixbuf(self):
        if not self.picture_widget or not self.picture_widget.get_paintable():
            return None

        img_w = self.picture_widget.get_paintable().get_intrinsic_width()
        img_h = self.picture_widget.get_paintable().get_intrinsic_height()
        if img_w <= 0 or img_h <= 0:
            return None

        surface = cairo.ImageSurface(cairo.Format.ARGB32, img_w, img_h)
        cr = cairo.Context(surface)
        def image_coords_to_self(x, y):
            return (x * img_w, y * img_h)

        cr.set_line_cap(cairo.LineCap.ROUND)
        cr.set_line_join(cairo.LineJoin.ROUND)
        cr.set_line_width(self.pen_size)

        for action in self.actions:
            action.draw(cr, image_coords_to_self)

        surface.flush()
        return Gdk.pixbuf_get_from_surface(surface, 0, 0, img_w, img_h)

    def clear_drawing(self):
        self.actions.clear()
        self.redo_stack.clear()
        self.queue_draw()

    def undo(self):
        if self.actions:
            self.redo_stack.append(self.actions.pop())
            self.queue_draw()

    def redo(self):
        if self.redo_stack:
            self.actions.append(self.redo_stack.pop())
            self.queue_draw()

    def set_pen_color(self, r, g, b, a=0.8): self.pen_color = (r, g, b, a)
    def set_pen_size(self, s): self.pen_size = max(1.0, s)
    def set_arrow_head_size(self, s): self.arrow_head_size = max(5.0, s)
    def set_drawing_visible(self, v): self.set_visible(v)
    def get_drawing_visible(self): return self.get_visible()
    def trigger_pen_mode(self): self.set_drawing_mode(DrawingMode.PEN)
    def trigger_arrow_mode(self): self.set_drawing_mode(DrawingMode.ARROW)
    def toggle_drawing_mode(self):
        self.set_drawing_mode(DrawingMode.ARROW if self.drawing_mode == DrawingMode.PEN else DrawingMode.PEN)

