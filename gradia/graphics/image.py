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
import shutil
from pathlib import Path
from typing import Callable, Optional

from PIL import Image
from gi.repository import Adw, GLib, Gdk, GdkPixbuf, Gio, Gtk

from gradia.constants import rootdir
from gradia.graphics.background import Background
from gradia.ui.widget.preset_button import ImagePresetButton
from gradia.app_constants import PRESET_IMAGES

class ImageBackground(Background):
    @property
    def SAVED_IMAGE_PATH(self) -> Path:
        cache_dir = GLib.get_user_cache_dir()
        return Path(cache_dir) / 'gradia' / 'last_image.png'

    def __init__(self, file_path: Optional[str] = None) -> None:
        self.file_path: Optional[str] = file_path
        self.image: Optional[Image.Image] = None

        self.SAVED_IMAGE_PATH.parent.mkdir(parents=True, exist_ok=True)

        if file_path:
            self.load_image(file_path)
        else:
            if self.SAVED_IMAGE_PATH.exists():
                self.load_image(str(self.SAVED_IMAGE_PATH))
            elif PRESET_IMAGES:
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

    def save_image_copy_async(self) -> None:
        def save_in_background():
            if self.image:
                self.image.save(self.SAVED_IMAGE_PATH, 'PNG')

        thread = threading.Thread(target=save_in_background, daemon=True)
        thread.start()

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

    preset_button: ImagePresetButton = Gtk.Template.Child()
    preview_picture: Gtk.Picture = Gtk.Template.Child()
    open_image_dialog: Gtk.FileDialog = Gtk.Template.Child()
    image_filter: Gtk.FileFilter = Gtk.Template.Child()

    def __init__(
        self,
        image_background: ImageBackground,
        callback: Optional[Callable[[ImageBackground], None]] = None,
        **kwargs
    ) -> None:
        super().__init__(**kwargs)

        self.image_background = image_background
        self.callback = callback

        self._setup_file_dialog()
        self._setup_drag_and_drop()
        self._setup_gesture()
        self._setup_preset_button()

        self._update_preview()

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

    def _setup_preset_button(self) -> None:
        self.preset_button.set_callback(self._on_preset_selected)

    @Gtk.Template.Callback()
    def _on_select_clicked(self, _button: Gtk.Button, *args) -> None:
        self.open_image_dialog.open(self.get_root(), None, self._on_file_dialog_ready)

    def _on_preset_selected(self, path: str) -> None:
        self._load_image_async(path)

    def _on_preview_clicked(self, _gesture: Gtk.GestureClick, _n_press: int, _x: float, _y: float) -> None:
        self.open_image_dialog.open(self.get_root(), None, self._on_file_dialog_ready)

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
        self.image_background.save_image_copy_async()
        if self.callback:
            self.callback(self.image_background)

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
