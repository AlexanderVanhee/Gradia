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

import io
import os
import math
import time
import cairo

from typing import Optional
from gi.repository import GdkPixbuf
from gradia.graphics.background import Background
from gradia.backend.logger import Logger

logger = Logger()

class ImageProcessor:
    MAX_DIMESION = 1440
    MAX_FILE_SIZE = 1000 * 1024

    def __init__(
        self,
        image_path: Optional[str] = None,
        background: Optional[Background] = None,
        padding: int = 5,
        aspect_ratio: Optional[str | float] = None,
        corner_radius: int = 2,
        shadow_strength: float = 5,
        auto_balance: bool = False
    ) -> None:
        self.background: Optional[Background] = background
        self.padding: int = padding
        self.shadow_strength: float = shadow_strength
        self.aspect_ratio: Optional[str | float] = aspect_ratio
        self.corner_radius: int = corner_radius
        self.auto_balance: bool = auto_balance
        self.source_pixbuf: Optional[GdkPixbuf.Pixbuf] = None
        self._loaded_image_path: Optional[str] = None
        self._balanced_padding: Optional[dict] = None

        if image_path:
            self.set_image_path(image_path)

    def set_image_path(self, image_path: str) -> None:
        start_time = time.perf_counter()

        if image_path != self._loaded_image_path:
            if not os.path.exists(image_path):
                raise FileNotFoundError(f"Input image not found: {image_path}")

            self.source_pixbuf = self._load_and_downscale_image(image_path)
            self._loaded_image_path = image_path

            if self.auto_balance:
                balance_start = time.perf_counter()
                self._balanced_padding = self.get_balanced_padding()
                logger.debug(f"Auto-balance analysis: {(time.perf_counter() - balance_start)*1000:.2f}ms")

        logger.debug(f"Image loading: {(time.perf_counter() - start_time)*1000:.2f}ms")

    def process(self) -> cairo.ImageSurface:
        total_start = time.perf_counter()

        if not self.source_pixbuf:
            raise ValueError("No image loaded to process")

        source_pixbuf = self.source_pixbuf.copy()
        width, height = source_pixbuf.get_width(), source_pixbuf.get_height()

        if self.auto_balance and self._balanced_padding:
            step_start = time.perf_counter()
            source_pixbuf = self._apply_auto_balance(source_pixbuf)
            width, height = source_pixbuf.get_width(), source_pixbuf.get_height()
            logger.debug(f"Auto-balance apply: {(time.perf_counter() - step_start)*1000:.2f}ms")

        if self.padding < 0:
            step_start = time.perf_counter()
            source_pixbuf = self._crop_image(source_pixbuf)
            width, height = source_pixbuf.get_width(), source_pixbuf.get_height()
            logger.debug(f"Image cropping: {(time.perf_counter() - step_start)*1000:.2f}ms")

        step_start = time.perf_counter()
        padded_width, padded_height = self._calculate_final_dimensions(width, height)
        surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, padded_width, padded_height)
        ctx = cairo.Context(surface)
        logger.debug(f"Surface creation: {(time.perf_counter() - step_start)*1000:.2f}ms")

        step_start = time.perf_counter()
        self._create_background(ctx, padded_width, padded_height)
        logger.debug(f"Background rendering: {(time.perf_counter() - step_start)*1000:.2f}ms")

        paste_x, paste_y = self._get_paste_position(width, height, padded_width, padded_height)

        if self.shadow_strength > 0:
            step_start = time.perf_counter()
            self._draw_shadow(ctx, source_pixbuf, paste_x, paste_y)
            logger.debug(f"Shadow rendering: {(time.perf_counter() - step_start)*1000:.2f}ms")

        step_start = time.perf_counter()
        self._draw_image_with_corners(ctx, source_pixbuf, paste_x, paste_y)
        logger.info(f"Image rendering: {(time.perf_counter() - step_start)*1000:.2f}ms")

        step_start = time.perf_counter()
        return surface

    def get_balanced_padding(self, tolerance: int = 5) -> dict[str, int | tuple[int, int, int, int]]:
        if not self.source_pixbuf:
            raise ValueError("No image loaded to analyze padding")

        width = self.source_pixbuf.get_width()
        height = self.source_pixbuf.get_height()
        pixels = self.source_pixbuf.get_pixels()
        n_channels = self.source_pixbuf.get_n_channels()
        rowstride = self.source_pixbuf.get_rowstride()

        def get_pixel(x, y):
            offset = y * rowstride + x * n_channels
            if n_channels == 4:
                return (pixels[offset], pixels[offset+1], pixels[offset+2], pixels[offset+3])
            else:
                return (pixels[offset], pixels[offset+1], pixels[offset+2], 255)

        ref_color = get_pixel(0, 0)

        def is_similar(px):
            return all(abs(px[i] - ref_color[i]) <= tolerance for i in range(len(px)))

        def scan_edge(scan_func):
            return scan_func()

        def count_top():
            for y in range(height):
                for x in range(width):
                    if not is_similar(get_pixel(x, y)):
                        return y
            return height

        def count_bottom():
            for y in range(height-1, -1, -1):
                for x in range(width):
                    if not is_similar(get_pixel(x, y)):
                        return height - 1 - y
            return height

        def count_left():
            for x in range(width):
                for y in range(height):
                    if not is_similar(get_pixel(x, y)):
                        return x
            return width

        def count_right():
            for x in range(width-1, -1, -1):
                for y in range(height):
                    if not is_similar(get_pixel(x, y)):
                        return width - 1 - x
            return width

        top = count_top()
        bottom = count_bottom()
        left = count_left()
        right = count_right()

        max_padding = max(top, bottom, left, right)

        return {
            "top": max_padding - top,
            "bottom": max_padding - bottom,
            "left": max_padding - left,
            "right": max_padding - right,
            "color": ref_color
        }

    def _apply_auto_balance(self, pixbuf: GdkPixbuf.Pixbuf) -> GdkPixbuf.Pixbuf:
        if not self._balanced_padding:
            return pixbuf

        width = pixbuf.get_width()
        height = pixbuf.get_height()
        top = self._balanced_padding["top"]
        bottom = self._balanced_padding["bottom"]
        left = self._balanced_padding["left"]
        right = self._balanced_padding["right"]
        bg_color = self._balanced_padding["color"]

        new_width = width + left + right
        new_height = height + top + bottom

        surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, new_width, new_height)
        ctx = cairo.Context(surface)

        ctx.set_source_rgba(bg_color[0]/255, bg_color[1]/255, bg_color[2]/255, bg_color[3]/255)
        ctx.rectangle(0, 0, new_width, new_height)
        ctx.fill()

        self._draw_pixbuf(ctx, pixbuf, left, top)

        return self._surface_to_pixbuf(surface)

    def _get_percentage(self, value: float) -> float:
        return value * 0.01

    def _load_and_downscale_image(self, image_path: str) -> GdkPixbuf.Pixbuf:
        source_pixbuf = GdkPixbuf.Pixbuf.new_from_file(image_path)

        if self._needs_downscaling(source_pixbuf):
            source_pixbuf = self._downscale_image(source_pixbuf)

        return source_pixbuf

    def _needs_downscaling(self, pixbuf: GdkPixbuf.Pixbuf) -> bool:
        return pixbuf.get_width() > self.MAX_DIMESION or pixbuf.get_height() > self.MAX_DIMESION

    def _downscale_image(self, pixbuf: GdkPixbuf.Pixbuf) -> GdkPixbuf.Pixbuf:
        width = pixbuf.get_width()
        height = pixbuf.get_height()

        if width >= height:
            new_width = self.MAX_DIMESION
            new_height = int(height * (self.MAX_DIMESION / width))
        else:
            new_height = self.MAX_DIMESION
            new_width = int(width * (self.MAX_DIMESION / height))

        return pixbuf.scale_simple(new_width, new_height, GdkPixbuf.InterpType.BILINEAR)

    def _crop_image(self, pixbuf: GdkPixbuf.Pixbuf) -> GdkPixbuf.Pixbuf:
        width = pixbuf.get_width()
        height = pixbuf.get_height()
        smaller_dimension = min(width, height)
        padding_percentage = self._get_percentage(abs(self.padding))
        padding_pixels = int(padding_percentage * smaller_dimension)

        crop_width = max(1, width - (padding_pixels << 1))
        crop_height = max(1, height - (padding_pixels << 1))
        offset_x = (width - crop_width) >> 1
        offset_y = (height - crop_height) >> 1

        return pixbuf.new_subpixbuf(offset_x, offset_y, crop_width, crop_height)

    def _calculate_final_dimensions(self, width: int, height: int) -> tuple[int, int]:
        if self.padding >= 0:
            smaller_dimension = min(width, height)
            padding_percentage = self._get_percentage(self.padding)
            padding_pixels = int(padding_percentage * smaller_dimension)
            width += padding_pixels << 1
            height += padding_pixels << 1

        if self.aspect_ratio:
            width, height = self._adjust_for_aspect_ratio(width, height)

        return width, height

    def _adjust_for_aspect_ratio(self, width: int, height: int) -> tuple[int, int]:
        try:
            ratio = self._parse_aspect_ratio()
            current = width / height

            if current < ratio:
                width = int(height * ratio)
            elif current > ratio:
                height = int(width / ratio)

            return width, height
        except Exception:
            return width, height

    def _parse_aspect_ratio(self) -> float:
        if isinstance(self.aspect_ratio, str) and ":" in self.aspect_ratio:
            w, h = map(float, self.aspect_ratio.split(":"))
            return w / h

        if self.aspect_ratio:
            return float(self.aspect_ratio)

        raise ValueError("aspect_ratio is None and cannot be converted to float")

    def _create_background(self, ctx: cairo.Context, width: int, height: int) -> None:
        if self.background:
            bg_surface = self.background.prepare_cairo_surface(width, height)
            ctx.set_source_surface(bg_surface)
            ctx.paint()
        else:
            ctx.set_operator(cairo.OPERATOR_CLEAR)
            ctx.rectangle(0, 0, width, height)
            ctx.fill()
            ctx.set_operator(cairo.OPERATOR_OVER)

    def _draw_shadow(self, ctx: cairo.Context, pixbuf: GdkPixbuf.Pixbuf, x: int, y: int) -> None:
        shadow_strength = max(0.0, min(self.shadow_strength, 10)) * 0.2
        shadow_alpha = shadow_strength * 0.3
        shadow_offset_x, shadow_offset_y = 10, 10

        ctx.save()
        ctx.translate(x + shadow_offset_x, y + shadow_offset_y)
        ctx.set_source_rgba(0, 0, 0, shadow_alpha)

        if self.corner_radius > 0:
            self._draw_rounded_rectangle(ctx, 0, 0, pixbuf.get_width(), pixbuf.get_height())
            ctx.fill()
        else:
            ctx.rectangle(0, 0, pixbuf.get_width(), pixbuf.get_height())
            ctx.fill()

        ctx.restore()

    def _draw_image_with_corners(self, ctx: cairo.Context, pixbuf: GdkPixbuf.Pixbuf, x: int, y: int) -> None:
        ctx.save()
        ctx.translate(x, y)

        if self.corner_radius > 0:
            self._draw_rounded_rectangle(ctx, 0, 0, pixbuf.get_width(), pixbuf.get_height())
            ctx.clip()

        self._draw_pixbuf(ctx, pixbuf, 0, 0)
        ctx.restore()

    def _draw_rounded_rectangle(self, ctx: cairo.Context, x: float, y: float, width: float, height: float) -> None:
        smaller_dimension = min(width, height)
        radius_percentage = self._get_percentage(self.corner_radius)
        radius = min(radius_percentage * smaller_dimension, min(width, height) * 0.5)

        ctx.new_sub_path()
        ctx.arc(x + width - radius, y + radius, radius, -math.pi*0.5, 0)
        ctx.arc(x + width - radius, y + height - radius, radius, 0, math.pi*0.5)
        ctx.arc(x + radius, y + height - radius, radius, math.pi*0.5, math.pi)
        ctx.arc(x + radius, y + radius, radius, math.pi, math.pi*1.5)
        ctx.close_path()

    def _draw_pixbuf(self, ctx: cairo.Context, pixbuf: GdkPixbuf.Pixbuf, x: float, y: float) -> None:
        from gi.repository import Gdk

        ctx.save()
        ctx.translate(x, y)
        Gdk.cairo_set_source_pixbuf(ctx, pixbuf, 0, 0)
        ctx.paint()
        ctx.restore()

    def _get_paste_position(
        self,
        image_width: int,
        image_height: int,
        background_width: int,
        background_height: int
    ) -> tuple[int, int]:
        if self.padding >= 0:
            x = (background_width - image_width) >> 1
            y = (background_height - image_height) >> 1
            return x, y

        return 0, 0

    def _surface_to_pixbuf(self, surface: cairo.ImageSurface) -> GdkPixbuf.Pixbuf:
        width = surface.get_width()
        height = surface.get_height()
        surface_data = surface.get_data()

        rgba_data = bytearray(width * height * 4)

        for i in range(0, len(surface_data), 4):
            rgba_data[i] = surface_data[i + 2]
            rgba_data[i + 1] = surface_data[i + 1]
            rgba_data[i + 2] = surface_data[i]
            rgba_data[i + 3] = surface_data[i + 3]

        return GdkPixbuf.Pixbuf.new_from_data(
            data=rgba_data,
            colorspace=GdkPixbuf.Colorspace.RGB,
            has_alpha=True,
            bits_per_sample=8,
            width=width,
            height=height,
            rowstride=width * 4
        )
