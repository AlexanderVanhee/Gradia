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
import math
from typing import Callable, Optional
from pathlib import Path
from gi.repository import Adw, Gtk, GLib, Gdk, GdkPixbuf, Graphene, Gsk, GObject

from gradia.app_constants import PREDEFINED_GRADIENTS
from gradia.backend.settings import Settings
from gradia.constants import rootdir  # pyright: ignore
from gradia.graphics.gradient import Gradient


class RecentFile:
    def __init__(self, path: Path) -> None:
        self.path = path
        self.folder = str(path.parent)
        self.name = str(path.parent)


class RecentImageGetter:
    MAX_RESULTS = 6
    FALLBACK_PICTURES_PATH = Path.home() / "Pictures"

    def __init__(self) -> None:
        pass

    def get_recent_screenshot_files(self) -> list[RecentFile]:
        screenshots_dir = self._get_screenshots_directory()
        if not screenshots_dir or not screenshots_dir.exists():
            print(f"Screenshots directory does not exist: {screenshots_dir}")
            return None

        image_extensions = {'.png', '.jpg', '.jpeg', '.webp', '.avif'}
        all_files = [f for f in screenshots_dir.iterdir()
                     if f.is_file() and f.suffix.lower() in image_extensions]

        sorted_files = sorted(all_files, key=lambda f: f.stat().st_mtime, reverse=True)
        top_files = sorted_files[:self.MAX_RESULTS]

        return [RecentFile(f) for f in top_files]

    def _get_screenshots_directory(self) -> Path | None:
        xdg_pictures = GLib.get_user_special_dir(GLib.USER_DIRECTORY_PICTURES)
        screenshot_folder = Settings().screenshot_folder

        if screenshot_folder:
            path = Path(screenshot_folder)
            return path if path.exists() else None


        if xdg_pictures:
            path = Path(xdg_pictures) / 'Screenshots'
            return path if path.exists() else None
        return None

class RoundedImage(Gtk.Widget):
    def __init__(self, path: str, radius: float = 4.0, padding: int = 8,
                 compact: bool = False, shadow_offset: tuple = (5, 5),
                 shadow_blur: float = 8, shadow_opacity: float = 0.3):
        super().__init__()
        self.radius = radius
        self.texture = None
        self.shadow_texture = None
        self.padding = padding
        self.shadow_offset = shadow_offset
        self.shadow_blur = shadow_blur
        self.shadow_opacity = shadow_opacity
        self._image_rect = Graphene.Rect()
        self._shadow_rect = Graphene.Rect()

        width = 155 if compact else 260
        height = 120 if compact else 160

        try:
            pixbuf = GdkPixbuf.Pixbuf.new_from_file_at_size(path, width, height)
            self.texture = Gdk.Texture.new_for_pixbuf(pixbuf)

            if self.shadow_blur > 0 and self.shadow_opacity > 0:
                self.shadow_texture = self._create_shadow_texture(pixbuf)
        except Exception as e:
            print(f"Failed to load image {path}: {e}")

    def _create_shadow_texture(self, pixbuf: GdkPixbuf.Pixbuf) -> Gdk.Texture:
        width = pixbuf.get_width()
        height = pixbuf.get_height()

        blur_padding = int(self.shadow_blur * 3)
        shadow_width = width + blur_padding * 2
        shadow_height = height + blur_padding * 2

        surface = cairo.ImageSurface(cairo.FORMAT_A8, shadow_width, shadow_height)
        cr = cairo.Context(surface)

        cr.set_source_rgba(0, 0, 0, 0)
        cr.paint()
        cr.save()
        cr.translate(blur_padding, blur_padding)

        temp_surface = cairo.ImageSurface(cairo.FORMAT_A8, width, height)
        temp_cr = cairo.Context(temp_surface)
        Gdk.cairo_set_source_pixbuf(temp_cr, pixbuf, 0, 0)
        temp_cr.paint()

        cr.set_source_rgba(0, 0, 0, self.shadow_opacity)
        cr.mask_surface(temp_surface, 0, 0)
        cr.restore()

        if self.shadow_blur > 0:
            surface = self._apply_separable_blur(surface, self.shadow_blur)

        shadow_pixbuf = Gdk.pixbuf_get_from_surface(surface, 0, 0,
                                                      shadow_width, shadow_height)
        return Gdk.Texture.new_for_pixbuf(shadow_pixbuf)

    def _apply_separable_blur(self, surface: cairo.ImageSurface, radius: float) -> cairo.ImageSurface:
        width = surface.get_width()
        height = surface.get_height()

        kernel_size = int(radius * 2) + 1
        kernel = self._gaussian_kernel(kernel_size, radius / 3.0)

        temp_surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, width, height)
        temp_cr = cairo.Context(temp_surface)

        for i, weight in enumerate(kernel):
            offset = i - kernel_size // 2
            temp_cr.save()
            temp_cr.translate(offset, 0)
            temp_cr.set_source_surface(surface, 0, 0)
            temp_cr.paint_with_alpha(weight)
            temp_cr.restore()

        final_surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, width, height)
        final_cr = cairo.Context(final_surface)

        for i, weight in enumerate(kernel):
            offset = i - kernel_size // 2
            final_cr.save()
            final_cr.translate(0, offset)
            final_cr.set_source_surface(temp_surface, 0, 0)
            final_cr.paint_with_alpha(weight)
            final_cr.restore()

        return final_surface

    def _gaussian_kernel(self, size: int, sigma: float) -> list:
        kernel = []
        center = size // 2
        total = 0

        for i in range(size):
            x = i - center
            value = math.exp(-(x * x) / (2 * sigma * sigma))
            kernel.append(value)
            total += value

        return [k / total for k in kernel]

    def do_snapshot(self, snapshot: Gtk.Snapshot) -> None:
        if not self.texture:
            return

        widget_width = self.get_width()
        widget_height = self.get_height()
        texture_width = self.texture.get_width()
        texture_height = self.texture.get_height()

        available_width = widget_width - (self.padding * 2)
        available_height = widget_height - (self.padding * 2)

        scale_x = available_width / texture_width
        scale_y = available_height / texture_height
        scale = min(scale_x, scale_y)

        scaled_width = texture_width * scale
        scaled_height = texture_height * scale

        x_offset = self.padding + (available_width - scaled_width) / 2
        y_offset = self.padding + (available_height - scaled_height) / 2

        if self.shadow_texture:
            shadow_width = self.shadow_texture.get_width()
            shadow_height = self.shadow_texture.get_height()
            blur_padding = int(self.shadow_blur * 3)
            shadow_scale_width = scaled_width + blur_padding * 2 * scale
            shadow_scale_height = scaled_height + blur_padding * 2 * scale

            shadow_x = x_offset - blur_padding * scale + self.shadow_offset[0]
            shadow_y = y_offset - blur_padding * scale + self.shadow_offset[1]

            self._shadow_rect.init(shadow_x, shadow_y, shadow_scale_width, shadow_scale_height)

            if self.radius > 0:
                rounded_shadow_rect = Gsk.RoundedRect()
                rounded_shadow_rect.init_from_rect(self._shadow_rect, self.radius)
                snapshot.push_rounded_clip(rounded_shadow_rect)

            snapshot.append_texture(self.shadow_texture, self._shadow_rect)

            if self.radius > 0:
                snapshot.pop()

        self._image_rect.init(x_offset, y_offset, scaled_width, scaled_height)

        if self.radius > 0:
            rounded_rect = Gsk.RoundedRect()
            rounded_rect.init_from_rect(self._image_rect, self.radius)
            snapshot.push_rounded_clip(rounded_rect)

        snapshot.append_texture(self.texture, self._image_rect)

        if self.radius > 0:
            snapshot.pop()

@Gtk.Template(resource_path=f"{rootdir}/ui/recent_picker.ui")
class RecentPicker(Adw.Bin):
    __gtype_name__ = "GradiaRecentPicker"

    FRAME_SPACING = 5
    IMAGE_WIDTH = 260
    IMAGE_HEIGHT = 160
    COMPACT_IMAGE_WIDTH = 150
    COMPACT_IMAGE_HEIGHT = 120

    item_grid: Gtk.FlowBox = Gtk.Template.Child()

    recent_overlay: Gtk.Overlay= Gtk.Template.Child()
    error_overlay: Adw.StatusPage = Gtk.Template.Child()

    compact = GObject.Property(type=bool, default=False)

    def __init__(self, callback: Optional[Callable] = None, **kwargs) -> None:
        super().__init__(**kwargs)

        self.image_getter = RecentImageGetter()
        self.callback = callback

        self.image_bins: list[Gtk.Button] = []
        self.recent_files: list[RecentFile] = []

        self.gradient_colors = PREDEFINED_GRADIENTS
        self.original_gradient_indexes = list(range(len(self.gradient_colors)))
        combined = list(zip(self.gradient_colors, self.original_gradient_indexes))
        self.gradient_colors, self.original_gradient_indexes = zip(*combined)
        self.gradient_colors = list(self.gradient_colors)
        self.original_gradient_indexes = list(self.original_gradient_indexes)

        self.connect("notify::compact", self._on_compact_changed)
        self._setup_cards()
        self._load_images()

    def _on_compact_changed(self, *args) -> None:
        self._setup_cards()
        self._load_images()

    def _setup_cards(self) -> None:
        for child in list(self.item_grid):
            self.item_grid.remove(child)

        self.image_bins.clear()

        width = self.COMPACT_IMAGE_WIDTH if self.compact else self.IMAGE_WIDTH
        height = self.COMPACT_IMAGE_HEIGHT if self.compact else self.IMAGE_HEIGHT

        for index in range(6):
            image_bin = Adw.Bin()
            image_bin.set_size_request(width, height)
            image_bin.add_css_class("card")
            self._apply_gradient_to_button(image_bin, index)
            placeholder = Gtk.Box()
            image_bin.set_child(placeholder)
            self.image_bins.append(image_bin)
            self.item_grid.append(image_bin)

        self.item_grid.connect(
            "child-activated",
            lambda flowbox, flowbox_child: self._on_image_clicked(
                self.image_bins.index(flowbox_child.get_child())
            )
        )

    def _on_image_clicked(self, index: int, *args) -> None:
        if index < len(self.recent_files):
            file_path = self.recent_files[index].path
            original_gradient_index = self.original_gradient_indexes[index % len(self.original_gradient_indexes)]

            if self.callback:
                self.callback(str(file_path), original_gradient_index)

    def refresh(self) -> None:
        self._load_images()

    def _apply_gradient_to_button(self, button: Gtk.Button, index: int) -> None:
        gradient_name = f"gradient-button-{index}"
        button.set_name(gradient_name)
        button.add_css_class("recent-button")

        color_index = index % len(self.gradient_colors)
        gradient = self.gradient_colors[color_index]

        css = f"""
            *#{gradient_name} {{
                background-image: {gradient.to_css()};
            }}
        """

        css_provider = Gtk.CssProvider()
        css_provider.load_from_string(css)
        button.get_style_context().add_provider(
            css_provider,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
        )

    def _load_images(self) -> None:
        recent_files = self.image_getter.get_recent_screenshot_files()
        self._update_display(recent_files)

    def _update_display(self, recent_files: list[RecentFile]) -> None:
        self.recent_files = recent_files

        if self.recent_files is None:
            self.error_overlay.set_visible(True)
            self.item_grid.set_opacity(0.25)
            recent_files = []
        else:
            self.error_overlay.set_visible(False)
            self.item_grid.set_opacity(1)

        radius = 2.0 if self.compact else 4.0
        padding = 4 if self.compact else 8

        for i in range(6):
            if i < len(recent_files):
                file = recent_files[i]

                try:
                    rounded = RoundedImage(str(file.path), radius=radius, padding=padding, compact=self.compact)
                    self.image_bins[i].set_child(rounded)
                    self.image_bins[i].set_sensitive(True)
                except Exception as e:
                    icon = Gtk.Image.new_from_icon_name("image-missing-symbolic")
                    self.image_bins[i].set_child(icon)
                    self.image_bins[i].set_sensitive(False)
                    print(f"Error loading image {file.path}: {e}")
            else:
                icon = Gtk.Image.new_from_icon_name("image-missing-symbolic")
                self.image_bins[i].set_child(icon)
                self.image_bins[i].set_sensitive(False)
