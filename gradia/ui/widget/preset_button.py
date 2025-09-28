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

from gi.repository import Adw, Gtk, Gio, GdkPixbuf, GLib
from typing import Callable, Optional, Any
import threading
from gradia.utils.colors import HexColor
from gradia.graphics.gradient import GradientBackground, Gradient
from gradia.app_constants import PREDEFINED_GRADIENTS, PRESET_IMAGES


class BasePresetButton(Gtk.MenuButton):
    def __init__(
        self,
        callback: Optional[Callable[[Any], None]] = None,
        icon_name: str = "view-grid-symbolic",
        **kwargs
    ) -> None:
        super().__init__(**kwargs)
        self.callback = callback
        self.set_icon_name(icon_name)
        self.set_valign(Gtk.Align.CENTER)
        self.add_css_class("flat")
        self._setup_popover()

    def _setup_popover(self) -> None:
        self.popover = Gtk.Popover()
        self.set_popover(self.popover)

        main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        main_box.set_spacing(8)
        main_box.set_margin_top(8)
        main_box.set_margin_bottom(8)
        main_box.set_margin_start(8)
        main_box.set_margin_end(8)

        self.flowbox = Gtk.FlowBox()
        self.flowbox.set_max_children_per_line(3)
        self.flowbox.set_selection_mode(Gtk.SelectionMode.NONE)
        self.flowbox.set_homogeneous(True)
        self.flowbox.set_row_spacing(8)
        self.flowbox.set_column_spacing(8)
        self.flowbox.connect("child-activated", self._on_item_selected)

        self._create_preset_buttons()

        main_box.append(self.flowbox)
        self.popover.set_child(main_box)

    def _create_preset_buttons(self) -> None:
        raise NotImplementedError("Subclasses must implement _create_preset_buttons")

    def _on_item_selected(self, flowbox, item):
        raise NotImplementedError("Subclasses must implement _on_item_selected")

    def _create_bin(self, width: int = 60, height: int = 40, css_class: str = "preset") -> Adw.Bin:
        bin_widget = Adw.Bin()
        bin_widget.set_size_request(width, height)
        bin_widget.add_css_class(css_class)
        bin_widget.add_css_class("flat")
        return bin_widget

    def set_callback(self, callback: Callable[[Any], None]) -> None:
        self.callback = callback

    def _clear_flowbox(self) -> None:
        child = self.flowbox.get_first_child()
        while child:
            next_child = child.get_next_sibling()
            self.flowbox.remove(child)
            child = next_child


class GradientPresetButton(BasePresetButton):
    __gtype_name__ = "GradiaGradientPresetButton"

    def _create_preset_buttons(self) -> None:
        for i, gradient in enumerate(PREDEFINED_GRADIENTS[:6]):
            gradient_name = f"gradient-preset-{i}"
            bin_widget = self._create_bin(css_class="preset-button")
            bin_widget.set_name(gradient_name)
            self._apply_gradient_to_bin(bin_widget, gradient)
            self.flowbox.append(bin_widget)

    def _apply_gradient_to_bin(self, bin_widget: Adw.Bin, gradient: Gradient) -> None:
        css = f"""
            .preset-button {{
                background-image: {gradient.to_css()};
            }}
        """
        css_provider = Gtk.CssProvider()
        css_provider.load_from_string(css)
        bin_widget.get_style_context().add_provider(
            css_provider,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION + 3
        )

    def _on_item_selected(self, flowbox, item):
        index = item.get_index()
        if index < len(PREDEFINED_GRADIENTS[:6]):
            gradient = PREDEFINED_GRADIENTS[index]
            self.popover.popdown()
            if self.callback:
                self.callback(gradient)

    def set_gradient_presets(self, gradients: list[Gradient]) -> None:
        self._clear_flowbox()

        for i, gradient in enumerate(gradients[:6]):
            gradient_name = f"gradient-preset-{i}"
            bin_widget = self._create_bin(css_class="gradient-preset")
            bin_widget.set_name(gradient_name)
            self._apply_gradient_to_bin(bin_widget, gradient)
            self.flowbox.append(bin_widget)


class ImagePresetButton(BasePresetButton):
    __gtype_name__ = "GradiaImagePresetButton"

    def __init__(
        self,
        callback: Optional[Callable[[str], None]] = None,
        **kwargs
    ) -> None:
        super().__init__(callback=callback, **kwargs)

    def _create_preset_buttons(self) -> None:
        for path in PRESET_IMAGES:
            bin_widget = self._create_bin(width=80, height=60, css_class="preset-button")

            picture = Gtk.Picture()
            picture.set_content_fit(Gtk.ContentFit.COVER)
            picture.set_halign(Gtk.Align.FILL)
            picture.set_valign(Gtk.Align.FILL)
            picture.set_hexpand(True)
            picture.set_vexpand(True)

            bin_widget.set_child(picture)
            self._load_preset_image_async(path, picture)
            self.flowbox.append(bin_widget)

    def _on_item_selected(self, flowbox, item):
        index = item.get_index()
        if index < len(PRESET_IMAGES):
            path = PRESET_IMAGES[index]
            self.popover.popdown()
            if self.callback:
                self.callback(path)

    def _load_preset_image_async(self, resource_path: str, picture: Gtk.Picture) -> None:
        def load_in_background():
            try:
                resource = Gio.resources_lookup_data(resource_path, Gio.ResourceLookupFlags.NONE)
                data = resource.get_data()

                if data is None:
                    raise RuntimeError("Failed to get data from resource lookup")

                loader = GdkPixbuf.PixbufLoader.new()
                loader.write(data)
                loader.close()

                pixbuf = loader.get_pixbuf()

                if pixbuf is None:
                    raise RuntimeError("Failed to load pixbuf from resource data")

                GLib.idle_add(self._on_preset_image_loaded, picture, pixbuf)

            except Exception as e:
                print(f"Error loading preset image {resource_path}: {e}")
                GLib.idle_add(self._on_preset_image_error, picture)

        thread = threading.Thread(target=load_in_background, daemon=True)
        thread.start()

    def _on_preset_image_loaded(self, picture: Gtk.Picture, pixbuf: GdkPixbuf.Pixbuf) -> bool:
        try:
            max_width, max_height = 80, 60

            width = pixbuf.get_width()
            height = pixbuf.get_height()

            scale_width = max_width
            scale_height = int(height * max_width / width)

            if scale_height > max_height:
                scale_height = max_height
                scale_width = int(width * max_height / height)

            if width > max_width or height > max_height:
                scaled_pixbuf = pixbuf.scale_simple(scale_width, scale_height, GdkPixbuf.InterpType.BILINEAR)
            else:
                scaled_pixbuf = pixbuf

            picture.set_pixbuf(scaled_pixbuf)
        except Exception as e:
            print(f"Error setting image pixbuf: {e}")
            self._on_preset_image_error(picture)

        return False

    def _on_preset_image_error(self, picture: Gtk.Picture) -> bool:
        error_icon = Gtk.Image.new_from_icon_name("image-missing-symbolic")
        error_icon.set_pixel_size(24)
        error_icon.set_halign(Gtk.Align.CENTER)
        error_icon.set_valign(Gtk.Align.CENTER)
        picture.get_parent().set_child(error_icon)
        return False
