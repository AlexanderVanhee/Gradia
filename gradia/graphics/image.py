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
import tempfile
import threading
from typing import Callable, Optional

from PIL import Image
from gi.repository import Adw, GLib, Gdk, GdkPixbuf, Gio, Gtk

from gradia.constants import rootdir  # pyright: ignore
from gradia.graphics.background import Background


PRESET_IMAGES = [
    "/be/alexandervanhee/gradia/images/preset1.avif",
    "/be/alexandervanhee/gradia/images/preset2.avif",
    "/be/alexandervanhee/gradia/images/preset3.avif",
    "/be/alexandervanhee/gradia/images/preset4.avif",
    "/be/alexandervanhee/gradia/images/preset5.avif",
    "/be/alexandervanhee/gradia/images/preset6.avif",
]


class ImageBackground(Background):
    def __init__(self, file_path: Optional[str] = None) -> None:
        self.file_path: Optional[str] = file_path
        self.image: Optional[Image.Image] = None

        if file_path:
            self.load_image(file_path)
        else:
            if PRESET_IMAGES:
                self.load_image(PRESET_IMAGES[0])

    def load_image(self, path: str) -> None:
        self.file_path = path

        if path.startswith(rootdir):
            resource_data = Gio.resources_lookup_data(path, Gio.ResourceLookupFlags.NONE)
            bytes_data = resource_data.get_data()

            if bytes_data is None:
                raise RuntimeError("Failed to get data from resource lookup")

            byte_stream = io.BytesIO(bytes_data)
            self.image = Image.open(byte_stream).convert("RGBA")
        else:
            self.image = Image.open(path).convert("RGBA")

    def prepare_image(self, width: int, height: int) -> Optional[Image.Image]:
        if not self.image:
            return None

        img = self.image
        img_ratio = img.width / img.height
        target_ratio = width / height

        if img_ratio > target_ratio:
            new_height = height
            new_width = int(new_height * img_ratio)
        else:
            new_width = width
            new_height = int(new_width / img_ratio)

        img_resized = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
        left = (new_width - width) // 2
        top = (new_height - height) // 2
        right = left + width
        bottom = top + height

        img_cropped = img_resized.crop((left, top, right, bottom))
        return img_cropped

    def get_name(self) -> str:
        return f"image-{self.file_path or 'none'}"


@Gtk.Template(resource_path=f"{rootdir}/ui/selectors/image_selector.ui")
class ImageSelector(Adw.PreferencesGroup):
    __gtype_name__ = "GradiaImageSelector"

    preview_picture: Gtk.Picture = Gtk.Template.Child()
    open_image_dialog: Gtk.FileDialog = Gtk.Template.Child()
    image_filter: Gtk.FileFilter = Gtk.Template.Child()
    image_popover: Gtk.Popover = Gtk.Template.Child()
    popover_flowbox: Gtk.FlowBox = Gtk.Template.Child()

    def __init__(
        self,
        image_background: ImageBackground,
        callback: Optional[Callable[[ImageBackground], None]] = None,
        parent_window: Optional[Gtk.Window] = None,
        **kwargs
    ) -> None:
        super().__init__(**kwargs)

        self.image_background = image_background
        self.callback = callback
        self.parent_window = parent_window

        self._setup_file_dialog()
        self._setup_drag_and_drop()
        self._setup_gesture()
        self._setup_preset_popover()

        self._update_preview()

    """
    Setup Methods
    """

    def _setup_file_dialog(self) -> None:
        filter_list = Gio.ListStore.new(Gtk.FileFilter)
        filter_list.append(self.image_filter)
        self.open_image_dialog.set_filters(filter_list)

    def _setup_drag_and_drop(self) -> None:
        drop_target = Gtk.DropTarget.new(Gio.File, Gdk.DragAction.COPY)
        drop_target.connect("drop", self._on_image_drop)
        self.preview_picture.add_controller(drop_target)

    def _setup_gesture(self) -> None:
        gesture = Gtk.GestureClick.new()
        gesture.connect("pressed", self._on_preview_clicked)
        self.preview_picture.add_controller(gesture)

    def _setup_preset_popover(self) -> None:
        """Setup the preset popover with preset images"""

        for path in PRESET_IMAGES:
            button = Gtk.Button(
                focusable=False,
                can_focus=False,
                width_request=80,
                height_request=60,
                css_classes=["image-preset-button", "flat"]
            )

            stack = Gtk.Stack()
            stack.set_transition_type(Gtk.StackTransitionType.CROSSFADE)
            stack.set_transition_duration(200)
            stack.set_hexpand(True)
            stack.set_vexpand(True)

            spinner = Adw.Spinner.new()
            spinner.set_size_request(32, 32)
            spinner.set_hexpand(False)
            spinner.set_vexpand(False)
            spinner.set_halign(Gtk.Align.CENTER)
            spinner.set_valign(Gtk.Align.CENTER)
            stack.add_named(spinner, "loading")

            picture = Gtk.Picture()
            picture.set_content_fit(Gtk.ContentFit.COVER)
            picture.set_halign(Gtk.Align.FILL)
            picture.set_valign(Gtk.Align.FILL)
            picture.set_hexpand(True)
            picture.set_vexpand(True)
            stack.add_named(picture, "image")

            error_icon = Gtk.Image.new_from_icon_name("image-missing-symbolic")
            error_icon.set_pixel_size(24)
            error_icon.set_halign(Gtk.Align.CENTER)
            error_icon.set_valign(Gtk.Align.CENTER)
            stack.add_named(error_icon, "error")

            button.set_child(stack)
            button.connect("clicked", lambda b, p=path: self._on_preset_selected(p))

            self._load_preset_image_async(path, picture, stack)
            self.popover_flowbox.append(button)
            self.image_popover.set_position(Gtk.PositionType.TOP)

    """
    Callbacks
    """

    @Gtk.Template.Callback()
    def _on_select_clicked(self, _button: Gtk.Button, *args) -> None:
        self.open_image_dialog.open(self.parent_window, None, self._on_file_dialog_ready)

    def _on_preset_image_loaded(self, picture: Gtk.Picture, stack: Gtk.Stack, pixbuf: GdkPixbuf.Pixbuf) -> bool:
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
            stack.set_visible_child_name("image")
        except Exception as e:
            print(f"Error setting image pixbuf: {e}")
            stack.set_visible_child_name("error")

        return False

    def _on_preset_image_error(self, stack: Gtk.Stack) -> bool:
        stack.set_visible_child_name("error")
        return False

    def _on_preset_selected(self, path: str) -> None:
        """Handle preset image selection"""
        self._load_image_async(path)
        self.image_popover.popdown()

    def _on_preview_clicked(self, _gesture: Gtk.GestureClick, _n_press: int, _x: float, _y: float) -> None:
        self.open_image_dialog.open(self.parent_window, None, self._on_file_dialog_ready)

    def _on_image_drop(self, _drop_target: Gtk.DropTarget, file: Gio.File, _x: int, _y: int) -> bool:
        file_path = file.get_path()
        if file_path:
            self._load_image_async(file_path)
            return True
        return False

    def _on_file_dialog_ready(self, file_dialog: Gtk.FileDialog, result: Gio.AsyncResult) -> None:
        try:
            file = file_dialog.open_finish(result)
            file_path = file.get_path()
            if file_path:
                self._load_image_async(file_path)
        except GLib.Error as e:
            print(f"FileDialog cancelled or failed: {e.message}")

    def _on_image_loaded(self) -> None:
        self._update_preview()
        if self.callback:
            self.callback(self.image_background)

    """
    Internal Methods
    """

    def _update_preview(self) -> None:
        if self.image_background.image:
            def save_and_update() -> None:
                try:
                    if not self.image_background.image:
                        return

                    image = self.image_background.image.copy()

                    max_width = 400
                    if image.width > max_width:
                        ratio = max_width / image.width
                        new_size = (int(image.width * ratio), int(image.height * ratio))
                        image = image.resize(new_size, Image.LANCZOS)

                    with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as temp_file:
                        temp_path = temp_file.name
                        image.save(temp_path, 'PNG')

                    GLib.idle_add(self._set_preview_image, temp_path)
                except Exception as e:
                    print(f"Error saving preview: {e}")

            thread = threading.Thread(target=save_and_update, daemon=True)
            thread.start()
        else:
            self.preview_picture.set_paintable(None)

    def _set_preview_image(self, temp_path: str) -> bool:
        self.preview_picture.set_filename(temp_path)
        def cleanup_temp_file():
            try:
                os.unlink(temp_path)
            except Exception:
                pass
            return False

        GLib.timeout_add(100, cleanup_temp_file)
        return False

    def _load_image_async(self, file_path: str) -> None:
        def load_in_background():
            try:
                self.image_background.load_image(file_path)
                GLib.idle_add(self._on_image_loaded)
            except Exception as e:
                print(f"Error loading image: {e}")
        thread = threading.Thread(target=load_in_background, daemon=True)
        thread.start()

    def _load_preset_image_async(self, resource_path: str, picture: Gtk.Picture, stack: Gtk.Stack) -> None:
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

                GLib.idle_add(self._on_preset_image_loaded, picture, stack, pixbuf)

            except Exception as e:
                print(f"Error loading preset image {resource_path}: {e}")
                GLib.idle_add(self._on_preset_image_error, stack)

        thread = threading.Thread(target=load_in_background, daemon=True)
        thread.start()
