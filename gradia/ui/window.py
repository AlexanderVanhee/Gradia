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
from gradia.ui.image_loaders import ImportManager
from gradia.ui.image_sidebar import ImageSidebar
from gradia.ui.image_stack import ImageStack
from gradia.ui.ui_parts import *
from gradia.ui.welcome_page import WelcomePage
from gradia.utils.aspect_ratio import *
from gradia.ui.preferences_window import PreferencesWindow
from gradia.backend.settings import Settings
from gradia.constants import rootdir  # pyright: ignore
from gradia.ui.dialog.delete_screenshots_dialog import DeleteScreenshotsDialog
from gradia.ui.dialog.confirm_close_dialog import ConfirmCloseDialog

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

        self.app: Adw.Application = kwargs['application']
        self.temp_dir: str = temp_dir
        self.version: str = version
        self.start_screenshot = start_screenshot
        self.file_path: Optional[str] = file_path
        self.image_path: Optional[str] = None
        self.processed_pixbuf: Optional[Gdk.Pixbuf] = None
        self.image_ready = False
        self.show_close_confirmation = False

        self.export_manager: ExportManager = ExportManager(self, temp_dir)
        self.import_manager: ImportManager = ImportManager(self, temp_dir, self.app)

        self.background_selector: BackgroundSelector = BackgroundSelector(
            callback=self._on_background_changed,
            window=self
        )

        self.processor: ImageProcessor = ImageProcessor(
            padding=5,
            background=self.background_selector.get_current_background()
        )
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

        self.create_action("save", lambda *_: self.export_manager.save_to_file(), ["<Primary>s"], enabled=False)
        self.create_action("copy", lambda *_: self.export_manager.copy_to_clipboard(), ["<Primary>c"], enabled=False)
        self.create_action("command", lambda *_: self._run_custom_command(), ["<Primary>m"], enabled=False)

        self.create_action("aspect-ratio-crop",lambda _, variant: self.image_bin.set_aspect_ratio(variant.get_double()), vt="d")
        self.create_action("crop", lambda *_: self.image_bin.on_toggle_crop(), ["<Primary>r"])
        self.create_action("reset-crop", lambda *_: self.image_bin.reset_crop_selection(), ["<Primary><Shift>r"])

        self.create_action("undo", lambda *_: self.drawing_overlay.undo(), ["<Primary>z"])
        self.create_action("redo", lambda *_: self.drawing_overlay.redo(), ["<Primary><Shift>z"])
        self.create_action("clear", lambda *_: self.drawing_overlay.clear_drawing())
        self.create_action("draw-mode", lambda action, param: self.drawing_overlay.set_drawing_mode(DrawingMode(param.get_string())), vt="s")

        self.create_action("pen-color", lambda action, param: self._set_pen_color_from_string(param.get_string()), vt="s")
        self.create_action("fill-color", lambda action, param: self._set_fill_color_from_string(param.get_string()), vt="s")
        self.create_action("outline-color", lambda action, param: self._set_outline_color_from_string(param.get_string()), vt="s")
        self.create_action("highlighter-color", lambda action, param: self._set_highlighter_color_from_string(param.get_string()), vt="s")
        self.create_action("del-selected", lambda *_: self.drawing_overlay.remove_selected_action(), ["<Primary>x", "Delete"])
        self.create_action("font", lambda action, param: self.drawing_overlay.settings.set_font_family(param.get_string()), vt="s")
        self.create_action("pen-size", lambda action, param: self.drawing_overlay.settings.set_pen_size(param.get_double()), vt="d")
        self.create_action("highlighter-size", lambda action, param: self.drawing_overlay.settings.set_highlighter_size(param.get_double()), vt="d")
        self.create_action("number-radius", lambda action, param: self.drawing_overlay.settings.set_number_radius(param.get_double()), vt="d")

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
            background_selector_widget=self.background_selector,
            on_padding_changed=self.on_padding_changed,
            on_corner_radius_changed=self.on_corner_radius_changed,
            on_aspect_ratio_changed=self.on_aspect_ratio_changed,
            on_shadow_strength_changed=self.on_shadow_strength_changed,
            on_auto_balance_changed=self.on_auto_balance_changed,
            on_rotation_changed=self.on_rotation_changed
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
        if Settings().show_close_confirm_dialog and self.show_close_confirmation:
            confirm_dialog = ConfirmCloseDialog(self)
            confirm_dialog.show_dialog(self._on_confirm_close_ok)
            return True
        else:
            self._on_confirm_close_ok()
            return True

    def _on_confirm_close_ok(self) -> None:
        if Settings().delete_screenshots_on_close:
            self.import_manager.delete_screenshots()
        self.destroy()

    """
    Callbacks
    """

    def _on_background_changed(self, updated_background: Background) -> None:
        if (getattr(self, "processor", None)):
            self.processor.background = updated_background
            self._trigger_processing()

    def on_padding_changed(self, value: int) -> None:
        setattr(self.processor, "padding", value)
        self._trigger_processing()

    def on_corner_radius_changed(self, value: int) -> None:
        setattr(self.processor, "corner_radius", value)
        self._trigger_processing()

    def on_aspect_ratio_changed(self, text: str) -> None:
        try:
            ratio: Optional[float] = parse_aspect_ratio(text)
            if ratio is None:
                self.processor.aspect_ratio = None
                self._trigger_processing()
                return

            if not check_aspect_ratio_bounds(ratio):
                raise ValueError(f"Aspect ratio must be between 0.2 and 5 (got {ratio})")

            self.processor.aspect_ratio = ratio
            self._trigger_processing()

        except Exception as e:
            print(f"Invalid aspect ratio: {text} ({e})")

    def on_shadow_strength_changed(self, value: int) -> None:
        self.processor.shadow_strength = value
        self._trigger_processing()

    def on_auto_balance_changed(self, value: bool) -> None:
        self.processor.auto_balance = value
        self._trigger_processing()

    def on_rotation_changed(self, value: int) -> None:
        self.processor.rotation = value
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
        vt: Optional[str] = None
    ) -> None:
        variant_type = GLib.VariantType.new(vt) if vt is not None else None
        action: Gio.SimpleAction = Gio.SimpleAction.new(name, variant_type)
        action.connect("activate", callback)
        action.set_enabled(enabled)
        self.add_action(action)

        if shortcuts:
            self.app.set_accels_for_action(f"win.{name}", shortcuts)

    def show(self) -> None:
        self.present()

    def process_image(self) -> None:
        if not self.image_path:
            return

        threading.Thread(target=self._process_in_background, daemon=True).start()

    """
    Private Methods
    """

    def _update_and_process(
        self,
        obj: Any,
        attr: str,
        transform: Callable[[Any], Any] = lambda x: x,
        assign_to: Optional[str] = None
    ) -> Callable[[Any], None]:
        def handler(widget: Any) -> None:
            value = transform(widget)
            setattr(obj, attr, value)

            if assign_to:
                setattr(self.processor, assign_to, obj)

            self._trigger_processing()

        return handler

    def _start_processing(self) -> None:
        self.toolbar_view.set_top_bar_style(Adw.ToolbarStyle.RAISED)

        self.image_stack.get_style_context().add_class("view")
        self._show_loading_state()
        self.process_image()
        self._set_export_ready(True)

    def _show_loading_state(self) -> None:
        self.main_stack.set_visible_child_name("main")
        self.welcome_content.recent_picker.set_visible(False)
        self.image_stack.set_visible_child_name(self.PAGE_LOADING)

    def _hide_loading_state(self) -> None:
        self.image_stack.set_visible_child_name(self.PAGE_IMAGE)

    def _update_sidebar_file_info(self, filename: str, location: str) -> None:
        self.sidebar.filename_row.set_subtitle(filename)
        self.sidebar.location_row.set_subtitle(location)
        self.sidebar.set_visible(True)

    def _parse_rgba(self, color_string: str) -> list[float]:
        return list(map(float, color_string.split(',')))

    def _set_pen_color_from_string(self, color_string: str) -> None:
        self.drawing_overlay.settings.set_pen_color(*self._parse_rgba(color_string))

    def _set_fill_color_from_string(self, color_string: str) -> None:
        self.drawing_overlay.settings.set_fill_color(*self._parse_rgba(color_string))

    def _set_outline_color_from_string(self, color_string: str) -> None:
        self.drawing_overlay.settings.set_outline_color(*self._parse_rgba(color_string))

    def _set_highlighter_color_from_string(self, color_string: str) -> None:
        self.drawing_overlay.settings.set_highlighter_color(*self._parse_rgba(color_string))

    def _trigger_processing(self) -> None:
        if self.image_path:
            self.process_image()

    def _process_in_background(self) -> None:
        try:
            if self.image_path is not None:
                self.processor.set_image_path(self.image_path)
                pixbuf, true_width, true_height = self.processor.process()
                self._update_processed_image_size(true_width, true_height)
                self.processed_pixbuf = pixbuf

            else:
                print("No image path set for processing.")

            GLib.idle_add(self._update_image_preview, priority=GLib.PRIORITY_DEFAULT)  # pyright: ignore
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
        preferences_window.present()

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
