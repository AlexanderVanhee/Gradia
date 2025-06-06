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

from typing import Optional, Callable
from gi.repository import Gtk, Gdk, Adw, GdkPixbuf, GLib
from PIL import Image
from gradia.graphics.background import Background
import threading
import tempfile
import os

class ImageBackground(Background):
    def __init__(self, file_path: Optional[str] = None) -> None:
        self.file_path: Optional[str] = file_path
        self.image: Optional[Image.Image] = None

        if file_path:
            self.load_image(file_path)

    def load_image(self, path: str) -> None:
        self.file_path = path
        try:
            self.image = Image.open(path).convert("RGBA")
        except Exception as e:
            self.image = None
            print(f"Error loading image: {e}")

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


class ImageSelector:
    def __init__(
        self,
        image_background: ImageBackground,
        callback: Optional[Callable[[ImageBackground], None]] = None,
        parent_window: Optional[Gtk.Window] = None
    ) -> None:
        self.image_background = image_background
        self.callback = callback
        self.preview_picture = Gtk.Picture()
        self.widget = self._build()
        self._update_preview()
        self.parent_window = parent_window

    def _build(self) -> Adw.PreferencesGroup:
        group = Adw.PreferencesGroup(title=_("Image Background"))
        button_row = Adw.ActionRow()
        file_button = Gtk.Button(label=_("Select Image"), margin_start=8, margin_end=8, margin_top=8, margin_bottom=8)
        file_button.connect("clicked", self._on_select_clicked)
        button_row.set_child(file_button)
        button_row.set_activatable(False)
        group.add(button_row)

        preview_row = Adw.ActionRow()
        preview_row.set_activatable(False)
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, hexpand=True, halign=Gtk.Align.CENTER)
        self.preview_picture.set_size_request(250, 88)
        self.preview_picture.set_content_fit(Gtk.ContentFit.COVER)
        frame = Gtk.Frame(margin_top=8, margin_bottom=8)
        frame.set_child(self.preview_picture)
        box.append(frame)
        preview_row.set_child(box)
        group.add(preview_row)

        return group

    def _on_select_clicked(self, _button: Gtk.Button) -> None:
        dialog = Gtk.FileChooserDialog(
            title=_("Select Background Image"),
            action=Gtk.FileChooserAction.OPEN,
            transient_for=self.parent_window,
            modal=True
        )
        dialog.add_buttons(
            "_Cancel", Gtk.ResponseType.CANCEL,
            "_Open", Gtk.ResponseType.ACCEPT
        )

        filter_image = Gtk.FileFilter()
        filter_image.set_name("Image files")
        filter_image.add_mime_type("image/png")
        filter_image.add_mime_type("image/jpeg")
        filter_image.add_mime_type("image/webp")
        filter_image.add_mime_type("image/avif")
        dialog.add_filter(filter_image)

        dialog.connect("response", self._on_file_dialog_response)
        dialog.show()

    def _on_file_dialog_response(self, dialog: Gtk.FileChooserDialog, response: int) -> None:
        if response == Gtk.ResponseType.ACCEPT:
            file_path = dialog.get_file().get_path()
            if file_path:
                self._load_image_async(file_path)
        dialog.destroy()

    def _load_image_async(self, file_path: str) -> None:
        def load_in_background():
            try:
                self.image_background.load_image(file_path)
                GLib.idle_add(self._on_image_loaded)

            except Exception as e:
                print(f"Error loading image: {e}")
                GLib.idle_add(self._on_image_load_error)

        thread = threading.Thread(target=load_in_background, daemon=True)
        thread.start()

    def _on_image_loaded(self) -> None:
        self._update_preview()
        if self.callback:
            self.callback(self.image_background)

    def _on_image_load_error(self) -> None:
        pass

    def _update_preview(self) -> None:
        if self.image_background.image:

            def save_and_update():
                try:
                    from PIL import Image
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

    def _set_preview_image(self, temp_path: str) -> None:
        self.preview_picture.set_filename(temp_path)
        def cleanup_temp_file():
            try:
                import os
                os.unlink(temp_path)
            except:
                pass
            return False

        GLib.timeout_add(100, cleanup_temp_file)
        return False  
