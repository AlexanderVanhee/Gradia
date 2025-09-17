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

import cairo

from typing import Callable
from gi.repository import Gtk, Gdk, Gio, Pango, PangoCairo, GdkPixbuf
from enum import Enum
import math
from gradia.backend.logger import Logger
from gradia.utils.colors import has_visible_color
import time
import random
import unicodedata

logging = Logger()

start_time_seed = int(time.time())


class DrawingMode(Enum):
    SELECT = "SELECT"
    PEN = "PEN"
    TEXT = "TEXT"
    LINE = "LINE"
    ARROW = "ARROW"
    SQUARE = "SQUARE"
    CIRCLE = "CIRCLE"
    HIGHLIGHTER = "HIGHLIGHTER"
    CENSOR = "CENSOR"
    NUMBER = "NUMBER"

    def label(self):
        return {
            "PEN": _("Pen"),
            "ARROW": _("Arrow"),
            "LINE": _("Line"),
            "SQUARE": _("Rectangle"),
            "CIRCLE": _("Oval"),
            "TEXT": _("Text"),
            "SELECT": _("Select"),
            "HIGHLIGHTER": _("Highlighter"),
            "CENSOR": _("Censor"),
            "NUMBER": _("Number"),
        }[self.value]

    @property
    def shortcuts(self):
        return DrawingMode._shortcuts[self]

DrawingMode._shortcuts = {
    DrawingMode.SELECT:       ["0", "KP_0", "grave", "s"],
    DrawingMode.PEN:          ["1", "KP_1", "d", "p"],
    DrawingMode.TEXT:         ["2", "KP_2", "t"],
    DrawingMode.LINE:         ["3", "KP_3", "l"],
    DrawingMode.ARROW:        ["4", "KP_4", "a"],
    DrawingMode.SQUARE:       ["5", "KP_5", "r"],
    DrawingMode.CIRCLE:       ["6", "KP_6", "o"],
    DrawingMode.HIGHLIGHTER:  ["7", "KP_7", "h"],
    DrawingMode.CENSOR:       ["8", "KP_8", "c"],
    DrawingMode.NUMBER:       ["9", "KP_9", "n"],
}


class DrawingAction:
    def draw(self, cr: cairo.Context, image_to_widget_coords: Callable[[int, int], tuple[float, float]], scale: float):
        raise NotImplementedError

    def get_bounds(self) -> tuple[int, int, int, int]:
        raise NotImplementedError

    def contains_point(self, x_img: int, y_img: int) -> bool:
        min_x, min_y, max_x, max_y = self.get_bounds()
        if isinstance(self, (LineAction, ArrowAction)):
            px, py = x_img, y_img
            x1, y1 = self.start
            x2, y2 = self.end
            line_len_sq = (x2 - x1) ** 2 + (y2 - y1) ** 2
            if line_len_sq == 0:
                return math.hypot(px - x1, py - y1) < (5 + self.width)
            t = ((px - x1) * (x2 - x1) + (py - y1) * (y2 - y1)) / line_len_sq
            t = max(0, min(1, t))
            closest_x = x1 + t * (x2 - x1)
            closest_y = y1 + t * (y2 - y1)
            dist_sq = (px - closest_x)**2 + (py - closest_y)**2
            return dist_sq < (5 + self.width)**2
        return min_x <= x_img <= max_x and min_y <= y_img <= max_y

    def _calculate_shadow_color(self, color):
        r = color.red
        g = color.green
        b = color.blue
        luminance = 0.299 * r + 0.587 * g + 0.114 * b
        if luminance < 0.5:
            return (1.0, 1.0, 1.0, 0.05)
        else:
            return (0.0, 0.0, 0.0, 0.3)

    def translate(self, dx: int, dy: int):
        raise NotImplementedError

class StrokeAction(DrawingAction):
    def __init__(self, stroke: list[tuple[int, int]], options):
        self.stroke = stroke
        self.color = options.primary_color
        self.pen_size = options.size
        self._bounds = None
        self.shadow_color = self._calculate_shadow_color(self.color)

    def draw(self, cr: cairo.Context, image_to_widget_coords: Callable[[int, int], tuple[float, float]], scale: float):
        if len(self.stroke) < 2:
            return
        coords = [image_to_widget_coords(x, y) for x, y in self.stroke]
        shadow_offset = 2 * scale
        line_width = self.pen_size * scale
        self._build_path(cr, coords)
        path = cr.copy_path()
        cr.save()
        cr.translate(shadow_offset, shadow_offset)
        cr.append_path(path)
        cr.set_source_rgba(*self.shadow_color)
        cr.set_line_width(line_width)
        cr.stroke()
        cr.restore()
        cr.append_path(path)
        cr.set_source_rgba(*self.color)
        cr.set_line_width(line_width)
        cr.stroke()

    def _build_path(self, cr, coords):
        cr.set_line_cap(cairo.LineCap.ROUND)
        cr.set_line_join(cairo.LineJoin.ROUND)
        if len(coords) <= 2:
            cr.move_to(*coords[0])
            if len(coords) == 2:
                cr.line_to(*coords[1])
            return
        cr.move_to(*coords[0])
        for i in range(1, len(coords) - 1):
            x1, y1 = coords[i]
            x2, y2 = coords[i + 1]
            mid_x = (x1 + x2) * 0.5
            mid_y = (y1 + y2) * 0.5
            cr.curve_to(x1, y1, x1, y1, mid_x, mid_y)
        cr.line_to(*coords[-1])

    def get_bounds(self) -> tuple[int, int, int, int]:
        if self._bounds is None:
            if not self.stroke:
                self._bounds = (0, 0, 0, 0)
            else:
                xs, ys = zip(*self.stroke)
                padding = self.pen_size // 2 + 5
                self._bounds = (min(xs) - padding, min(ys) - padding, max(xs) + padding, max(ys) + padding)
        return self._bounds

    def translate(self, dx: int, dy: int):
        self.stroke = [(x + dx, y + dy) for x, y in self.stroke]
        self._bounds = None

class ArrowAction(DrawingAction):
    ARROW_HEAD_SIZE_MULTIPLIER = 4
    HEAD_WIDTH_RATIO = 0.6
    SHAFT_WIDTH_RATIO = 0.5
    SHAFT_START_WIDTH_RATIO = 0.3
    MAX_HEAD_LENGTH_RATIO = 0.3
    MIN_DISTANCE_THRESHOLD = 2

    def __init__(self, start: tuple[int, int], end: tuple[int, int], shift: bool, options):
        self.start = start
        if shift:
            dx = abs(end[0] - start[0])
            dy = abs(end[1] - start[1])
            if dx > dy:
                self.end = (end[0], start[1])
            else:
                self.end = (start[0], end[1])
        else:
            self.end = end
        self.color = options.primary_color
        self.arrow_head_size = options.size * self.ARROW_HEAD_SIZE_MULTIPLIER
        self.width = options.size
        self.shadow_color = self._calculate_shadow_color(self.color)

    def draw(self, cr: cairo.Context, image_to_widget_coords: Callable[[int, int], tuple[float, float]], scale: float):
        start_x, start_y = image_to_widget_coords(*self.start)
        end_x, end_y = image_to_widget_coords(*self.end)
        distance = math.hypot(end_x - start_x, end_y - start_y)
        if distance < self.MIN_DISTANCE_THRESHOLD:
            return
        angle = math.atan2(end_y - start_y, end_x - start_x)
        cos_a = math.cos(angle)
        sin_a = math.sin(angle)
        start_offset = self.width * scale / 2
        adjusted_start_x = start_x + start_offset * cos_a
        adjusted_start_y = start_y + start_offset * sin_a
        adjusted_distance = math.hypot(end_x - adjusted_start_x, end_y - adjusted_start_y)
        if adjusted_distance < self.MIN_DISTANCE_THRESHOLD:
            return

        head_len = min(self.arrow_head_size * scale, adjusted_distance * self.MAX_HEAD_LENGTH_RATIO)
        head_width = head_len * self.HEAD_WIDTH_RATIO
        shaft_width = head_width * self.SHAFT_WIDTH_RATIO
        perp_cos = -sin_a
        perp_sin = cos_a
        shaft_end_x = end_x - head_len * cos_a
        shaft_end_y = end_y - head_len * sin_a
        shaft_start_half = shaft_width * self.SHAFT_START_WIDTH_RATIO
        shaft_end_half = shaft_width
        head_half = head_width

        self._build_arrow_path(cr, adjusted_start_x, adjusted_start_y, shaft_end_x, shaft_end_y,
                               end_x, end_y, angle, shaft_start_half, shaft_end_half,
                               head_half, perp_cos, perp_sin)
        path = cr.copy_path()

        shadow_offset = 3 * scale
        cr.save()
        cr.translate(shadow_offset, shadow_offset)
        cr.append_path(path)
        cr.set_source_rgba(*self.shadow_color)
        cr.fill()
        cr.restore()

        cr.append_path(path)
        cr.set_source_rgba(*self.color)
        cr.fill()

    def _build_arrow_path(self, cr, start_x, start_y, shaft_end_x, shaft_end_y,
                         end_x, end_y, angle, shaft_start_half, shaft_end_half,
                         head_half, perp_cos, perp_sin):
        cr.move_to(start_x + shaft_start_half * perp_cos, start_y + shaft_start_half * perp_sin)
        cr.arc(start_x, start_y, shaft_start_half, angle + math.pi/2, angle - math.pi/2)
        cr.line_to(shaft_end_x - shaft_end_half * perp_cos, shaft_end_y - shaft_end_half * perp_sin)
        cr.line_to(shaft_end_x - head_half * perp_cos, shaft_end_y - head_half * perp_sin)
        cr.line_to(end_x, end_y)
        cr.line_to(shaft_end_x + head_half * perp_cos, shaft_end_y + head_half * perp_sin)
        cr.line_to(shaft_end_x + shaft_end_half * perp_cos, shaft_end_y + shaft_end_half * perp_sin)
        cr.close_path()

    def get_bounds(self) -> tuple[int, int, int, int]:
        distance = math.hypot(self.end[0] - self.start[0], self.end[1] - self.start[1])
        if distance < self.MIN_DISTANCE_THRESHOLD:
            return (self.start[0], self.start[1], self.start[0], self.start[1])
        min_x = min(self.start[0], self.end[0])
        max_x = max(self.start[0], self.end[0])
        min_y = min(self.start[1], self.end[1])
        max_y = max(self.start[1], self.end[1])
        return (min_x , min_y , max_x, max_y)

    def translate(self, dx: int, dy: int):
        self.start = (self.start[0] + dx, self.start[1] + dy)
        self.end = (self.end[0] + dx, self.end[1] + dy)

class TextAction(DrawingAction):
    PADDING_X_IMG = 4
    PADDING_Y_IMG = 2

    def __init__(self, position: tuple[int, int], text: str, intrinsic_image_bounds: tuple[int, int], options, font_size):
        self.options = options
        self.position = position
        self.text = text
        self.intrinsic_image_bounds = intrinsic_image_bounds
        self.color = options.primary_color
        self.font_size = font_size
        self.font_family = options.font
        self.background_color = options.fill_color
        self.outline_color = options.border_color

    def contains_emoji(self) -> bool:
        for char in self.text:
            cat = unicodedata.category(char)
            if cat.startswith("S") or ord(char) > 0xFFFF:
                return True
            if "EMOJI" in unicodedata.name(char, "").upper():
                return True
        return False

    def draw_rounded_rectangle(self, cr: cairo.Context, x: float, y: float, width: float, height: float, radius: float, round_top: bool = True, round_bottom: bool = True):
        cr.new_sub_path()
        if round_top:
            cr.arc(x + radius, y + radius, radius, math.pi, 3 * math.pi / 2)
            cr.arc(x + width - radius, y + radius, radius, 3 * math.pi / 2, 0)
        else:
            cr.move_to(x, y)
            cr.line_to(x + width, y)

        if round_bottom:
            cr.arc(x + width - radius, y + height - radius, radius, 0, math.pi / 2)
            cr.arc(x + radius, y + height - radius, radius, math.pi / 2, math.pi)
        else:
            cr.line_to(x + width, y + height)
            cr.line_to(x, y + height)

        cr.close_path()

    def draw_per_line_background(self, cr: cairo.Context, layout, text_x_widget: float, text_y_widget: float, scale: float):
        lines = self.text.split('\n')
        if len(lines) <= 1:
            _, logical_rect = layout.get_extents()
            text_width_widget = logical_rect.width / Pango.SCALE
            text_height_widget = logical_rect.height / Pango.SCALE

            bg_x_widget = text_x_widget - self.PADDING_X_IMG * scale
            bg_y_widget = text_y_widget - self.PADDING_Y_IMG * scale
            bg_width_widget = text_width_widget + 2 * self.PADDING_X_IMG * scale
            bg_height_widget = text_height_widget + 2 * self.PADDING_Y_IMG * scale

            radius = min(6.0 * scale, min(bg_width_widget, bg_height_widget) / 4)
            self.draw_rounded_rectangle(cr, bg_x_widget, bg_y_widget, bg_width_widget, bg_height_widget, radius)
            cr.fill()
            return

        line_heights = []
        line_widths = []

        _, overall_logical_rect = layout.get_extents()
        overall_width = overall_logical_rect.width / Pango.SCALE

        for line in lines:
            temp_layout = PangoCairo.create_layout(cr)
            font_desc = Pango.FontDescription()
            font_desc.set_family(self.font_family)
            font_desc.set_size(int(self.font_size * scale * Pango.SCALE))
            temp_layout.set_font_description(font_desc)
            temp_layout.set_text(line, -1)
            temp_layout.set_alignment(Pango.Alignment.CENTER)

            _, logical_rect = temp_layout.get_extents()
            line_widths.append(logical_rect.width / Pango.SCALE)
            line_heights.append(logical_rect.height / Pango.SCALE)

        current_y = text_y_widget

        for i, (line_width, line_height) in enumerate(zip(line_widths, line_heights)):
            bg_x_widget = text_x_widget + (overall_width - line_width) / 2 - self.PADDING_X_IMG * scale
            bg_y_widget = current_y - self.PADDING_Y_IMG * scale
            bg_width_widget = line_width + 2 * self.PADDING_X_IMG * scale
            bg_height_widget = line_height + 2 * self.PADDING_Y_IMG * scale

            radius = min(6.0 * scale, min(bg_width_widget, bg_height_widget) / 4)

            round_top = True
            round_bottom = True

            if i > 0 and line_widths[i-1] >= line_width:
                round_top = False
            if i < len(lines) - 1 and line_widths[i+1] >= line_width:
                round_bottom = False

            self.draw_rounded_rectangle(cr, bg_x_widget, bg_y_widget, bg_width_widget, bg_height_widget, radius, round_top, round_bottom)
            cr.fill()

            current_y += line_height

    def draw(self, cr: cairo.Context, image_to_widget_coords: Callable[[int, int], tuple[float, float]], scale: float):
        if not self.text.strip():
            return

        x_widget, y_widget = image_to_widget_coords(*self.position)

        layout = PangoCairo.create_layout(cr)
        font_desc = Pango.FontDescription()
        font_desc.set_family(self.font_family)
        font_desc.set_size(int(self.font_size * scale * Pango.SCALE))
        layout.set_font_description(font_desc)
        layout.set_text(self.text, -1)
        layout.set_alignment(Pango.Alignment.CENTER)

        _, logical_rect = layout.get_extents()
        text_width_widget = logical_rect.width / Pango.SCALE
        text_height_widget = logical_rect.height / Pango.SCALE

        text_x_widget = x_widget - text_width_widget / 2
        text_y_widget = y_widget - text_height_widget

        if self.background_color and any(c > 0 for c in self.background_color):
            cr.set_source_rgba(*self.background_color)
            self.draw_per_line_background(cr, layout, text_x_widget, text_y_widget, scale)

        cr.move_to(text_x_widget, text_y_widget)
        if self.contains_emoji():
            cr.set_source_rgba(*self.color)
            PangoCairo.show_layout(cr, layout)
        else:
            PangoCairo.layout_path(cr, layout)
            if self.outline_color and any(c > 0 for c in self.outline_color):
                cr.set_source_rgba(*self.outline_color)
                base_line_width = 2.0
                adjusted_line_width = base_line_width * scale * (self.font_size / 14.0)
                cr.set_line_width(adjusted_line_width)
                cr.stroke_preserve()
            cr.set_source_rgba(*self.color)
            cr.fill()

    def get_bounds(self) -> tuple[int, int, int, int]:
        if not self.text.strip():
            x, y = self.position
            return (x, y, x, y)

        temp_surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, 1, 1)
        temp_cr = cairo.Context(temp_surface)
        layout = PangoCairo.create_layout(temp_cr)
        font_desc = Pango.FontDescription()
        font_desc.set_family(self.font_family)
        font_desc.set_size(int(self.font_size * Pango.SCALE))
        layout.set_font_description(font_desc)
        layout.set_text(self.text, -1)
        layout.set_alignment(Pango.Alignment.CENTER)

        _, logical_rect = layout.get_extents()
        text_width_img = int(logical_rect.width / Pango.SCALE)
        text_height_img = int(logical_rect.height / Pango.SCALE)

        x_img, y_img = self.position

        outline_padding = 0
        if self.outline_color and any(c > 0 for c in self.outline_color):
            outline_padding = int(2.0 * (self.font_size / 14.0)) + 1

        left_img = x_img - text_width_img // 2 - self.PADDING_X_IMG - outline_padding
        right_img = x_img + text_width_img // 2 + self.PADDING_X_IMG + outline_padding
        top_img = y_img - text_height_img - self.PADDING_Y_IMG - outline_padding
        bottom_img = y_img + self.PADDING_Y_IMG + outline_padding

        return (left_img, top_img, right_img, bottom_img)

    def translate(self, dx: int, dy: int):
        self.position = (self.position[0] + dx, self.position[1] + dy)

class LineAction(ArrowAction):
    def draw(self, cr: cairo.Context, image_to_widget_coords: Callable[[int, int], tuple[float, float]], scale: float):
        start = image_to_widget_coords(*self.start)
        end = image_to_widget_coords(*self.end)
        shadow_offset = 2 * scale
        line_width = self.width * scale

        cr.set_line_width(line_width)
        cr.move_to(*start)
        cr.line_to(*end)
        path = cr.copy_path()

        cr.save()
        cr.translate(shadow_offset, shadow_offset)
        cr.append_path(path)
        cr.set_source_rgba(*self.shadow_color)
        cr.stroke()
        cr.restore()

        cr.append_path(path)
        cr.set_source_rgba(*self.color)
        cr.stroke()

    def get_bounds(self) -> tuple[int, int, int, int]:
        min_x = min(self.start[0], self.end[0])
        max_x = max(self.start[0], self.end[0])
        min_y = min(self.start[1], self.end[1])
        max_y = max(self.start[1], self.end[1])
        return (min_x, min_y, max_x, max_y)

class RectAction(DrawingAction):
    def __init__(self, start: tuple[int, int], end: tuple[int, int], shift: bool, options):
        self.start = start
        self.end = end
        self.shift = shift
        self.color = options.primary_color
        self.width = options.size
        self.fill_color = options.fill_color

    def draw(self, cr: cairo.Context, image_to_widget_coords: Callable[[int, int], tuple[float, float]], scale: float):
        x1_widget, y1_widget = image_to_widget_coords(*self.start)
        x2_widget, y2_widget = image_to_widget_coords(*self.end)

        if self.shift:
            size = max(abs(x2_widget - x1_widget), abs(y2_widget - y1_widget))
            if x2_widget < x1_widget:
                x2_widget = x1_widget - size
            else:
                x2_widget = x1_widget + size
            if y2_widget < y1_widget:
                y2_widget = y1_widget - size
            else:
                y2_widget = y1_widget + size

        stroke_offset = (self.width * scale) / 2
        x = min(x1_widget, x2_widget) + stroke_offset
        y = min(y1_widget, y2_widget) + stroke_offset
        w = abs(x2_widget - x1_widget) - (self.width * scale)
        h = abs(y2_widget - y1_widget) - (self.width * scale)

        if w > 0 and h > 0:
            if self.fill_color:
                cr.set_source_rgba(*self.fill_color)
                cr.rectangle(x, y, w, h)
                cr.fill()
            cr.set_source_rgba(*self.color)
            cr.set_line_width(self.width * scale)
            cr.rectangle(x, y, w, h)
            cr.stroke()

    def get_bounds(self) -> tuple[int, int, int, int]:
        if self.shift:
            dx = abs(self.end[0] - self.start[0])
            dy = abs(self.end[1] - self.start[1])
            size = max(dx, dy)
            if self.end[0] < self.start[0]:
                end_x = self.start[0] - size
            else:
                end_x = self.start[0] + size
            if self.end[1] < self.start[1]:
                end_y = self.start[1] - size
            else:
                end_y = self.start[1] + size
            min_x = min(self.start[0], end_x)
            max_x = max(self.start[0], end_x)
            min_y = min(self.start[1], end_y)
            max_y = max(self.start[1], end_y)
        else:
            min_x = min(self.start[0], self.end[0])
            max_x = max(self.start[0], self.end[0])
            min_y = min(self.start[1], self.end[1])
            max_y = max(self.start[1], self.end[1])

        return (min_x, min_y, max_x, max_y)

    def translate(self, dx: int, dy: int):
        self.start = (self.start[0] + dx, self.start[1] + dy)
        self.end = (self.end[0] + dx, self.end[1] + dy)

class CircleAction(RectAction):
    def draw(self, cr: cairo.Context, image_to_widget_coords: Callable[[int, int], tuple[float, float]], scale: float):
        x1_widget, y1_widget = image_to_widget_coords(*self.start)
        x2_widget, y2_widget = image_to_widget_coords(*self.end)

        if self.shift:
            size = max(abs(x2_widget - x1_widget), abs(y2_widget - y1_widget))
            if x2_widget < x1_widget:
                x2_widget = x1_widget - size
            else:
                x2_widget = x1_widget + size
            if y2_widget < y1_widget:
                y2_widget = y1_widget - size
            else:
                y2_widget = y1_widget + size

        cx, cy = (x1_widget + x2_widget) / 2, (y1_widget + y2_widget) / 2
        stroke_offset = (self.width * scale) / 2
        rx = (abs(x2_widget - x1_widget) - (self.width * scale)) / 2
        ry = (abs(y2_widget - y1_widget) - (self.width * scale)) / 2

        if rx > 0 and ry > 0:
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

class HighlighterAction(StrokeAction):
    def __init__(self, stroke: list[tuple[int, int]], options, shift: bool):
        if shift and len(stroke) >= 2:
            start_point = stroke[0]
            end_point = stroke[-1]
            self.stroke = [start_point, (end_point[0], start_point[1])]
        else:
            self.stroke = stroke
        self.color = options.primary_color
        self.pen_size = options.size

    def draw(self, cr: cairo.Context, image_to_widget_coords: Callable[[int, int], tuple[float, float]], scale: float):
        if len(self.stroke) < 2:
            return
        coords = [image_to_widget_coords(x, y) for x, y in self.stroke]
        cr.set_operator(cairo.Operator.MULTIPLY)
        cr.set_source_rgba(*self.color)
        cr.set_line_width(self.pen_size * scale * 2)
        cr.set_line_cap(cairo.LineCap.BUTT)
        cr.move_to(*coords[0])
        for point in coords[1:]:
            cr.line_to(*point)
        cr.stroke()
        cr.set_operator(cairo.Operator.OVER)
        cr.set_line_cap(cairo.LineCap.ROUND)

    def get_bounds(self) -> tuple[int, int, int, int]:
        if not self.stroke:
            return (0, 0, 0, 0)
        xs, ys = zip(*self.stroke)
        padding = self.pen_size + 3
        return (min(xs) - padding, min(ys) - padding, max(xs) + padding, max(ys) + padding)

class CensorAction(RectAction):
    def __init__(self, start: tuple[int, int], end: tuple[int, int], background_pixbuf: GdkPixbuf.Pixbuf, options):
        super().__init__(start, end, False, options)
        self.block_size = 8
        self.background_pixbuf = background_pixbuf

    def draw(self, cr: cairo.Context, image_to_widget_coords: Callable[[int, int], tuple[float, float]], scale: float):
        x1, y1 = image_to_widget_coords(*self.start)
        x2, y2 = image_to_widget_coords(*self.end)
        x, y = min(x1, x2), min(y1, y2)
        width, height = abs(x2 - x1), abs(y2 - y1)
        if width < 1 or height < 1:
            return
        crop = self._get_image_crop()
        if not crop:
            return
        self._draw_pixelation(cr, crop, x, y, width, height)

    def _draw_pixelation(self, cr: cairo.Context, crop: dict, x: float, y: float, width: float, height: float):
        cr.save()
        cr.rectangle(x, y, width, height)
        cr.clip()

        blocks_x = max(1, int(width / self.block_size))
        blocks_y = max(1, int(height / self.block_size))

        tiny_surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, blocks_x, blocks_y)
        tiny_cr = cairo.Context(tiny_surface)

        tiny_cr.set_operator(cairo.OPERATOR_CLEAR)
        tiny_cr.paint()
        tiny_cr.set_operator(cairo.OPERATOR_OVER)

        tiny_cr.scale(blocks_x / crop['width'], blocks_y / crop['height'])
        tiny_cr.translate(-crop['x'], -crop['y'])
        Gdk.cairo_set_source_pixbuf(tiny_cr, self.background_pixbuf, 0, 0)
        tiny_cr.paint()

        cr.translate(x, y)
        cr.scale(width / blocks_x, height / blocks_y)
        pattern = cairo.SurfacePattern(tiny_surface)
        pattern.set_filter(cairo.FILTER_NEAREST)
        cr.set_source(pattern)
        cr.paint()

        cr.restore()

    def _get_image_crop(self) -> dict | None:
        img_w, img_h = self.background_pixbuf.get_width(), self.background_pixbuf.get_height()
        x1 = int(self.start[0] + img_w / 2)
        y1 = int(self.start[1] + img_h / 2)
        x2 = int(self.end[0] + img_w / 2)
        y2 = int(self.end[1] + img_h / 2)
        x_start, x_end = sorted([max(0, min(x1, img_w)), max(0, min(x2, img_w))])
        y_start, y_end = sorted([max(0, min(y1, img_h)), max(0, min(y2, img_h))])
        width, height = x_end - x_start, y_end - y_start
        return {'x': x_start, 'y': y_start, 'width': width, 'height': height} if width > 0 and height > 0 else None

    def get_bounds(self) -> tuple[int, int, int, int]:
        min_x = min(self.start[0], self.end[0])
        max_x = max(self.start[0], self.end[0])
        min_y = min(self.start[1], self.end[1])
        max_y = max(self.start[1], self.end[1])
        return (min_x, min_y, max_x, max_y)

class NumberStampAction(DrawingAction):
    def __init__(self, position: tuple[int, int], number: int, options):
        super().__init__()
        self.position = position
        self.number = number
        self.radius = options.size * 2
        self.fill_color = options.fill_color
        self.text_color = options.primary_color
        self.outline_color = options.border_color
        self.creation_time = time.time()

    def draw(self, cr: cairo.Context, image_to_widget_coords: Callable[[int, int], tuple[float, float]], scale: float):
        x_widget, y_widget = image_to_widget_coords(*self.position)
        r_widget = self.radius * scale

        cr.set_source_rgba(*self.fill_color)
        cr.arc(x_widget, y_widget, r_widget, 0, 2 * math.pi)
        cr.fill_preserve()

        if self.outline_color.alpha != 0  and self.fill_color.alpha != 0:
            cr.set_source_rgba(*self.outline_color)
            cr.set_line_width(2.0 * scale)
            cr.stroke()
        else:
            cr.new_path()

        cr.select_font_face("Sans", cairo.FontSlant.NORMAL, cairo.FontWeight.BOLD)
        cr.set_font_size(r_widget * 1.2)
        text = str(self.number)

        xbearing, ybearing, width, height, xadvance, yadvance = cr.text_extents(text)
        tx = x_widget - width / 2 - xbearing
        ty = y_widget + height / 2

        cr.move_to(tx, ty)
        cr.text_path(text)

        if self.outline_color and any(c > 0 for c in self.outline_color):
            cr.set_source_rgba(*self.outline_color)
            cr.set_line_width(4 * scale)
            cr.stroke_preserve()

        cr.set_source_rgba(*self.text_color)
        cr.fill()

    def contains_point(self, px_img: int, py_img: int) -> bool:
        x_img, y_img = self.position
        distance_sq = (px_img - x_img)**2 + (py_img - y_img)**2
        return distance_sq <= (self.radius + 5)**2

    def get_bounds(self) -> tuple[int, int, int, int]:
        x_img, y_img = self.position
        outline_padding = 2 if self.outline_color and any(c > 0 for c in self.outline_color) else 0
        total_radius = self.radius + outline_padding + 1
        return (x_img - total_radius, y_img - total_radius, x_img + total_radius, y_img + total_radius)

    def translate(self, dx: int, dy: int):
        self.position = (self.position[0] + dx, self.position[1] + dy)
