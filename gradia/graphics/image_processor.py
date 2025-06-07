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

import os
import io
from typing import Optional
from PIL import Image, ImageDraw, ImageChops, ImageFilter, ImageOps
from gi.repository import GdkPixbuf

class ImageProcessor:

    MAX_DIMESION = 1440
    MAX_FILE_SIZE = 1000 * 1024

    
    def __init__(
        self,
        image_path: Optional[str] = None,
        background: Optional[object] = None,
        padding: int = 5,
        aspect_ratio: Optional[str | float] = None,
        corner_radius: int = 2,
        shadow_strength: float = 0.0
    ) -> None:
        self.background = background
        self.padding = padding
        self.shadow_strength = shadow_strength
        self.aspect_ratio = aspect_ratio
        self.corner_radius = corner_radius
        self.source_img: Optional[Image.Image] = None
        self._loaded_image_path: Optional[str] = None

        if image_path:
            self.set_image_path(image_path)

    def _get_percentage(self, value: float) -> float:
        return value / 100.0

    def set_image_path(self, image_path: str) -> None:
        if image_path != self._loaded_image_path:
            if not os.path.exists(image_path):
                raise FileNotFoundError(f"Input image not found: {image_path}")
            self.source_img = self._load_and_downscale_image(image_path)
            self._loaded_image_path = image_path

    def process(self) -> GdkPixbuf.Pixbuf:
        if not self.source_img:
            raise ValueError("No image loaded to process")

        source_img = self.source_img.copy()
        width, height = source_img.size

        if self.padding < 0:
            source_img = self._crop_image(source_img)
            width, height = source_img.size

        if self.corner_radius > 0:
            source_img = self._apply_rounded_corners(source_img)

        padded_width, padded_height = self._calculate_final_dimensions(width, height)
        final_img = self._create_background(padded_width, padded_height)
        paste_position = self._get_paste_position(width, height, padded_width, padded_height)

        shadow_img, shadow_offset = self._create_shadow(source_img, offset=(10, 10), shadow_strength=self.shadow_strength)
        shadow_pos = (paste_position[0] - shadow_offset[0], paste_position[1] - shadow_offset[1])
        final_img = self._alpha_composite_at_position(final_img, shadow_img, shadow_pos)

        final_img = self._alpha_composite_at_position(final_img, source_img, paste_position)

        return self._pil_to_pixbuf(final_img)

    def _alpha_composite_at_position(self, background: Image.Image, foreground: Image.Image, position: tuple[int, int]) -> Image.Image:
        if background.mode != 'RGBA':
            background = background.convert('RGBA')
        if foreground.mode != 'RGBA':
            foreground = foreground.convert('RGBA')
        temp_canvas = Image.new('RGBA', background.size, (0, 0, 0, 0))
        temp_canvas.paste(foreground, position, foreground)
        result = Image.alpha_composite(background, temp_canvas)

        return result

    def _load_and_downscale_image(self, image_path: str) -> Image.Image:
        source_img = Image.open(image_path).convert("RGBA")

        if self._needs_downscaling(source_img):
            source_img = self._downscale_image(source_img)

        quality = 100
        source_img, compressed_size = self._compress_image_with_size(source_img, quality)

        while compressed_size > self.MAX_FILE_SIZE and quality > 10:
            quality -= 10
            source_img, compressed_size = self._compress_image_with_size(source_img, quality)

        return source_img

    def _compress_image_with_size(self, image: Image.Image, quality: int) -> tuple[Image.Image, int]:
        buffer = io.BytesIO()
        image.save(buffer, format='PNG', optimize=True, quality=quality)
        size = buffer.tell()
        buffer.seek(0)
        compressed = Image.open(buffer).convert("RGBA")
        return compressed, size

    def _needs_downscaling(self, image: Image.Image) -> bool:
        width, height = image.size
        return width > self.MAX_DIMESION or height > self.MAX_DIMESION

    def _downscale_image(self, image: Image.Image) -> Image.Image:
        width, height = image.size
        if width >= height:
            new_width = self.MAX_DIMESION
            new_height = int(height * (self.MAX_DIMESION / width))
        else:
            new_height = self.MAX_DIMESION
            new_width = int(width * (self.MAX_DIMESION / height))
        return image.resize((new_width, new_height), Image.Resampling.LANCZOS)

    def _crop_image(self, image: Image.Image) -> Image.Image:
        width, height = image.size
        smaller_dimension = min(width, height)
        padding_percentage = self._get_percentage(abs(self.padding))
        padding_pixels = int(padding_percentage * smaller_dimension)
        crop_w = max(1, width - 2 * padding_pixels)
        crop_h = max(1, height - 2 * padding_pixels)
        offset_x = (width - crop_w) // 2
        offset_y = (height - crop_h) // 2
        return image.crop((offset_x, offset_y, offset_x + crop_w, offset_y + crop_h))

    def _calculate_final_dimensions(self, width: int, height: int) -> tuple[int, int]:
        if self.padding >= 0:
            smaller_dimension = min(width, height)
            padding_percentage = self._get_percentage(self.padding)
            padding_pixels = int(padding_percentage * smaller_dimension)
            width += padding_pixels * 2
            height += padding_pixels * 2

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

    def _apply_rounded_corners(self, image: Image.Image) -> Image.Image:
        width, height = image.size
        smaller_dimension = min(width, height)
        radius_percentage = self._get_percentage(self.corner_radius)
        radius_pixels = int(radius_percentage * smaller_dimension)
        oversample = 4
        large_mask = Image.new("L", (width * oversample, height * oversample), 0)
        draw = ImageDraw.Draw(large_mask)
        draw.rounded_rectangle(
            (0, 0, width * oversample, height * oversample),
            radius=radius_pixels * oversample,
            fill=255
        )
        mask = large_mask.resize((width, height), Image.LANCZOS)
        r, g, b, alpha = image.split()
        new_alpha = ImageChops.multiply(alpha, mask)
        return Image.merge("RGBA", (r, g, b, new_alpha))

    def _create_background(self, width: int, height: int) -> Image.Image:
        if self.background:
            return self.background.prepare_image(width, height)
        return Image.new("RGBA", (width, height), (0, 0, 0, 0))

    def _create_shadow(self, image: Image.Image, offset: tuple[int, int] = (10, 10), shadow_strength: float = 1.0) -> tuple[Image.Image, tuple[int, int]]:
        shadow_strength = max(0.0, min(shadow_strength, 1.0))
        blur_radius = int(10 * shadow_strength)
        shadow_alpha = int(150 * shadow_strength)
        shadow_color = (0, 0, 0, shadow_alpha)

        alpha = image.split()[3]
        shadow = Image.new("RGBA", image.size, shadow_color)
        shadow.putalpha(alpha)

        extra_margin = blur_radius * 5
        expanded_width = image.width + abs(offset[0]) + extra_margin
        expanded_height = image.height + abs(offset[1]) + extra_margin
        shadow_canvas = Image.new("RGBA", (expanded_width, expanded_height), (0, 0, 0, 0))

        shadow_x = extra_margin // 2 + max(offset[0], 0)
        shadow_y = extra_margin // 2 + max(offset[1], 0)
        shadow_canvas.paste(shadow, (shadow_x, shadow_y), shadow)

        shadow_canvas = shadow_canvas.filter(ImageFilter.GaussianBlur(blur_radius))
        return shadow_canvas, (shadow_x, shadow_y)

    def _get_paste_position(self, img_w: int, img_h: int, bg_w: int, bg_h: int) -> tuple[int, int]:
        if self.padding >= 0:
            x = (bg_w - img_w) // 2
            y = (bg_h - img_h) // 2
            return x, y
        return 0, 0

    def _pil_to_pixbuf(self, image: Image.Image) -> GdkPixbuf.Pixbuf:
        if image.mode != 'RGBA':
            image = image.convert('RGBA')

        width, height = image.size
        pixels = image.tobytes()

        pixbuf = GdkPixbuf.Pixbuf.new_from_data(
            pixels,
            GdkPixbuf.Colorspace.RGB,
            True,  # has_alpha=True
            8,
            width,
            height,
            width * 4
        )

        return pixbuf
