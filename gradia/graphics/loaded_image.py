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
import math
from PIL import Image
from typing import Optional
from gradia.backend.logger import Logger
from dataclasses import dataclass
from enum import Enum, auto
ImportFormat = tuple[str, str]

logger = Logger()

class ImageOrigin(Enum):
    FileDialog = auto()
    DragDrop = auto()
    Clipboard = auto()
    Screenshot = auto()
    FakeScreenshot = auto()
    CommandLine = auto()
    SourceImage = auto()

@dataclass(frozen=True)
class BalancedPadding:
    top: int
    bottom: int
    left: int
    right: int
    color: tuple[int, int, int, int]

    @property
    def max_padding(self) -> int:
        return max(self.top, self.bottom, self.left, self.right)

    @property
    def total_horizontal(self) -> int:
        return self.left + self.right

    @property
    def total_vertical(self) -> int:
        return self.top + self.bottom

class LoadedImage:
    MAX_PIXEL_AMOUNT = 1024 * 1024

    def __init__(self, image_path: str, origin: ImageOrigin, screenshot_path: str = None):
        self.image_path: str = image_path
        self.origin: ImageOrigin = origin
        self.screenshot_path: str | None = screenshot_path

        self._full_res_img: Optional[Image.Image] = None
        self._preview_img: Optional[Image.Image] = None
        self._balanced_padding: Optional[BalancedPadding] = None
        self._load_error: Optional[str] = None

        self._load_and_analyze_image()

    def _load_and_analyze_image(self) -> None:
        try:
            if not os.path.exists(self.image_path):
                self._load_error = f"Image file not found: {self.image_path}"
                return

            self._full_res_img = Image.open(self.image_path).convert("RGBA")
            self._preview_img = self._create_preview_image(self._full_res_img)
            self._balanced_padding = self._analyze_padding(self._preview_img)

        except Exception as e:
            self._load_error = f"Error loading image: {str(e)}"

    def _create_preview_image(self, image: Image.Image) -> Image.Image:
        if self._needs_downscaling(image):
            return self._downscale_image(image)
        return image.copy()

    def _needs_downscaling(self, image: Image.Image) -> bool:
        width, height = image.size
        return (width * height) > self.MAX_PIXEL_AMOUNT

    def _downscale_image(self, image: Image.Image) -> Image.Image:
        width, height = image.size
        current_pixel_count = width * height
        if current_pixel_count <= self.MAX_PIXEL_AMOUNT:
            return image
        scale_factor = math.sqrt(self.MAX_PIXEL_AMOUNT / current_pixel_count)
        new_width = max(1, int(width * scale_factor))
        new_height = max(1, int(height * scale_factor))
        return image.resize((new_width, new_height), Image.LANCZOS)

    def _analyze_padding(self, image: Image.Image, tolerance: int = 5) -> Optional[BalancedPadding]:
        if not image:
            return None

        img = image.convert("RGBA")
        pixels = img.load()
        width, height = img.size

        ref_color = pixels[0, 0]

        def is_similar(px):
            return all(abs(px[i] - ref_color[i]) <= tolerance for i in range(4))

        def count_top():
            for y in range(height):
                if any(not is_similar(pixels[x, y]) for x in range(width)):
                    return y
            return height

        def count_bottom():
            for y in reversed(range(height)):
                if any(not is_similar(pixels[x, y]) for x in range(width)):
                    return height - 1 - y
            return height

        def count_left():
            for x in range(width):
                if any(not is_similar(pixels[x, y]) for y in range(height)):
                    return x
            return width

        def count_right():
            for x in reversed(range(width)):
                if any(not is_similar(pixels[x, y]) for y in range(height)):
                    return width - 1 - x
            return width

        top = count_top()
        bottom = count_bottom()
        left = count_left()
        right = count_right()

        max_padding = max(top, bottom, left, right)

        balanced_padding = BalancedPadding(
            top=max_padding - top,
            bottom=max_padding - bottom,
            left=max_padding - left,
            right=max_padding - right,
            color=ref_color
        )

        return balanced_padding

    @property
    def full_res_image(self) -> Optional[Image.Image]:
        return self._full_res_img

    @property
    def preview_image(self) -> Optional[Image.Image]:
        return self._preview_img

    @property
    def balanced_padding(self) -> Optional[BalancedPadding]:
        return self._balanced_padding

    @property
    def load_error(self) -> Optional[str]:
        return self._load_error

    @property
    def is_loaded(self) -> bool:
        return self._load_error is None and self._full_res_img is not None

    def get_proper_name(self, with_extension: bool = True) -> str:
        if self.origin == ImageOrigin.Clipboard:
            return _("Clipboard Image")
        elif self.origin in (ImageOrigin.Screenshot, ImageOrigin.FakeScreenshot):
            return _("Screenshot")
        elif self.origin == ImageOrigin.SourceImage:
            return _("Generated Image")
        else:
            filename = os.path.basename(self.image_path)
            if not with_extension:
                filename, _unused = os.path.splitext(filename)
            return filename

    def get_proper_folder(self) -> str:
        if self.origin == ImageOrigin.Clipboard:
            return _("From clipboard")
        elif self.origin == ImageOrigin.Screenshot or self.origin == ImageOrigin.FakeScreenshot:
            return _("Screenshot")
        elif self.origin == ImageOrigin.SourceImage:
            return _("Source")
        else:
            return os.path.basename(os.path.dirname(self.image_path))

    def has_proper_name(self) -> bool:
        return self.origin not in {
            ImageOrigin.Clipboard,
            ImageOrigin.Screenshot,
            ImageOrigin.FakeScreenshot,
            ImageOrigin.SourceImage,
        }

    def has_proper_folder(self) -> bool:
        return self.origin not in {
            ImageOrigin.Clipboard,
            ImageOrigin.Screenshot,
            ImageOrigin.FakeScreenshot,
            ImageOrigin.SourceImage,
        }

    def get_folder_path(self) -> str:
        return os.path.dirname(self.image_path)

    def is_screenshot(self) -> bool:
        return self.origin in (ImageOrigin.Screenshot, ImageOrigin.FakeScreenshot)
