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

from collections.abc import Callable
import os
import threading
from typing import Any, Optional

from gi.repository import Adw, GLib, GObject, Gdk, Gio, Gtk, Xdp

from gradia.clipboard import *
from gradia.graphics.background import Background
from gradia.graphics.gradient import GradientBackground
from gradia.graphics.image import ImageBackground
from gradia.graphics.image_processor import ImageProcessor
from gradia.graphics.solid import SolidBackground
from gradia.overlay.drawing_actions import DrawingMode
from gradia.ui.background_selector import BackgroundSelector
from gradia.ui.image_exporters import ExportManager
from gradia.ui.image_loaders import ImportManager, LoadedImage
from gradia.ui.image_sidebar import ImageSidebar, ImageOptions
from gradia.ui.image_stack import ImageStack
from gradia.ui.ui_parts import *
from gradia.ui.welcome_page import WelcomePage
from gradia.utils.aspect_ratio import *
from gradia.ui.preferences_window import PreferencesWindow
from gradia.backend.settings import Settings
from gradia.constants import rootdir, build_type # pyright: ignore
from gradia.ui.dialog.delete_screenshots_dialog import DeleteScreenshotsDialog
from gradia.ui.dialog.confirm_close_dialog import ConfirmCloseDialog
from gradia.backend.tool_config import ToolOption

@Gtk.Template(resource_path=f"{rootdir}/ui/main_window.ui")
class GradiaMainWindow(Adw.ApplicationWindow):
    __gtype_name__ = 'GradiaMainWindow'

    SIDEBAR_WIDTH: int = 300

    PAGE_IMAGE: str = "image"
    PAGE_LOADING: str = "loading"

    TEMP_PROCESSED_FILENAME: str = "processed.png"

    toast_overlay: Adw.ToastOverlay = Gtk.Template.Child()
    toolbar_view: Adw.ToolbarView = Gtk.Template.Child()

    welcome_content: WelcomePage = Gtk.Template.Child()

    main_stack: Gtk.Stack = Gtk.Template.Child()
    split_view: Gtk.Box = Gtk.Template.Child()

    def __init__(
        self,
        temp_dir: str,
        version: str,
        file_path: Optional[str] = None,
        start_screenshot: Optional[str] = None,
        **kwargs
    ) -> None:
        super().__init__(**kwargs)
        self._setup_accelerator_handling()
        self.app: Adw.Application = kwargs['application']
        self.temp_dir: str = temp_dir
        self.version: str = version
        self.start_screenshot = start_screenshot
        self.file_path: Optional[str] = file_path
        self.image: Optional[LoadedImage] = None
        self.processed_pixbuf: Optional[Gdk.Pixbuf] = None
        self.image_ready = False
        self.show_close_confirmation = False

        self.export_manager: ExportManager = ExportManager(self, temp_dir)
        self.import_manager: ImportManager = ImportManager(self, temp_dir, self.app)

        if build_type == "debug":
            self.add_css_class("devel")

        self.processor: ImageProcessor = ImageProcessor()
        self._setup_actions()
        self._setup_image_stack()
        self._setup_sidebar()
        self._setup()

        self.connect("close-request", self._on_close_request)

        if self.file_path:
            self.import_manager.load_from_file(self.file_path)
        if self.start_screenshot:
            self.import_manager.load_as_screenshot(self.start_screenshot)

    def _setup_actions(self) -> None:
        self.create_action("shortcuts", self._on_shortcuts_activated)
        self.create_action("about", self._on_about_activated)
        self.create_action("quit", lambda *_: self.close(),  ['<primary>q', '<primary>w'])
        self.create_action("shortcuts", self._on_shortcuts_activated,  ['<primary>question'])

        self.create_action("open", lambda *_: self.import_manager.open_file_dialog(), ["<Primary>o"])
        self.create_action("create-source-image", lambda *_: self.import_manager.generate_from_source_code(), ["<Primary>p"])
        self.create_action("load-drop", self.import_manager._on_drop_action, vt="s")
        self.create_action("paste", lambda *_: self.import_manager.load_from_clipboard(), ["<Primary>v"])
        self.create_action("screenshot", lambda *_: self.import_manager.take_screenshot(), ["<Primary>a"])
        self.create_action("open-path", lambda action, param: self.import_manager.load_from_file(param.get_string()), vt="s")

        self.create_action(
            "tool-option-changed",
            lambda action, param: setattr(self.drawing_overlay, "options", ToolOption.deserialize(param.get_string())),
            vt="s",
        )
        self.create_action("del-selected", lambda *_: self.drawing_overlay.remove_selected_action(), ["<Primary>x", "Delete"])

        self.create_action("open-folder", lambda *_: self.open_loaded_image_folder(), enabled=False)
        self.create_action("save", lambda *_: self.export_manager.save_to_file(), ["<Primary>s"], enabled=False)
        self.create_action("copy", lambda *_: self.export_manager.copy_to_clipboard(), ["<Primary>c"], enabled=False)
        self.create_action("command", lambda *_: self._run_custom_command(), ["<Primary>m"], enabled=False)

        self.create_action("aspect-ratio-crop", lambda _, variant: self.image_bin.set_aspect_ratio(variant.get_double()), vt="d")
        self.create_action("crop", lambda *_: self.image_bin.on_toggle_crop(), ["<Primary>r"])
        self.create_action("reset-crop", lambda *_: self.image_bin.reset_crop_selection(), ["<Primary><Shift>r"])


        self.create_action("zoom-in", lambda *_: self.image_bin.zoom_in(), ["<Control>plus", "<Control>equal", "<Control>KP_Add"])
        self.create_action("zoom-out", lambda *_: self.image_bin.zoom_out(), ["<Control>minus", "<Control>KP_Subtract"])
        self.create_action("reset-zoom", lambda *_: self.image_bin.reset_zoom(), ["<Control>0", "<Control>KP_0"])

        for mode in DrawingMode:
            self.create_action(
                f"set-drawing-mode-{mode.name.lower()}",
                lambda *_, m=mode: self.sidebar.set_drawing_mode(m),
                mode.shortcuts,
                disable_on_entry_focus=True
            )

        self.create_action("undo", lambda *_: self.drawing_overlay.undo(), ["<Primary>z"])
        self.create_action("redo", lambda *_: self.drawing_overlay.redo(), ["<Primary><Shift>z"])
        self.create_action("clear", lambda *_: self.drawing_overlay.clear_drawing())
        self.create_action("draw-mode", lambda action, param: self.drawing_overlay.set_drawing_mode(DrawingMode(param.get_string())), vt="s")


        self.create_action("delete-screenshots", lambda *_: self._create_delete_screenshots_dialog(), enabled=False)

        self.create_action("preferences", self._on_preferences_activated, ['<primary>comma'])

        self.create_action("set-screenshot-folder",  lambda action, param: self.set_screenshot_subfolder(param.get_string()), vt="s")


    """
    Setup Methods
    """

    def _setup_image_stack(self) -> None:
        self.image_bin = ImageStack()
        self.image_bin.connect("crop-toggled", self._on_crop_toggled)
        self.image_stack = self.image_bin.stack
        self.picture = self.image_bin.picture
        self.drawing_overlay = self.image_bin.drawing_overlay

    def _setup_sidebar(self) -> None:
        self.sidebar = ImageSidebar(
            on_image_options_changed=self.on_image_options_changed,
        )

        self.sidebar.set_size_request(self.SIDEBAR_WIDTH, -1)
        self.sidebar.set_visible(False)

        self.share_button = self.sidebar.share_button

    def _setup(self) -> None:
        self.split_view.set_sidebar(self.sidebar)
        self.split_view.set_content(self.image_bin)
        self.image_stack.set_hexpand(True)
        self.sidebar.set_hexpand(False)

    """
    Shutdown
    """
    def _on_close_request(self, window) -> bool:
        exit_method = Settings().exit_method

        if exit_method == "confirm" and self.show_close_confirmation:
            confirm_dialog = ConfirmCloseDialog(self)
            confirm_dialog.show_dialog(self._on_confirm_close_ok, self._on_confirm_close_copy)
            return True
        elif exit_method == "copy":
            self._on_confirm_close_copy()
            return True
        else:  # "none"
            self._on_confirm_close_ok()
            return True

    def _finalize_close(self, copy: bool) -> None:
        if Settings().delete_screenshots_on_close:
            self.import_manager.delete_screenshots()

        if not copy:
            self.hide()

        save = not Settings().delete_screenshots_on_close
        if self.image_ready:
            self.export_manager.close_handler(
                copy=copy,
                save=save,
                callback=self._on_close_finished
            )
        else:
            self._on_close_finished()

    def _on_close_finished(self) -> None:
        self.destroy()

    def _on_confirm_close_ok(self) -> None:
        self._finalize_close(copy=False)

    def _on_confirm_close_copy(self) -> None:
        self._finalize_close(copy=True)

    """
    Callbacks
    """

    def on_image_options_changed(self, options: ImageOptions):
        self.processor.background = options.background
        self.processor.padding = options.padding
        self.processor.corner_radius = options.corner_radius

        try:
            ratio: Optional[float] = parse_aspect_ratio(options.aspect_ratio)
            if ratio is None:
                self.processor.aspect_ratio = None
            else:
                if not check_aspect_ratio_bounds(ratio):
                    raise ValueError(f"Aspect ratio must be between 0.2 and 5 (got {ratio})")
                self.processor.aspect_ratio = ratio
        except Exception as e:
            print(f"Invalid aspect ratio: {options.aspect_ratio} ({e})")

        self.processor.shadow_strength = options.shadow_strength
        self.processor.auto_balance = options.auto_balance
        self.processor.rotation = options.rotation

        self._trigger_processing()

    def _on_about_activated(self, action: Gio.SimpleAction, param: GObject.ParamSpec) -> None:
        about = AboutDialog(version=self.version)
        about.show(self)

    def _on_shortcuts_activated(self, action: Gio.SimpleAction, param: GObject.ParamSpec) -> None:
        shortcuts = ShortcutsDialog(parent=self)
        shortcuts.create()
        shortcuts.dialog.connect("close-request", self._on_shortcuts_closed)
        shortcuts.dialog.present()

    def _on_shortcuts_closed(self, dialog: Adw.Window) -> bool:
        dialog.hide()
        return True

    """
    Public Methods
    """

    def create_action(
        self,
        name: str,
        callback: Callable[..., Any],
        shortcuts: Optional[list[str]] = None,
        enabled: bool = True,
        vt: Optional[str] = None,
        disable_on_entry_focus: bool = False
    ) -> None:
        variant_type = GLib.VariantType.new(vt) if vt is not None else None
        action: Gio.SimpleAction = Gio.SimpleAction.new(name, variant_type)

        action.connect("activate", callback)
        action.set_enabled(enabled)
        self.add_action(action)

        if shortcuts:
            self.app.set_accels_for_action(f"win.{name}", shortcuts)
            if disable_on_entry_focus:
                if not hasattr(self, '_entry_disabled_actions'):
                    self._entry_disabled_actions = {}
                self._entry_disabled_actions[name] = shortcuts

    def _setup_accelerator_handling(self) -> None:
        if not hasattr(self, '_entry_disabled_actions'):
            self._entry_disabled_actions = {}

        def on_focus_changed(window, pspec):
            widget = self.get_focus()
            is_editable = False
            if widget:
                if isinstance(widget, (Gtk.Entry, Gtk.TextView, Gtk.SearchEntry)):
                    is_editable = True
                elif type(widget).__name__ == 'Text':
                    is_editable = widget.get_editable()

            if is_editable:
                for action_name in self._entry_disabled_actions:
                    self.app.set_accels_for_action(f"win.{action_name}", [])
            else:
                for action_name, shortcuts in self._entry_disabled_actions.items():
                    self.app.set_accels_for_action(f"win.{action_name}", shortcuts)

        self.connect("notify::focus-widget", on_focus_changed)

    def show(self) -> None:
        self.present()

    def process_image(self, callback=None) -> None:
        if not self.image:
            return
        def worker():
            self._process_in_background(callback)
        threading.Thread(target=worker, daemon=True).start()

    """
    Private Methods
    """

    def set_image(self, image: LoadedImage, copy_after_processing=False):
        self.image = image
        self.drawing_overlay.clear_drawing()
        self._update_sidebar_file_info(image)
        self.show_close_confirmation = True
        self.toolbar_view.set_top_bar_style(Adw.ToolbarStyle.RAISED)
        self.image_stack.get_style_context().add_class("view")
        self._show_loading_state()

        def after_process():
            if copy_after_processing:
                self.export_manager.copy_to_clipboard(silent=True)
            self._set_export_ready(True)
            self.lookup_action("open-folder").set_enabled(image.has_proper_folder())

        self.process_image(callback=after_process)


    def _show_loading_state(self) -> None:
        self.main_stack.set_visible_child_name("main")
        self.welcome_content.recent_picker.set_visible(False)
        self.image_stack.set_visible_child_name(self.PAGE_LOADING)

    def _hide_loading_state(self) -> None:
        self.image_stack.set_visible_child_name(self.PAGE_IMAGE)

    def _update_sidebar_file_info(self, image: LoadedImage) -> None:
        self.sidebar.filename_row.set_subtitle(image.get_proper_name())
        self.sidebar.location_row.set_subtitle(image.get_proper_folder())
        self.sidebar.set_visible(True)

    def _trigger_processing(self) -> None:
        if self.image:
            self.process_image()

    def _process_in_background(self, callback=None) -> None:
        try:
            if self.image is not None:
                self.processor.set_image(self.image)
                pixbuf, true_width, true_height = self.processor.process()
                self._update_processed_image_size(true_width, true_height)
                self.processed_pixbuf = pixbuf
            else:
                print("No image path set for processing.")

            def finish():
                self._update_image_preview()
                if callback:
                    callback()
                return False

            GLib.idle_add(finish, priority=GLib.PRIORITY_DEFAULT)

        except Exception as e:
            print(f"Error processing image: {e}")

    def _update_image_preview(self) -> bool:
        if self.processed_pixbuf:
            paintable: Gdk.Paintable = Gdk.Texture.new_for_pixbuf(self.processed_pixbuf)
            self.picture.set_paintable(paintable)
            self._hide_loading_state()
        return False

    def _update_processed_image_size(self, width, height) -> None:
        size_str: str = f"{width}×{height}"
        self.sidebar.processed_size_row.set_subtitle(size_str)


    def _show_notification(self, message: str,action_label: str | None = None,action_callback: Callable[[], None] | None = None) -> None:
        if self.toast_overlay:
            toast = Adw.Toast.new(message)
            if action_label and action_callback:
                toast.set_button_label(action_label)
                toast.connect("button-clicked", lambda *_: action_callback())
            self.toast_overlay.add_toast(toast)

    def _set_loading_state(self, is_loading: bool) -> None:
        if is_loading:
            self._show_loading_state()
        else:
            child: str = getattr(self, "_previous_stack_child", self.PAGE_IMAGE)
            self.image_stack.set_visible_child_name(child)

    def _set_export_ready(self, enabled: bool) -> None:
        self.image_ready = True
        for action_name in ["save", "copy"]:
            action = self.lookup_action(action_name)
            if action:
                action.set_enabled(enabled)
        self.update_command_ready()

    def open_loaded_image_folder(self):
        folder_uri = GLib.filename_to_uri(self.image.get_folder_path())
        try:
            Gio.AppInfo.launch_default_for_uri(folder_uri, None)
        except Exception as e:
            print("Failed to open folder:", e)

    def update_command_ready(self) -> None:
        action = self.lookup_action('command')
        if action:
            action.set_enabled(self.image_ready)
            self.share_button.set_visible(bool(Settings().custom_export_command.strip()))

    def _create_delete_screenshots_dialog(self) -> None:
        dialog = DeleteScreenshotsDialog(self)
        dialog.show(
            self.import_manager.get_screenshot_uris(),
            self.import_manager.delete_screenshots,
            self._show_notification
        )

    def _on_preferences_activated(self, action: Gio.SimpleAction, param) -> None:
        preferences_window = PreferencesWindow(self)
        preferences_window.present(self)

    def set_screenshot_subfolder(self, subfolder) -> None:
        Settings().screenshot_subfolder = subfolder
        self.welcome_content.refresh_recent_picker()

    def _on_crop_toggled(self, image_stack: ImageStack, enabled: bool) -> None:
        self.split_view.set_show_sidebar(not enabled)


    def _run_custom_command(self) -> None:
        if Settings().show_export_confirm_dialog:
            provider_name = Settings().provider_name

            dialog = Adw.AlertDialog.new(
                heading=_("Confirm Upload"),
                body=_(f"Are you sure you want to upload this image to {provider_name}?")
            )
            dialog.add_response("cancel", _("Cancel"))
            dialog.add_response("confirm", _("Upload"))
            dialog.set_default_response("cancel")
            dialog.set_response_appearance("confirm", Adw.ResponseAppearance.SUGGESTED)

            dialog.connect("response", lambda dialog, response_id:
                          self.export_manager.run_custom_command() if response_id == "confirm" else None)

            dialog.present(self.get_root())
        else:
            self.export_manager.run_custom_command()
