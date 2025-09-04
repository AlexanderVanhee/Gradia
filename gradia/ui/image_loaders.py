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
import mimetypes
import shutil
from urllib.parse import urlparse, unquote
import urllib.request
from datetime import datetime
from typing import Optional, Callable

from gi.repository import Gtk, Gio, Gdk, GLib, Xdp
from gradia.clipboard import save_texture_to_file
from gradia.ui.image_creation.source_image_generator import SourceImageGeneratorWindow
from gradia.utils.timestamp_filename import TimestampedFilenameGenerator
from gradia.backend.logger import Logger
from enum import Enum, auto
ImportFormat = tuple[str, str]

logger = Logger()

class ImageOrigin(Enum):
        FileDialog = auto()
        DragDrop = auto()
        Clipboard = auto()
        Screenshot = auto()
        FakeScreenshot = auto()
        CommandLine = auto()
        SourceImage = auto()

class LoadedImage:
    def __init__(self, image_path: str, origin: ImageOrigin, screenshot_path: str = None):
        self.image_path: str = image_path
        self.origin: ImageOrigin = origin
        self.screenshot_path: str | None = screenshot_path

    def get_proper_name(self, with_extension: bool = True) -> str:
        if self.origin == ImageOrigin.Clipboard:
            return _("Clipboard Image")
        elif self.origin in (ImageOrigin.Screenshot, ImageOrigin.FakeScreenshot):
            return _("Screenshot")
        elif self.origin == ImageOrigin.SourceImage:
            return _("Generated Image")
        else:
            filename = os.path.basename(self.image_path)
            if not with_extension:
                filename, _unused = os.path.splitext(filename)
            return filename

    def get_proper_folder(self) -> str:
        if self.origin == ImageOrigin.Clipboard:
            return _("From clipboard")
        elif self.origin == ImageOrigin.Screenshot or self.origin == ImageOrigin.FakeScreenshot:
            return _("Screenshot")
        elif self.origin == ImageOrigin.SourceImage:
            return _("Source")
        else:
            return os.path.basename(os.path.dirname(self.image_path))

    def has_proper_name(self) -> bool:
        return self.origin not in {
            ImageOrigin.Clipboard,
            ImageOrigin.Screenshot,
            ImageOrigin.FakeScreenshot,
            ImageOrigin.SourceImage,
        }

    def has_proper_folder(self) -> bool:
        return self.origin not in {
            ImageOrigin.Clipboard,
            ImageOrigin.Screenshot,
            ImageOrigin.FakeScreenshot,
            ImageOrigin.SourceImage,
        }

    def get_folder_path(self) -> str:
        return os.path.dirname(self.image_path)


    def is_screenshot(self) -> bool:
        return self.origin in (ImageOrigin.Screenshot, ImageOrigin.FakeScreenshot)

class BaseImageLoader:
    """Base class for image loading handlers"""
    SUPPORTED_INPUT_FORMATS: list[ImportFormat] = [
        (".png", "image/png"),
        (".jpg", "image/jpg"),
        (".jpeg", "image/jpeg"),
        (".webp", "image/webp"),
        (".avif", "image/avif"),
    ]

    def __init__(self, window: Gtk.ApplicationWindow, temp_dir: str) -> None:
        self.window: Gtk.ApplicationWindow = window
        self.temp_dir: str = temp_dir

    def _is_supported_format(self, file_path: str) -> bool:
        """Check if file format is supported"""
        lower_path = file_path.lower()
        supported_extensions = [ext for ext, _ in self.SUPPORTED_INPUT_FORMATS]
        return any(lower_path.endswith(ext) for ext in supported_extensions)

    def _set_image_and_update_ui(self, image: LoadedImage, copy_after_processing=False) -> None:
        """Common method to set image and update UI"""
        self.window.set_image(image, copy_after_processing=copy_after_processing)

    def _handle_uri(self, uri: str, origin: ImageOrigin) -> bool:
        """Handle URI loading for both file and web URIs"""
        logger.info(f"Processing URI: {uri}")

        if uri.startswith("file://"):
            file_path = unquote(urlparse(uri).path)

            if not os.path.isfile(file_path):
                logger.error("File does not exist:", file_path)
                return False

            if not self._is_supported_format(file_path):
                self.window._show_notification(_("Not a supported image format"))
                return False

            self._set_image_and_update_ui(LoadedImage(file_path, origin))
            return True

        elif uri.startswith(("http://", "https://")):
            return self._handle_image_url(uri, origin)

        else:
            logger.info("Unsupported URI scheme:", uri)
            self.window._show_notification(_("Not a supported image format"))
            return False

    def _handle_image_url(self, url: str, origin: ImageOrigin) -> bool:
        try:
            path = urlparse(url).path
            mime_type, _unused = mimetypes.guess_type(path)
            logger.info(f"mime type from guess_type: {mime_type}")

            if not (mime_type and mime_type.startswith("image/")):
                lower_path = path.lower()
                supported_extensions = [ext for ext, _ in self.SUPPORTED_INPUT_FORMATS]
                if not any(lower_path.endswith(ext) for ext in supported_extensions):
                    self.window._show_notification(_("Not a supported image format"))
                    return False
                else:
                    logger.info("Fallback: file extension matches supported image format.")

            filename = os.path.basename(path) or "downloaded_image"
            temp_path = os.path.join(self.temp_dir, filename)

            urllib.request.urlretrieve(url, temp_path)

            if not self._is_supported_format(temp_path):
                self.window._show_notification(_("URL is not a supported image format"))
                os.remove(temp_path)
                return False

            self._set_image_and_update_ui(LoadedImage(temp_path, origin))
            return True

        except Exception as e:
            logger.error("Error downloading image:", e)
            self.window._show_notification(_("Failed to load image from URL."))
            return False

class FileDialogImageLoader(BaseImageLoader):
    """Handles loading images through file dialog"""
    def __init__(self, window: Gtk.ApplicationWindow, temp_dir: str) -> None:
        super().__init__(window, temp_dir)

    def open_file_dialog(self) -> None:
        """Open file dialog to select an image"""
        file_dialog = Gtk.FileDialog()
        file_dialog.set_title(_("Open Image"))

        image_filter = Gtk.FileFilter()
        image_filter.set_name(_("Image Files"))
        for _ext, mime_type in self.SUPPORTED_INPUT_FORMATS:
            image_filter.add_mime_type(mime_type)

        filters = Gio.ListStore.new(Gtk.FileFilter)
        filters.append(image_filter)
        file_dialog.set_filters(filters)

        file_dialog.open(self.window, None, self._on_file_selected)

    def _on_file_selected(self, dialog: Gtk.FileDialog, result: Gio.AsyncResult) -> None:
        try:
            file = dialog.open_finish(result)
            if not file:
                return

            file_path = file.get_path()
            if not file_path or not os.path.isfile(file_path):
                logger.info(f"Invalid file path: {file_path}")
                return

            if not self._is_supported_format(file_path):
                logger.info(f"Unsupported file format: {file_path}")
                return

            self._set_image_and_update_ui(LoadedImage(file_path, ImageOrigin.FileDialog))

        except Exception as e:
            logger.error(f"Error opening file: {e}")


class DragDropImageLoader(BaseImageLoader):
    def __init__(self, window: Gtk.ApplicationWindow, temp_dir: str) -> None:
        super().__init__(window, temp_dir)

    def handle_file_drop(
        self,
        drop_target: Optional[object],
        value: object,
        x: int,
        y: int
    ) -> bool:

        if isinstance(value, Gio.File):
            uri = value.get_uri()
            return self._handle_uri(uri, ImageOrigin.DragDrop)

        return False


class ClipboardImageLoader(BaseImageLoader):
    def __init__(self, window: Gtk.ApplicationWindow, temp_dir: str) -> None:
        super().__init__(window, temp_dir)

    def load_from_clipboard(self) -> None:
        display = Gdk.Display.get_default()
        clipboard = display.get_clipboard()

        clipboard.read_value_async(
            Gdk.FileList,
            0,
            None,
            self._on_uris_get
        )

    def _on_uris_get(self, clipboard, result, user_data=None) -> None:
        try:
            file_list = clipboard.read_value_finish(result)
            if file_list:
                files = file_list.get_files()
                if files:
                    file_obj = files[0]
                    uri = file_obj.get_uri()
                    self._handle_uri(uri, ImageOrigin.Clipboard)
        except GLib.GError as e:
            print(f"Error reading URIs: {e}")


class ScreenshotImageLoader(BaseImageLoader):
    """Handles loading images through screenshot capture"""

    def __init__(self, window: Gtk.ApplicationWindow, temp_dir: str, app: Gtk.Application) -> None:
        super().__init__(window, temp_dir)
        self.portal = Xdp.Portal()
        self._error_callback: Optional[Callable[[str], None]] = None
        self._success_callback: Optional[Callable[[], None]] = None
        self._screenshot_uris: list[str] = []  # Store URIs of taken screenshots
        self.window = window

    def _update_delete_action_state(self) -> None:
        action = self.window.lookup_action("delete-screenshots")
        if action:
            action.set_enabled(bool(self._screenshot_uris))

    def take_screenshot(
        self,
        flags: Xdp.ScreenshotFlags = Xdp.ScreenshotFlags.INTERACTIVE,
        on_error_or_cancel: Optional[Callable[[str], None]] = None,
        on_success: Optional[Callable[[], None]] = None
    ) -> None:
        try:
            self._error_callback = on_error_or_cancel
            self._success_callback = on_success
            self.window.hide()
            GLib.timeout_add(150, self._do_take_screenshot, flags)
        except Exception as e:
            logger.error(f"Failed to initiate screenshot: {e}")
            self.window._show_notification(_("Failed to take screenshot"))
            if on_error_or_cancel:
                on_error_or_cancel(str(e))

    def _do_take_screenshot(self, flags: Xdp.ScreenshotFlags) -> bool:
        try:
            self.portal.take_screenshot(
                None,
                flags,
                None,
                self._on_screenshot_taken,
                None
            )
        except Exception as e:
            logger.info(f"Failed during screenshot: {e}")
            self.window._show_notification(_("Failed to take screenshot"))
            self.window.show()
            if self._error_callback:
                self._error_callback(str(e))
            self._error_callback = None
        return False

    def _on_screenshot_taken(self, portal_object, result, user_data) -> None:
        """Handle screenshot completion and restore window"""
        try:
            uri = self.portal.take_screenshot_finish(result)
            self._screenshot_uris.append(uri)  # Save URI
            self._handle_screenshot_uri(uri)
            self._update_delete_action_state()
        except GLib.Error as e:
            logger.error(f"Screenshot error: {e}")
            self.window._show_notification(_("Screenshot cancelled"))
            if self._error_callback:
                self._error_callback(str(e))
        finally:
            self.window.show()
            self._error_callback = None

    def _handle_screenshot_uri(self, uri: str) -> None:
        """Process the screenshot URI and convert to local file"""
        try:
            file = Gio.File.new_for_uri(uri)
            original_path = file.get_path()
            success, contents, _unused = file.load_contents(None)
            if not success or not contents:
                raise Exception("Failed to load screenshot data")


            filename = TimestampedFilenameGenerator().generate(_("Edited Screenshot From %Y-%m-%d %H-%M-%S")) + ".png"
            temp_path = os.path.join(self.temp_dir, filename)

            with open(temp_path, 'wb') as f:
                f.write(contents)

            self._set_image_and_update_ui(LoadedImage(temp_path, ImageOrigin.Screenshot, screenshot_path=original_path), copy_after_processing=True)
            self.window._show_notification(_("Screenshot captured!"))

            if self._success_callback:
                self._success_callback()

        except Exception as e:
            logger.error(f"Error processing screenshot: {e}")
            self.window._show_notification(_("Failed to process screenshot"))

    def load_path_as_screenshot(self, file_path: str) -> None:
        try:
            file = Gio.File.new_for_path(file_path)
            uri = file.get_uri()
            self._screenshot_uris.append(uri)
            self._update_delete_action_state()

            filename = TimestampedFilenameGenerator().generate(_("Edited Screenshot From %Y-%m-%d %H-%M-%S")) + ".png"
            new_path = os.path.join(self.temp_dir, filename)

            shutil.copy(file_path, new_path)

            self._set_image_and_update_ui(LoadedImage(file_path, ImageOrigin.FakeScreenshot, screenshot_path=file_path), copy_after_processing=True)

            self.window._show_notification(_("Screenshot captured!"))

        except Exception as e:
            logger.error(f"Error loading screenshot from path: {e}")
            self.window._show_notification(_("Failed to load screenshot"))

    def get_screenshot_uris(self) -> list[str]:
        return self._screenshot_uris.copy()

    def delete_screenshots(self) -> None:
        for uri in self._screenshot_uris:
            try:
                file = Gio.File.new_for_uri(uri)
                file.trash(None)
            except Exception as e:
                logger.error(f"Failed to trash screenshot {uri}: {e}")

        self._screenshot_uris.clear()
        self._update_delete_action_state()


class CommandlineLoader(BaseImageLoader):
    """Handles loading images from command line arguments or programmatic file paths"""
    def __init__(self, window: Gtk.ApplicationWindow, temp_dir: str) -> None:
        super().__init__(window, temp_dir)

    def load_from_file(self, file_path: str) -> None:
        try:
            if not file_path:
                logger.info("No file path provided")
                return

            if not os.path.isfile(file_path):
                logger.info(f"File does not exist: {file_path}")
                return

            if not self._is_supported_format(file_path):
                logger.info(f"Unsupported file format: {file_path}")
                return

            self._set_image_and_update_ui(LoadedImage(file_path, ImageOrigin.CommandLine))

        except Exception as e:
            logger.error(f"Error loading file from command line: {e}")

class SourceImageLoader(BaseImageLoader):
    """Handles loading images from source code image generator"""

    def __init__(self, window: Gtk.ApplicationWindow, temp_dir: str) -> None:
        super().__init__(window, temp_dir)
        self._generator_window: Optional[SourceImageGeneratorWindow] = None

    def open_generator(self) -> None:
        if self._generator_window and self._generator_window.get_visible():
            self._generator_window.present()
            return

        self._generator_window = SourceImageGeneratorWindow(parent_window=self.window, temp_dir=self.temp_dir, export_callback=self.load_generated_image)
        self._generator_window.set_transient_for(self.window)
        self._generator_window.connect("destroy", self._on_generator_window_destroyed)
        self._generator_window.show()

    def _on_generator_window_destroyed(self, window: Gtk.Window) -> None:
        self._generator_window = None

    def load_generated_image(self, image_path: str) -> None:
        if not image_path or not os.path.isfile(image_path):
            logger.warning(f"Invalid generated image path: {image_path}")
            return

        self._set_image_and_update_ui(LoadedImage(image_path, ImageOrigin.SourceImage))
        self.window._show_notification(_("Source snippet Generated!"))

class ImportManager:
    def __init__(self, window: Gtk.ApplicationWindow, temp_dir: str, app: Gtk.Application) -> None:
        self.window: Gtk.ApplicationWindow = window
        self.temp_dir: str = temp_dir

        self.file_loader: FileDialogImageLoader = FileDialogImageLoader(window, temp_dir)
        self.drag_drop_loader: DragDropImageLoader = DragDropImageLoader(window, temp_dir)
        self.clipboard_loader: ClipboardImageLoader = ClipboardImageLoader(window, temp_dir)
        self.screenshot_loader: ScreenshotImageLoader = ScreenshotImageLoader(window, temp_dir, app)
        self.commandline_loader: CommandlineLoader = CommandlineLoader(window, temp_dir)
        self.source_image_loader: SourceImageLoader = SourceImageLoader(window, temp_dir)

    def open_file_dialog(self) -> None:
        self.file_loader.open_file_dialog()

    def _on_drop_action(self, action: Optional[object], param: object) -> None:
        if isinstance(param, GLib.Variant):
            uri = param.get_string()
            file = Gio.File.new_for_uri(uri)
            self.drag_drop_loader.handle_file_drop(None, file, 0, 0)
        else:
            logger.info("ImportManager._on_drop_action: Invalid drop parameter")

    def load_from_clipboard(self) -> None:
        self.clipboard_loader.load_from_clipboard()

    def take_screenshot(
        self,
        flags: Xdp.ScreenshotFlags = Xdp.ScreenshotFlags.INTERACTIVE,
        on_error_or_cancel: Optional[Callable[[str], None]] = None,
        on_success: Optional[Callable[[], None]] = None
    ) -> None:
        self.screenshot_loader.take_screenshot(flags, on_error_or_cancel, on_success)

    def load_as_screenshot(self, file_path: str):
        self.screenshot_loader.load_path_as_screenshot(file_path)

    def get_screenshot_uris(self) -> list[str]:
        return self.screenshot_loader.get_screenshot_uris()

    def delete_screenshots(self) -> None:
        return self.screenshot_loader.delete_screenshots()

    def load_from_file(self, file_path: str) -> None:
        self.commandline_loader.load_from_file(file_path)

    def generate_from_source_code(self) -> None:
        self.source_image_loader.open_generator()

