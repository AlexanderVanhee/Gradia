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
import shutil
import gi
from gi.repository import Gtk, Gio
from gradia.clipboard import copy_file_to_clipboard, save_pixbuff_to_path

class BaseImageExporter:
    """Base class for image export handlers"""

    SUPPORTED_OUTPUT_FORMATS = [
        (".png", "image/png", "PNG Image"),
        (".jpg", "image/jpeg", "JPEG Image"),
        (".jpeg", "image/jpeg", "JPEG Image"),
        (".webp", "image/webp", "WebP Image"),
    ]

    def __init__(self, window, temp_dir):
        self.window = window
        self.temp_dir = temp_dir

    def _get_dynamic_filename(self, extension=".png"):
        """Generate dynamic filename based on original image"""
        if self.window.image_path:
            original_name = os.path.splitext(os.path.basename(self.window.image_path))[0]
            return f"{original_name}_processed{extension}"
        else:
            return f"processed_image{extension}"

    def _ensure_processed_image_available(self):
        """Ensure processed image is available for export"""
        if not self.window.processed_pixbuf:
            raise Exception("No processed image available for export")

class FileDialogExporter(BaseImageExporter):
    """Handles exporting images through file dialog"""

    def __init__(self, window, temp_dir):
        super().__init__(window, temp_dir)

    def save_to_file(self):
        """Open save dialog to export processed image"""
        if not self._ensure_processed_image_available():
            return

        save_dialog = Gtk.FileDialog()
        save_dialog.set_title(_("Save Processed Image"))

        # Set default filename
        dynamic_name = self._get_dynamic_filename()
        save_dialog.set_initial_name(dynamic_name)

        # Create filters for supported formats
        filters = Gio.ListStore.new(Gtk.FileFilter)

        for ext, mime_type, display_name in self.SUPPORTED_OUTPUT_FORMATS:
            file_filter = Gtk.FileFilter()
            file_filter.set_name(display_name)
            file_filter.add_mime_type(mime_type)
            file_filter.add_suffix(ext.lstrip('.'))
            filters.append(file_filter)

        save_dialog.set_filters(filters)
        save_dialog.save(self.window.win, None, self._on_save_finished)

    def _on_save_finished(self, dialog, result):
        """Handle save dialog completion"""
        try:
            file = dialog.save_finish(result)
            if file is None:
                return

            save_path = file.get_path()
            if not save_path:
                raise Exception("Invalid save path")

            self._save_processed_image(save_path)
            self.window._show_notification(_("Image saved"))

        except Exception as e:
            error_msg = f"Failed to save image: {str(e)}"
            self.window._show_notification(error_msg)
            print(f"Error saving file: {e}")

    def _save_processed_image(self, save_path):
        """Save the processed image to the specified path"""
        # Get file extension to determine format
        _, ext = os.path.splitext(save_path.lower())

        # Map extensions to pixbuf formats
        format_map = {
            '.png': 'png',
            '.jpg': 'jpeg',
            '.jpeg': 'jpeg',
            '.webp': 'webp'
        }

        pixbuf_format = format_map.get(ext, 'png')

        # Save with appropriate format and quality settings
        if pixbuf_format == 'jpeg':
            # JPEG format with quality setting
            self.window.processed_pixbuf.savev(save_path, pixbuf_format, ['quality'], ['90'])
        elif pixbuf_format == 'webp':
            # WebP format with quality setting
            self.window.processed_pixbuf.savev(save_path, pixbuf_format, ['quality'], ['90'])
        else:
            # PNG and other formats
            self.window.processed_pixbuf.savev(save_path, pixbuf_format, [], [])

    def _ensure_processed_image_available(self):
        """Override to return boolean for easier checking"""
        try:
            super()._ensure_processed_image_available()
            return True
        except Exception as e:
            self.window._show_notification(_("No processed image available to save"))
            print(f"Export check failed: {e}")
            return False

class ClipboardExporter(BaseImageExporter):
    """Handles exporting images to clipboard"""

    TEMP_CLIPBOARD_EXPORT_FILENAME = "clipboard_export.png"

    def __init__(self, window, temp_dir):
        super().__init__(window, temp_dir)

    def copy_to_clipboard(self):
        """Copy processed image to system clipboard"""
        try:
            self._ensure_processed_image_available()

            # Save pixbuf to temporary file for clipboard operation
            temp_path = save_pixbuff_to_path(self.temp_dir, self.window.processed_pixbuf)
            if not temp_path or not os.path.exists(temp_path):
                raise Exception("Failed to create temporary file for clipboard")

            # Copy to clipboard
            copy_file_to_clipboard(temp_path)
            self.window._show_notification(_("Image copied to clipboard"))

        except Exception as e:
            self.window._show_notification(_("Failed to copy image to clipboard"))
            print(f"Error copying to clipboard: {e}")

class ExportManager:

    def __init__(self, window, temp_dir):
        self.window = window
        self.temp_dir = temp_dir

        # Initialize exporters
        self.file_exporter = FileDialogExporter(window, temp_dir)
        self.clipboard_exporter = ClipboardExporter(window, temp_dir)

    def save_to_file(self):
        """Export to file using file dialog"""
        self.file_exporter.save_to_file()

    def copy_to_clipboard(self):
        """Export to clipboard"""
        self.clipboard_exporter.copy_to_clipboard()

    def is_export_available(self):
        """Check if export operations are available"""
        return self.window.processed_pixbuf is not None
