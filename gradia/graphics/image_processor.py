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
from typing import Optional

from PIL import Image, ImageChops, ImageDraw, ImageFilter
from gi.repository import GdkPixbuf

from gradia.graphics.background import Background
from gradia.graphics.loaded_image import LoadedImage, BalancedPadding


class ImageProcessor:
    def __init__(
        self,
        image: Optional[LoadedImage] = None,
        background: Optional[Background] = None,
        padding: int = 0,
        aspect_ratio: Optional[str | float] = None,
        corner_radius: int = 0,
        shadow_strength: float = 0,
        auto_balance: bool = False,
        rotation: int = 0
    ) -> None:
        self.background: Optional[Background] = background
        self.padding: int = padding
        self.shadow_strength: float = shadow_strength
        self.aspect_ratio: Optional[str | float] = aspect_ratio
        self.corner_radius: int = corner_radius
        self.auto_balance: bool = auto_balance
        self.rotation: int = rotation
        self._loaded_image: Optional[LoadedImage] = None

        if image:
            self.set_image(image)

    def set_image(self, image: LoadedImage) -> None:
        if not image.is_loaded:
            raise ValueError(f"Failed to load image: {image.load_error}")
        self._loaded_image = image

    def process_to_pillow(self) -> Image:
        if not self._loaded_image or not self._loaded_image.preview_image:
            raise ValueError("No image loaded to process")
        source_img = self._loaded_image.preview_image.copy()

        if self.rotation != 0:
            source_img = self._apply_rotation(source_img)
        width, height = source_img.size

        if self.auto_balance and self._loaded_image.balanced_padding:
            source_img = self._apply_auto_balance(source_img, self._loaded_image.balanced_padding)
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
        shadow_position = (paste_position[0] - shadow_offset[0], paste_position[1] - shadow_offset[1])

        final_img = self._alpha_composite_at_position(final_img, shadow_img, shadow_position)
        final_img = self._alpha_composite_at_position(final_img, source_img, paste_position)

        return final_img

    def process(self) -> tuple[GdkPixbuf.Pixbuf, int, int]:
        final_img = self.process_to_pillow()
        final_pixbuf = self._pil_to_pixbuf(final_img)
        full_width, full_height = self.get_full_resolution_dimensions(final_pixbuf)
        return final_pixbuf, full_width, full_height

    def process_full_resolution(self) -> GdkPixbuf.Pixbuf:
        if not self._loaded_image or not self._loaded_image.full_res_image:
            raise ValueError("No full resolution image loaded to process")

        source_img = self._loaded_image.full_res_image.copy()

        if self.rotation != 0:
            source_img = self._apply_rotation(source_img)

        width, height = source_img.size

        if self.auto_balance and self._loaded_image.balanced_padding:
            source_img = self._apply_auto_balance_full_res(source_img, self._loaded_image.balanced_padding)
            width, height = source_img.size

        if self.padding < 0:
            source_img = self._crop_image(source_img)
            width, height = source_img.size

        if self.corner_radius > 0:
            source_img = self._apply_rounded_corners(source_img)

        padded_width, padded_height = self._calculate_final_dimensions(width, height)
        final_img = self._create_background_full_res(padded_width, padded_height)
        paste_position = self._get_paste_position(width, height, padded_width, padded_height)

        shadow_img, shadow_offset = self._create_shadow_full_res(source_img, offset=(10, 10), shadow_strength=self.shadow_strength)
        shadow_position = (paste_position[0] - shadow_offset[0], paste_position[1] - shadow_offset[1])
        final_img = self._alpha_composite_at_position(final_img, shadow_img, shadow_position)

        final_img = self._alpha_composite_at_position(final_img, source_img, paste_position)

        return self._pil_to_pixbuf(final_img)

    def _apply_rotation(self, image: Image.Image) -> Image.Image:
        if self.rotation == 0:
            return image
        elif self.rotation == 90:
            return image.transpose(Image.ROTATE_90)
        elif self.rotation == 180:
            return image.transpose(Image.ROTATE_180)
        elif self.rotation == 270:
            return image.transpose(Image.ROTATE_270)
        else:
            return image

    def _apply_auto_balance(self, image: Image.Image, balanced_padding: BalancedPadding) -> Image.Image:
        width, height = image.size

        new_width = width + balanced_padding.left + balanced_padding.right
        new_height = height + balanced_padding.top + balanced_padding.bottom

        balanced_image = Image.new("RGBA", (new_width, new_height), balanced_padding.color)

        paste_x = balanced_padding.left
        paste_y = balanced_padding.top
        balanced_image.paste(image, (paste_x, paste_y), image)

        return balanced_image

    def _apply_auto_balance_full_res(self, image: Image.Image, balanced_padding: BalancedPadding) -> Image.Image:
        if not self._loaded_image or not self._loaded_image.preview_image or not self._loaded_image.full_res_image:
            return image

        scale_x = self._loaded_image.full_res_image.width / self._loaded_image.preview_image.width
        scale_y = self._loaded_image.full_res_image.height / self._loaded_image.preview_image.height
        scale = max(scale_x, scale_y)

        width, height = image.size
        top = int(balanced_padding.top * scale)
        bottom = int(balanced_padding.bottom * scale)
        left = int(balanced_padding.left * scale)
        right = int(balanced_padding.right * scale)

        new_width = width + left + right
        new_height = height + top + bottom

        balanced_image = Image.new("RGBA", (new_width, new_height), balanced_padding.color)

        paste_x = left
        paste_y = top
        balanced_image.paste(image, (paste_x, paste_y), image)

        return balanced_image

    def _create_background_full_res(self, width: int, height: int) -> Image.Image:
        if self.background:
            return self.background.prepare_image(width, height)
        return Image.new("RGBA", (width, height), (0, 0, 0, 0))

    def _create_shadow_full_res(
        self,
        image: Image.Image,
        offset: tuple[int, int] = (10, 10),
        shadow_strength: float = 1.0
    ) -> tuple[Image.Image, tuple[int, int]]:
        if not self._loaded_image or not self._loaded_image.preview_image or not self._loaded_image.full_res_image:
            scale = 1.0
        else:
            scale_x = self._loaded_image.full_res_image.width / self._loaded_image.preview_image.width
            scale_y = self._loaded_image.full_res_image.height / self._loaded_image.preview_image.height
            scale = max(scale_x, scale_y)

        shadow_strength = max(0.0, min(shadow_strength, 10)) / 5
        blur_radius = int(10 * shadow_strength * scale)
        shadow_alpha = int(150 * shadow_strength)
        shadow_color = (0, 0, 0, shadow_alpha)
        scaled_offset = (int(offset[0] * scale), int(offset[1] * scale))

        alpha = image.split()[3]
        shadow = Image.new("RGBA", image.size, shadow_color)
        shadow.putalpha(alpha)

        extra_margin = blur_radius * 5
        expanded_width = image.width + abs(scaled_offset[0]) + extra_margin
        expanded_height = image.height + abs(scaled_offset[1]) + extra_margin
        shadow_canvas = Image.new("RGBA", (expanded_width, expanded_height), (0, 0, 0, 0))

        shadow_x = extra_margin // 2 + max(scaled_offset[0], 0)
        shadow_y = extra_margin // 2 + max(scaled_offset[1], 0)
        shadow_canvas.paste(shadow, (shadow_x, shadow_y), shadow)

        shadow_canvas = shadow_canvas.filter(ImageFilter.GaussianBlur(blur_radius))

        return shadow_canvas, (shadow_x, shadow_y)

    def _get_percentage(self, value: float) -> float:
        return value / 100.0

    def _alpha_composite_at_position(
        self,
        background: Image.Image,
        foreground: Image.Image,
        position: tuple[int, int]
    ) -> Image.Image:
        if background.mode != 'RGBA':
            background = background.convert('RGBA')

        if foreground.mode != 'RGBA':
            foreground = foreground.convert('RGBA')

        temp_canvas = Image.new('RGBA', background.size, (0, 0, 0, 0))
        temp_canvas.paste(foreground, position, foreground)
        result = Image.alpha_composite(background, temp_canvas)

        return result

    def _crop_image(self, image: Image.Image) -> Image.Image:
        width, height = image.size
        smaller_dimension = min(width, height)
        padding_percentage = self._get_percentage(abs(self.padding))
        padding_pixels = int(padding_percentage * smaller_dimension)

        crop_width = max(1, width - 2 * padding_pixels)
        crop_height = max(1, height - 2 * padding_pixels)
        offset_x = (width - crop_width) // 2
        offset_y = (height - crop_height) // 2

        return image.crop(
            (offset_x, offset_y, offset_x + crop_width, offset_y + crop_height)
        )

    def get_full_resolution_dimensions(self, processed_pixbuf) -> tuple[int, int]:
        if not self._loaded_image or not self._loaded_image.full_res_image or not self._loaded_image.preview_image:
            raise ValueError("No images loaded")

        scale_x = self._loaded_image.full_res_image.width / self._loaded_image.preview_image.width
        scale_y = self._loaded_image.full_res_image.height / self._loaded_image.preview_image.height
        scale = max(scale_x, scale_y)

        downscaled_width = processed_pixbuf.get_width()
        downscaled_height = processed_pixbuf.get_height()

        full_width = int(downscaled_width * scale)
        full_height = int(downscaled_height * scale)

        return full_width, full_height

    def _calculate_final_dimensions(self, width: int, height: int) -> tuple[int, int]:
       width = max(1, width)
       height = max(1, height)

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

    def _create_shadow(
        self,
        image: Image.Image,
        offset: tuple[int, int] = (10, 10),
        shadow_strength: float = 1.0
    ) -> tuple[Image.Image, tuple[int, int]]:
        shadow_strength = max(0.0, min(shadow_strength, 10)) / 5
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

    def _get_paste_position(
        self,
        image_width: int,
        image_height: int,
        background_width: int,
        background_height: int
    ) -> tuple[int, int]:
        if self.padding >= 0:
            x = (background_width - image_width) // 2
            y = (background_height - image_height) // 2
            return x, y
        return 0, 0

    def _pil_to_pixbuf(self, image: Image.Image) -> GdkPixbuf.Pixbuf:
        if image.mode != 'RGBA':
            image = image.convert('RGBA')

        width, height = image.size
        pixels = image.tobytes()

        pixbuf = GdkPixbuf.Pixbuf.new_from_data(
            data=pixels,
            colorspace=GdkPixbuf.Colorspace.RGB,
            has_alpha=True,
            bits_per_sample=8,
            width=width,
            height=height,
            rowstride=width * 4,
            destroy_fn=None
        )

        return pixbuf
