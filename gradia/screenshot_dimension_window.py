# screenshot_dimension_window.py
#
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

import gi
import os
class ScreenshotResolutionHandler:
    def __init__(self):
        gi.require_version('Gtk', '4.0')
        gi.require_version('Adw', '1')
        from gi.repository import Gtk, Gdk, GdkPixbuf, Adw, Gio, GLib
        self.Gtk = Gtk
        self.Gdk = Gdk
        self.GdkPixbuf = GdkPixbuf
        self.Adw = Adw
        self.Gio = Gio
        self.GLib = GLib

    def handle_screenshot_resolution(self, screenshot_path: str) -> bool:
        try:
            resolution = self._get_image_resolution(screenshot_path)
            if not resolution:
                print("Failed to get screenshot resolution")
                return False

            app = self.Adw.Application(application_id="be.alexandervanhee.gradia.screenshot")
            app.connect("activate", lambda app: self._show_resolution_window(app, resolution, screenshot_path))
            app.run([])
            return True
        except Exception as e:
            print(f"Failed to handle screenshot resolution: {e}")
            return False

    def _get_image_resolution(self, image_path: str) -> tuple[int, int] | None:
        try:
            pixbuf = self.GdkPixbuf.Pixbuf.new_from_file(image_path)
            return (pixbuf.get_width(), pixbuf.get_height())
        except Exception as e:
            print(f"Failed to get image resolution: {e}")
            return None

    def _show_resolution_window(self, app, resolution: tuple[int, int], screenshot_path: str):
        width, height = resolution
        window = self.Adw.ApplicationWindow(application=app, title="Gradia - " + _("Screenshot Dimensions"))
        window.set_default_size(300, 150)
        window.set_resizable(False)
        window.set_modal(True)

        toolbar_view = self.Adw.ToolbarView()
        header_bar = self.Adw.HeaderBar()
        title = self.Adw.WindowTitle(title=_("Screenshot Dimensions"))
        header_bar.set_title_widget(title)
        toolbar_view.add_top_bar(header_bar)

        main_box = self.Gtk.Box(orientation=self.Gtk.Orientation.VERTICAL, spacing=24)
        main_box.set_vexpand(True)
        main_box.set_valign(self.Gtk.Align.CENTER)
        main_box.set_margin_start(24)
        main_box.set_margin_end(24)

        label = self.Gtk.Label()
        label.set_markup(f"{width} × {height}")
        label.add_css_class("title-1")
        label.set_halign(self.Gtk.Align.CENTER)
        main_box.append(label)

        copy_button = self.Gtk.Button(label="Copy & Close")
        copy_button.add_css_class("suggested-action")
        copy_button.add_css_class("pill")
        copy_button.set_halign(self.Gtk.Align.CENTER)
        copy_button.connect("clicked", lambda btn: self._on_copy_clicked(resolution, screenshot_path, app))
        main_box.append(copy_button)

        toolbar_view.set_content(main_box)
        window.set_content(toolbar_view)
        window.present()

    def _on_copy_clicked(self, resolution: tuple[int, int], screenshot_path: str, app):
        self._copy_resolution_to_clipboard(resolution)
        self.GLib.timeout_add(25, lambda: self._cleanup_and_quit(screenshot_path, app))

    def _cleanup_and_quit(self, screenshot_path: str, app):
        self._cleanup_screenshot(screenshot_path)
        app.quit()
        return False

    def _copy_resolution_to_clipboard(self, resolution: tuple[int, int]):
        try:
            width, height = resolution
            resolution_text = f"{width}x{height}"
            display = self.Gdk.Display.get_default()
            if not display:
                return
            clipboard = display.get_clipboard()
            text_bytes = resolution_text.encode("utf-8")
            bytes_data = self.GLib.Bytes.new(text_bytes)
            content_provider = self.Gdk.ContentProvider.new_for_bytes("text/plain;charset=utf-8", bytes_data)
            clipboard.set_content(content_provider)
        except Exception as e:
            print(f"Failed to copy resolution to clipboard: {e}")

    def _cleanup_screenshot(self, screenshot_path: str):
        try:
            if os.path.exists(screenshot_path):
                file = self.Gio.File.new_for_path(screenshot_path)
                file.trash(None)
        except Exception as e:
            print(f"Failed to trash screenshot file: {e}")
