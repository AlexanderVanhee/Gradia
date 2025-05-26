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
import gi
from gi.repository import Gtk, Gio, Gdk
from .clipboard import save_texture_to_file

class BaseImageLoader:
    """Base class for image loading handlers"""

    SUPPORTED_INPUT_FORMATS = [
        (".png", "image/png"),
        (".jpg", "image/jpg"),
        (".jpeg", "image/jpeg"),
        (".webp", "image/webp"),
        (".avif", "image/avif"),
    ]

    def __init__(self, window, temp_dir):
        self.window = window
        self.temp_dir = temp_dir

    def _is_supported_format(self, file_path):
        """Check if file format is supported"""
        lower_path = file_path.lower()
        supported_extensions = [ext for ext, _mime in self.SUPPORTED_INPUT_FORMATS]
        return any(lower_path.endswith(ext) for ext in supported_extensions)

    def _set_image_and_update_ui(self, image_path, filename, location):
        """Common method to set image and update UI"""
        self.window.image_path = image_path
        self.window._update_sidebar_info(filename, location)
        self.window._start_processing()

class FileDialogImageLoader(BaseImageLoader):
    """Handles loading images through file dialog"""

    def __init__(self, window, temp_dir):
        super().__init__(window, temp_dir)

    def open_file_dialog(self):
        """Open file dialog to select an image"""
        print("test")
        file_dialog = Gtk.FileDialog()
        file_dialog.set_title("Open Image")

        # Create filter for supported image formats
        image_filter = Gtk.FileFilter()
        image_filter.set_name("Image Files")
        for _, mime_type in self.SUPPORTED_INPUT_FORMATS:
            image_filter.add_mime_type(mime_type)

        filters = Gio.ListStore.new(Gtk.FileFilter)
        filters.append(image_filter)
        file_dialog.set_filters(filters)

        file_dialog.open(self.window.win, None, self._on_file_selected)

    def _on_file_selected(self, dialog, result):
        """Handle file selection from dialog"""
        try:
            file = dialog.open_finish(result)
            if file is None:
                return

            file_path = file.get_path()
            if not file_path or not os.path.isfile(file_path):
                print(f"Invalid file path: {file_path}")
                return

            if not self._is_supported_format(file_path):
                print(f"Unsupported file format: {file_path}")
                return

            filename = os.path.basename(file_path)
            directory = os.path.dirname(file_path)

            self._set_image_and_update_ui(file_path, filename, directory)

        except Exception as e:
            print(f"Error opening file: {e}")

class DragDropImageLoader(BaseImageLoader):
    """Handles loading images through drag and drop"""

    def __init__(self, window, temp_dir):
        super().__init__(window, temp_dir)

    def handle_file_drop(self, drop_target, value, x, y):
        """Handle file dropped onto the application"""
        if not isinstance(value, Gio.File):
            return False

        file_path = value.get_path()
        if not file_path or not os.path.isfile(file_path):
            return False

        if not self._is_supported_format(file_path):
            return False

        filename = os.path.basename(file_path)
        directory = os.path.dirname(file_path)

        self._set_image_and_update_ui(file_path, filename, directory)
        return True

class ClipboardImageLoader(BaseImageLoader):
    """Handles loading images from clipboard"""

    TEMP_CLIPBOARD_FILENAME = "clipboard_image.png"

    def __init__(self, window, temp_dir):
        super().__init__(window, temp_dir)

    def load_from_clipboard(self):
        """Load image from system clipboard"""

        clipboard = Gdk.Display.get_default().get_clipboard()
        clipboard.read_texture_async(None, self._handle_clipboard_texture)

    def _handle_clipboard_texture(self, clipboard, result):
        """Handle clipboard texture data"""
        try:
            texture = clipboard.read_texture_finish(result)
            if texture is None:
                print("No image found in clipboard")
                self.window._show_notification("No image found in clipboard")
                return

            # Save clipboard texture to temporary file
            image_path = save_texture_to_file(texture, self.temp_dir)
            if not image_path:
                raise Exception("Failed to save clipboard image to file")

            filename = "Clipboard Image"
            location = "From clipboard"

            self._set_image_and_update_ui(image_path, filename, location)

        except Exception as e:
            error_msg = str(e)
            if "No compatible transfer format found" in error_msg:
                self.window._show_notification("Clipboard does not contain an image.")
            else:
                self.window._show_notification("Failed to load image from clipboard.")
                print(f"Error processing clipboard image: {e}")

        finally:
            self.window._set_loading_state(False)

class ImportManager:
    def __init__(self, window, temp_dir):
        self.window = window
        self.temp_dir = temp_dir

        self.file_loader = FileDialogImageLoader(window, temp_dir)
        self.drag_drop_loader = DragDropImageLoader(window, temp_dir)
        self.clipboard_loader = ClipboardImageLoader(window, temp_dir)

    def open_file_dialog(self):
        self.file_loader.open_file_dialog()

    def _on_drop_action(self, action, param):
        if param and isinstance(param, Gio.File):
            self.drag_drop_loader.handle_file_drop(None, param, 0, 0)
        else:
            print("ImportManager._on_drop_action: Invalid drop parameter")

    def load_from_clipboard(self):
        self.clipboard_loader.load_from_clipboard()
