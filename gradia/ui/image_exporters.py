import os
from typing import Tuple
from gi.repository import Gtk, Gio
from gradia.clipboard import copy_file_to_clipboard, save_pixbuff_to_path

ExportFormat = Tuple[str, str, str]

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

    def _get_dynamic_filename(self, extension: str = ".png") -> str:
        """Generate dynamic filename based on original image"""
        if self.window.image_path:
            original_name = os.path.splitext(os.path.basename(self.window.image_path))[0]
            return f"{original_name}_processed{extension}"
        return f"processed_image{extension}"

    def _ensure_processed_image_available(self) -> bool:
        """Ensure processed image is available for export"""
        if not self.window.processed_pixbuf:
            raise Exception("No processed image available for export")
        return False 


class FileDialogExporter(BaseImageExporter):
    """Handles exporting images through file dialog"""

    def __init__(self, window: Gtk.ApplicationWindow, temp_dir: str) -> None:
        super().__init__(window, temp_dir)

    def save_to_file(self) -> None:
        """Open save dialog to export processed image"""
        if not self._ensure_processed_image_available():
            return

        save_dialog = Gtk.FileDialog()
        save_dialog.set_title(_("Save Processed Image"))

        dynamic_name = self._get_dynamic_filename()
        save_dialog.set_initial_name(dynamic_name)

        filters = Gio.ListStore.new(Gtk.FileFilter)

        for ext, mime_type, display_name in self.SUPPORTED_OUTPUT_FORMATS:
            file_filter = Gtk.FileFilter()
            file_filter.set_name(display_name)
            file_filter.add_mime_type(mime_type)
            file_filter.add_suffix(ext.lstrip('.'))
            filters.append(file_filter)

        save_dialog.set_filters(filters)
        save_dialog.save(self.window, None, self._on_save_finished)

    def _on_save_finished(self, dialog: Gtk.FileDialog, result: Gio.AsyncResult) -> None:
        """Handle save dialog completion"""
        try:
            file = dialog.save_finish(result)
            if not file:
                return

            save_path = file.get_path()
            if not save_path:
                raise Exception("Invalid save path")

            self._save_processed_image(save_path)
            self.window._show_notification(_("Image saved"))

        except Exception as e:
            self.window._show_notification(f"{_('Failed to save image')}: {str(e)}")
            print(f"Error saving file: {e}")

    def _save_processed_image(self, save_path: str) -> None:
        """Save the processed image to the specified path"""
        _unused, ext = os.path.splitext(save_path.lower())

        format_map = {
            '.png': 'png',
            '.jpg': 'jpeg',
            '.jpeg': 'jpeg',
            '.webp': 'webp'
        }

        pixbuf_format = format_map.get(ext, 'png')

        if pixbuf_format in ['jpeg', 'webp']:
            self.window.processed_pixbuf.savev(save_path, pixbuf_format, ['quality'], ['90'])
        else:
            self.window.processed_pixbuf.savev(save_path, pixbuf_format, [], [])

    def _ensure_processed_image_available(self) -> bool:
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

    TEMP_CLIPBOARD_EXPORT_FILENAME: str = "clipboard_export.png"

    def __init__(self, window: Gtk.ApplicationWindow, temp_dir: str) -> None:
        super().__init__(window, temp_dir)

    def copy_to_clipboard(self) -> None:
        """Copy processed image to system clipboard"""
        try:
            self._ensure_processed_image_available()

            temp_path = save_pixbuff_to_path(self.temp_dir, self.window.processed_pixbuf)
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
        return bool(self.window.processed_pixbuf)
