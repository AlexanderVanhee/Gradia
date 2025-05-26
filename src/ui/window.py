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
import threading

from gi.repository import Gtk, Gio, Adw, Gdk, GLib
from .image_processor import ImageProcessor
from .gradient import GradientSelector, GradientBackground
from .text import TextSelector
from .ui_parts import *
from .clipboard import *
from .misc import *
from .image_loaders import ImportManager
from .image_exporters import ExportManager

class GradientWindow:
    DEFAULT_WINDOW_WIDTH = 900
    DEFAULT_WINDOW_HEIGHT = 600
    DEFAULT_PANED_POSITION = 650
    SIDEBAR_WIDTH = 200

    # Stack page names
    PAGE_CONTENT = "content"
    PAGE_IMAGE = "image"
    PAGE_LOADING = "loading"

    # Temp file names
    TEMP_PROCESSED_FILENAME = "processed.png"

    def __init__(self, app, temp_dir, version):
        self.app = app
        self.temp_dir = temp_dir
        self.version = version
        self.image_path = None
        self.processed_path = None
        self.processed_pixbuf = None


        # Initialize import and export managers
        self.export_manager = ExportManager(self, temp_dir)
        self.import_manager = ImportManager(self, temp_dir)

        # Initialize gradient selector with callback
        self.gradient_selector = GradientSelector(
            gradient=GradientBackground(),
            callback=self._on_gradient_changed
        )
        self.text_selector = TextSelector(
            callback=self._on_text_changed
        )

        self.processor = ImageProcessor(padding=5, background=GradientBackground())

        # UI elements (populated during build_ui)
        self.win = None
        self.picture = None
        self.spinner = None
        self.image_stack = None
        self.toolbar_view = None
        self.sidebar = None
        self.sidebar_info = None
        self.main_paned = None
        self._previous_stack_child = self.PAGE_CONTENT

        self.create_action("shortcuts", self._on_shortcuts_activated)
        self.create_action("about", self._on_about_activated)
        self.create_action('quit', lambda *_: self.app.quit(), ['<primary>q'])
        self.create_action("shortcuts", self._on_shortcuts_activated,  ['<primary>question'])

        self.create_action("open", lambda *_: self.import_manager.open_file_dialog(), ["<Primary>o"])
        self.create_action("load-drop", self.import_manager._on_drop_action)
        self.create_action("paste", lambda *_: self.import_manager.load_from_clipboard(), ["<Primary>v"])

        self.create_action("save", lambda *_: self.export_manager.save_to_file(), ["<Primary>s"], enabled=False)
        self.create_action("copy", lambda *_: self.export_manager.copy_to_clipboard(), ["<Primary>c"], enabled=False)

        self.create_action("quit", lambda *_: self.win.close(), ["<Primary>q"])

    def create_action(self, name, callback, shortcuts=None, enabled=True):
        action = Gio.SimpleAction.new(name, None)
        action.connect("activate", callback)
        action.set_enabled(enabled)
        self.app.add_action(action)
        if shortcuts:
            self.app.set_accels_for_action(f"app.{name}", shortcuts)

    def _update_and_process(self, obj, attr, transform=lambda x: x, assign_to=None):
        def handler(widget):
            value = transform(widget)
            setattr(obj, attr, value)
            if assign_to:
                setattr(self.processor, assign_to, obj)
            self._trigger_processing()
        return handler

    def build_ui(self):
        self._setup_window()
        self._setup_toolbar()
        self._setup_header_bar()
        self._setup_image_stack()
        self._setup_sidebar()
        self._setup_main_layout()

    def _setup_window(self):
        self.win = Adw.ApplicationWindow(application=self.app)
        self.win.set_title("Gradia")
        self.win.set_default_size(self.DEFAULT_WINDOW_WIDTH, self.DEFAULT_WINDOW_HEIGHT)
        self.toast_overlay = Adw.ToastOverlay()
        self.win.set_content(self.toast_overlay)

    def _setup_toolbar(self):
        self.toolbar_view = Adw.ToolbarView()
        self.toolbar_view.set_top_bar_style(Adw.ToolbarStyle.FLAT)

    def _setup_header_bar(self):
        btn_refs = [None, None]
        header_bar = create_header_bar()
        self.toolbar_view.add_top_bar(header_bar)

    def _setup_image_stack(self):
        stack_info = create_image_stack()
        self.image_stack = stack_info[0]
        self.picture = stack_info[1]
        self.spinner = stack_info[2]

    def _setup_sidebar(self):
        self.sidebar_info = create_sidebar_ui(
            gradient_selector_widget=self.gradient_selector.widget,
            on_padding_changed=self.on_padding_changed,
            on_corner_radius_changed=self.on_corner_radius_changed,
            text_selector_widget=self.text_selector.widget,
            on_aspect_ratio_changed=self.on_aspect_ratio_changed,
            on_shadow_strength_changed=self.on_shadow_strength_changed,
        )
        self.sidebar = self.sidebar_info['sidebar']
        self.sidebar.set_size_request(self.SIDEBAR_WIDTH, -1)
        self.sidebar.set_visible(False)

    def _setup_main_layout(self):
        self.main_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=0)
        self.main_box.set_vexpand(True)

        self.main_box.append(self.image_stack)
        self.main_box.append(self.sidebar)

        self.image_stack.set_hexpand(True)
        self.sidebar.set_hexpand(False)
        self.sidebar.set_size_request(300, -1)

        self.toolbar_view.set_content(self.main_box)
        self.toast_overlay.set_child(self.toolbar_view)

        self.win.connect("notify::default-width", self._on_window_resize)
        self.win.connect("notify::default-height", self._on_window_resize)

    def _on_window_resize(self, *args):
        width = self.win.get_width()
        if width < 800:
            self.main_box.set_orientation(Gtk.Orientation.VERTICAL)
            self.sidebar.set_size_request(-1, 200)
        else:
            self.main_box.set_orientation(Gtk.Orientation.HORIZONTAL)
            self.sidebar.set_size_request(300, -1)

    def show(self):
        self.win.present()

    def _start_processing(self):
        self.toolbar_view.set_top_bar_style(Adw.ToolbarStyle.RAISED)
        self.image_stack.get_style_context().add_class("view")
        self._show_loading_state()
        self.process_image()
        self._set_save_and_toggle_(True)

    def _show_loading_state(self):
        self.image_stack.set_visible_child_name(self.PAGE_LOADING)
        self.spinner.start()

    def _hide_loading_state(self):
        self.spinner.stop()
        self.image_stack.set_visible_child_name(self.PAGE_IMAGE)

    def _update_sidebar_info(self, filename, location):
        """Update sidebar with file information"""
        self.sidebar_info['filename_row'].set_subtitle(filename)
        self.sidebar_info['location_row'].set_subtitle(location)
        self.sidebar.set_visible(True)

    def _on_gradient_changed(self, updated_gradient):
        self.processor.background = updated_gradient
        self._trigger_processing()

    def _on_text_changed(self, updated_text):
        self.processor.text = updated_text
        self._trigger_processing()

    def on_padding_changed(self, row: Adw.SpinRow):
        setattr(self.processor, "padding", int(row.get_value()))
        self._trigger_processing()

    def on_corner_radius_changed(self, row: Adw.SpinRow):
        setattr(self.processor, "corner_radius", int(row.get_value()))
        self._trigger_processing()

    def on_aspect_ratio_changed(self, entry):
        text = entry.get_text().strip()
        try:
            ratio = parse_aspect_ratio(text)
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

    def on_shadow_strength_changed(self, strength):
        self.processor.shadow_strength = strength.get_value()
        self._trigger_processing()

    def _trigger_processing(self):
        if self.image_path:
            self.process_image()

    def process_image(self):
        if not self.image_path:
            return

        # Run processing in background
        threading.Thread(target=self._process_in_background, daemon=True).start()

    def _process_in_background(self):
        try:
            self.processor.set_image_path(self.image_path)
            pixbuf = self.processor.process()
            self.processed_pixbuf = pixbuf
            self.processed_path = os.path.join(self.temp_dir, self.TEMP_PROCESSED_FILENAME)
            pixbuf.savev(self.processed_path, "png", [], [])

            # Schedule UI update on the main thread
            GLib.idle_add(self._update_image_preview, priority=GLib.PRIORITY_DEFAULT)
        except Exception as e:
            print(f"Error processing image: {e}")

    def _update_image_preview(self):
        if self.processed_pixbuf:
            # Create a Paintable from the pixbuf
            paintable = Gdk.Texture.new_for_pixbuf(self.processed_pixbuf)
            self.picture.set_paintable(paintable)
            self._update_processed_image_size()
            self._hide_loading_state()
        return False

    def _update_processed_image_size(self):
        try:
            if self.processed_pixbuf:
                width = self.processed_pixbuf.get_width()
                height = self.processed_pixbuf.get_height()
                size_str = f"{width}x{height}"
                self.sidebar_info['processed_size_row'].set_subtitle(size_str)
            else:
                self.sidebar_info['processed_size_row'].set_subtitle(_("Unknown"))
        except Exception as e:
            self.sidebar_info['processed_size_row'].set_subtitle(_("Error"))
            print(f"Error getting processed image size: {e}")

    def _show_notification(self, message):
        if self.toast_overlay:
            toast = Adw.Toast.new(message)
            self.toast_overlay.add_toast(toast)

    def _set_loading_state(self, is_loading):
        if is_loading:
            self._show_loading_state()
        else:
            child = getattr(self, "_previous_stack_child", self.PAGE_CONTENT)
            self.image_stack.set_visible_child_name(child)
            self.spinner.stop()

    def _on_about_activated(self, action, param):
        about = create_about_dialog(version=self.version)
        about.present(self.win)

    def _set_save_and_toggle_(self, enabled: bool):
        app = self.app
        for action_name in ["save", "copy"]:
            action = app.lookup_action(action_name)
            if action:
                action.set_enabled(enabled)
