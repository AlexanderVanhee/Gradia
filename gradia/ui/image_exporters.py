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
import subprocess

from gi.repository import Gtk, Gio, GdkPixbuf
from gradia.clipboard import copy_file_to_clipboard, copy_text_to_clipboard, save_pixbuff_to_path
from gradia.backend.logger import Logger
from gradia.app_constants import SUPPORTED_EXPORT_FORMATS, DEFAULT_EXPORT_FORMAT
from gradia.backend.settings import Settings

ExportFormat = tuple[str, str, str]

logger = Logger()
class BaseImageExporter:
    """Base class for image export handlers"""

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
    def __init__(self, window: Gtk.ApplicationWindow, temp_dir: str) -> None:
        super().__init__(window, temp_dir)
        self.settings = Settings()

    def save_to_file(self, filetype: str = None) -> None:
        if not self._ensure_processed_image_available():
            return

        dialog = Gtk.FileChooserNative.new(
            _("Save Image As"),
            self.window,
            Gtk.FileChooserAction.SAVE,
            _("Save"),
            _("Cancel")
        )
        dialog.set_modal(True)

        target_format = (
            filetype if filetype and filetype in SUPPORTED_EXPORT_FORMATS
            else self.settings.export_format if self.settings.export_format in SUPPORTED_EXPORT_FORMATS
            else DEFAULT_EXPORT_FORMAT
        )
        base_name = os.path.splitext(self._get_dynamic_filename())[0]
        default_ext = SUPPORTED_EXPORT_FORMATS[target_format]['extensions'][0]
        dialog.set_current_name(base_name + default_ext)

        dialog.connect("response", lambda d, r: self._on_dialog_response(d, r, target_format))
        dialog.show()

    def _on_dialog_response(self, dialog, response_id, suggested_format):
        if response_id == Gtk.ResponseType.ACCEPT:
            file = dialog.get_file()
            if file:
                save_path = file.get_path()

                format_type = self._get_format_from_extension(save_path)

                if format_type not in SUPPORTED_EXPORT_FORMATS:
                    self.window._show_notification(_("Unsupported image file extension."))
                    dialog.destroy()
                    return

                save_path = self._ensure_correct_extension(save_path, format_type)
                logger.debug(f"Saving to: {save_path} as {format_type}")
                self._save_image(save_path, format_type)
                self.window._show_notification(_("Image saved successfully"))

        dialog.destroy()

    def _get_format_from_extension(self, file_path: str) -> str:
        path_lower = file_path.lower()
        for format_key, format_info in SUPPORTED_EXPORT_FORMATS.items():
            for ext in format_info['extensions']:
                if path_lower.endswith(ext.lower()):
                    return format_key
        return None

    def _ensure_correct_extension(self, save_path: str, format_type: str) -> str:
        format_info = SUPPORTED_EXPORT_FORMATS.get(format_type)
        if not format_info:
            return save_path

        path_lower = save_path.lower()
        for ext in format_info['extensions']:
            if path_lower.endswith(ext.lower()):
                return save_path

        return save_path + format_info['extensions'][0]

    def _get_format_from_filter(self, selected_filter) -> str:
        filter_name = selected_filter.get_name()
        for format_key, format_info in SUPPORTED_EXPORT_FORMATS.items():
            if filter_name == format_info['name']:
                return format_key
        return None

    def _save_image(self, save_path: str, format_type: str) -> None:
        pixbuf = self.get_processed_pixbuf()
        format_info = SUPPORTED_EXPORT_FORMATS.get(format_type)

        if not format_info:
            raise Exception("Unsupported format")

        save_options = format_info['save_options']
        save_keys = save_options['keys'][:]
        save_values = save_options['values'][:]

        if not self.settings.export_compress:
            for i in reversed(range(len(save_keys))):
                key_lower = save_keys[i].lower()
                if "compression" in key_lower or "quality" in key_lower:
                    del save_keys[i]
                    del save_values[i]

        pixbuf.savev(save_path, format_type, save_keys, save_values)

    def _ensure_processed_image_available(self) -> bool:
        try:
            super()._ensure_processed_image_available()
            return True
        except Exception:
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


class CommandLineExporter(BaseImageExporter):
    def __init__(self, window: Gtk.ApplicationWindow, temp_dir: str) -> None:
        super().__init__(window, temp_dir)

    def _is_valid_url(self, text: str) -> bool:
        text = text.strip()
        return text.startswith(('http://', 'https://')) and '.' in text

    def _show_link_notification(self, url: str) -> None:
        self.window._show_notification(
            _("Link generated successfully"),
            _("Open Link"),
            lambda: self._open_link(url)
        )

    def _open_link(self, url: str) -> None:
        try:
            Gio.AppInfo.launch_default_for_uri(url, None)
        except Exception as e:
            logger.error(f"Failed to open URL: {e}")

    def run_custom_command(self) -> None:
        try:
            self._ensure_processed_image_available()
            temp_path = save_pixbuff_to_path(self.temp_dir, self.get_processed_pixbuf())
            if not temp_path or not os.path.exists(temp_path):
                raise Exception("Failed to create temporary file for command")

            command_template = Settings().custom_export_command
            if "$1" not in command_template:
                raise Exception("Custom export command must include $1 as a placeholder for the image path")

            command = command_template.replace("$1", temp_path)

            logger.info("running custom command: " + command)
            process = subprocess.Popen(
                command,
                shell=True,
                executable="/bin/bash",
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            stdout, stderr = process.communicate()

            logger.info("stderr:" + (stderr.decode('utf-8') if stderr else "None"))
            logger.info("stdout:" + (stdout.decode('utf-8') if stdout else "None"))
            logger.info("return code:" + str(process.returncode))

            if process.returncode != 0:
                error_msg = stderr.decode('utf-8').strip() if stderr else "Unknown error"
                self.window._show_notification(_("Custom command failed: ") + error_msg)
                return

            if stderr:
                warning_msg = stderr.decode('utf-8').strip()
                if warning_msg:
                    self.window._show_notification(_("Warning: ") + warning_msg)

            output_text = stdout.decode('utf-8').strip()
            if output_text:
                logger.info("output: " + output_text)

                if self._is_valid_url(output_text):
                    copy_text_to_clipboard(output_text)
                    self._show_link_notification(output_text)
                else:
                    copy_text_to_clipboard(output_text)
                    self.window._show_notification(_("Result copied to clipboard"))
            else:
                self.window._show_notification(_("No output from command"))

        except Exception as e:
            self.window._show_notification(_("Failed to run custom export command"))
            logger.error(f"Error running custom export command: {e}")
            import traceback
            traceback.print_exc()


class ExportManager:
    """Coordinates export functionality"""

    def __init__(self, window: Gtk.ApplicationWindow, temp_dir: str) -> None:
        self.window: Gtk.ApplicationWindow = window
        self.temp_dir: str = temp_dir

        self.file_exporter: FileDialogExporter = FileDialogExporter(window, temp_dir)
        self.clipboard_exporter: ClipboardExporter = ClipboardExporter(window, temp_dir)
        self.command_exporter: CommandLineExporter = CommandLineExporter(window, temp_dir)

    def save_to_file(self) -> None:
        """Export to file using file dialog"""
        self.file_exporter.save_to_file()

    def copy_to_clipboard(self) -> None:
        """Export to clipboard"""
        self.clipboard_exporter.copy_to_clipboard()

    def run_custom_command(self) -> None:
        """Run custom export command"""
        self.command_exporter.run_custom_command()

    def is_export_available(self) -> bool:
        """Check if export operations are available"""
        return bool(self.file_exporter.processed_pixbuf)

