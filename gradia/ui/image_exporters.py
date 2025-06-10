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

from gi.repository import Gtk, Gio, GdkPixbuf
from gradia.clipboard import copy_file_to_clipboard, save_pixbuff_to_path

ExportFormat = tuple[str, str, str]

class BaseImageExporter:
    """Base class for image export handlers"""

    SUPPORTED_OUTPUT_FORMATS: list[ExportFormat] = [
        (".png", "image/png", "PNG Image"),
        (".jpg", "image/jpeg", "JPEG Image"),
        (".jpeg", "image/jpeg", "JPEG Image"),
        (".webp", "image/webp", "WebP Image"),
    ]

    def __init__(self, window: Gtk.ApplicationWindow, temp_dir: str) -> None:
        self.window: Gtk.ApplicationWindow = window
        self.temp_dir: str = temp_dir

    def get_processed_pixbuf(self):
        return self.overlay_pixbuffs(self.window.processed_pixbuf, self.window.drawing_overlay.export_to_pixbuf())

    def overlay_pixbuffs(self, bottom: GdkPixbuf.Pixbuf, top: GdkPixbuf.Pixbuf, alpha: float = 1) -> GdkPixbuf.Pixbuf:
        if bottom.get_width() != top.get_width() or bottom.get_height() != top.get_height():
            raise ValueError("Pixbufs must be the same size to overlay")

        width = bottom.get_width()
        height = bottom.get_height()

        result = GdkPixbuf.Pixbuf.new(GdkPixbuf.Colorspace.RGB, True, 8, width, height)
        result.fill(0x00000000)

        bottom.composite(
            result,
            0, 0, width, height,
            0, 0, 1.0, 1.0,
            GdkPixbuf.InterpType.BILINEAR,
            255
        )

        top.composite(
            result,
            0, 0, width, height,
            0, 0, 1.0, 1.0,
            GdkPixbuf.InterpType.BILINEAR,
            int(255 * alpha)
        )

        return result

    def _get_dynamic_filename(self, extension: str = ".png") -> str:
       if self.window.image_path:
           original_name = os.path.splitext(os.path.basename(self.window.image_path))[0]
           return f"{original_name} ({_('Edit')}){extension}"
       return f"{_('Enhanced Screenshot')}{extension}"

    def _ensure_processed_image_available(self) -> bool:
        """Ensure processed image is available for export"""
        if not self.window.processed_pixbuf:
            raise Exception("No processed image available for export")
        return False 


class FileDialogExporter(BaseImageExporter):
    """Handles exporting images through file dialog"""
    SUPPORTED_FORMATS = {
        'png': {
            'name': _('PNG Image (*.png)'),
            'mime_type': 'image/png',
            'extensions': ['.png'],
            'save_options': {'keys': [], 'values': []}
        },
        'jpeg': {
            'name': _('JPEG Image (*.jpg)'),
            'mime_type': 'image/jpeg',
            'extensions': ['.jpg', '.jpeg'],
            'save_options': {'keys': ['quality'], 'values': ['90']}
        },
        'webp': {
            'name': _('WebP Image (*.webp)'),
            'mime_type': 'image/webp',
            'extensions': ['.webp'],
            'save_options': {'keys': ['quality'], 'values': ['90']}
        }
    }

    DEFAULT_FORMAT = 'png'

    def __init__(self, window: Gtk.ApplicationWindow, temp_dir: str) -> None:
        super().__init__(window, temp_dir)

    def save_to_file(self) -> None:
        if not self._ensure_processed_image_available():
            return

        dialog = Gtk.FileChooserNative.new(
            _("Save Image As"),
            self.window,
            Gtk.FileChooserAction.SAVE,
            _("Save"),
            _("Cancel")
        )

        dialog.set_current_name(os.path.splitext(self._get_dynamic_filename())[0])

        filters = {}
        for format_key, format_info in self.SUPPORTED_FORMATS.items():
            file_filter = Gtk.FileFilter()
            file_filter.set_name(format_info['name'])
            file_filter.add_mime_type(format_info['mime_type'])

            for ext in format_info['extensions']:
                file_filter.add_pattern(f"*{ext}")

            dialog.add_filter(file_filter)
            filters[format_key] = file_filter

        if self.DEFAULT_FORMAT in filters:
            dialog.set_filter(filters[self.DEFAULT_FORMAT])

        dialog.connect("response", self._on_dialog_response)
        dialog.show()

    def _on_dialog_response(self, dialog, response_id):
        if response_id == Gtk.ResponseType.ACCEPT:
            file = dialog.get_file()
            if file:
                save_path = file.get_path()
                selected_filter = dialog.get_filter()

                format_type = self._get_format_from_filter(selected_filter)
                if format_type:
                    save_path = self._ensure_correct_extension(save_path, format_type)
                    self._save_image(save_path, format_type)
                    self.window._show_notification(_("Image saved successfully"))

        dialog.destroy()

    def _get_format_from_filter(self, selected_filter) -> str:
        filter_name = selected_filter.get_name()
        for format_key, format_info in self.SUPPORTED_FORMATS.items():
            if filter_name == format_info['name']:
                return format_key
        return None

    def _ensure_correct_extension(self, save_path: str, format_type: str) -> str:
        format_info = self.SUPPORTED_FORMATS.get(format_type)
        if not format_info:
            return save_path

        path_lower = save_path.lower()
        for ext in format_info['extensions']:
            if path_lower.endswith(ext.lower()):
                return save_path

        return save_path + format_info['extensions'][0]

    def _save_image(self, save_path: str, format_type: str) -> None:
        pixbuf = self.get_processed_pixbuf()
        format_info = self.SUPPORTED_FORMATS.get(format_type)

        if format_info:
            save_options = format_info['save_options']
            pixbuf.savev(save_path, format_type, save_options['keys'], save_options['values'])
        else:
            raise Exception("Unsupported format")

    def _ensure_processed_image_available(self) -> bool:
        try:
            super()._ensure_processed_image_available()
            return True
        except Exception as e:
            self.window._show_notification(_("No processed image available"))
            return False

class ClipboardExporter(BaseImageExporter):
    """Handles exporting images to clipboard"""

    TEMP_CLIPBOARD_EXPORT_FILENAME: str = "clipboard_export.png"

    def __init__(self, window: Gtk.ApplicationWindow, temp_dir: str) -> None:
        super().__init__(window, temp_dir)

    def copy_to_clipboard(self) -> None:
        """Copy processed image to system clipboard"""
        try:
            self._ensure_processed_image_available()

            temp_path = save_pixbuff_to_path(self.temp_dir, self.get_processed_pixbuf())
            if not temp_path or not os.path.exists(temp_path):
                raise Exception("Failed to create temporary file for clipboard")

            copy_file_to_clipboard(temp_path)
            self.window._show_notification(_("Image copied to clipboard"))

        except Exception as e:
            self.window._show_notification(_("Failed to copy image to clipboard"))
            print(f"Error copying to clipboard: {e}")


class ExportManager:
    """Coordinates export functionality"""

    def __init__(self, window: Gtk.ApplicationWindow, temp_dir: str) -> None:
        self.window: Gtk.ApplicationWindow = window
        self.temp_dir: str = temp_dir

        self.file_exporter: FileDialogExporter = FileDialogExporter(window, temp_dir)
        self.clipboard_exporter: ClipboardExporter = ClipboardExporter(window, temp_dir)

    def save_to_file(self) -> None:
        """Export to file using file dialog"""
        self.file_exporter.save_to_file()

    def copy_to_clipboard(self) -> None:
        """Export to clipboard"""
        self.clipboard_exporter.copy_to_clipboard()

    def is_export_available(self) -> bool:
        """Check if export operations are available"""
        return bool(self.file_exporter.processed_pixbuf)

