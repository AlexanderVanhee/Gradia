# Copyright (C) 2026 Alexander Vanhee
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

from typing import Optional
from gi.repository import Adw, Gdk, GdkPixbuf, Gtk
from gradia.backend.logger import Logger

logging = Logger()


class PinWindow(Adw.ApplicationWindow):
    __gtype_name__ = "PinWindow"

    def __init__(self, application: Adw.Application, file_path: Optional[str] = None):
        super().__init__(application=application)
        self.file_path = file_path
        self.set_resizable(False)
        self.set_size_request(20, 20)
        self._build_ui()
        self._load_image()

    def _build_ui(self):
        self._picture = Gtk.Picture(
            can_shrink=True,
            keep_aspect_ratio=True,
            hexpand=True,
            vexpand=True,
        )

        header = Adw.HeaderBar()
        header.set_show_title(False)
        header.add_css_class("header-osd")

        toolbar_view = Adw.ToolbarView()
        toolbar_view.set_extend_content_to_top_edge(True)
        toolbar_view.add_top_bar(header)
        toolbar_view.set_content(self._picture)

        handle = Gtk.WindowHandle()
        handle.set_child(toolbar_view)

        self.set_content(handle)
        self._setup_hover_animation()

    def _setup_hover_animation(self):
        self.set_opacity(1.0)

        self._fade_in = Adw.TimedAnimation.new(
            self,
            1.0,
            0.25,
            200,
            Adw.PropertyAnimationTarget.new(self, "opacity"),
        )
        self._fade_in.set_easing(Adw.Easing.EASE_OUT_CUBIC)

        self._fade_out = Adw.TimedAnimation.new(
            self,
            0.25,
            1.0,
            350,
            Adw.PropertyAnimationTarget.new(self, "opacity"),
        )
        self._fade_out.set_easing(Adw.Easing.EASE_IN_CUBIC)

        motion = Gtk.EventControllerMotion()
        motion.connect("enter", self._on_enter)
        motion.connect("leave", self._on_leave)
        self._picture.add_controller(motion)

    def _on_enter(self, controller, x, y):
        self._fade_out.pause()
        self._fade_in.play()

    def _on_leave(self, controller):
        self._fade_in.pause()
        self._fade_out.play()

    def _load_image(self):
        if not self.file_path:
            logging.warning("PinWindow opened with no file path.")
            return

        pixbuf = GdkPixbuf.Pixbuf.new_from_file(self.file_path)
        img_w = pixbuf.get_width()
        img_h = pixbuf.get_height()

        display = Gdk.Display.get_default()
        monitor = display.get_monitors().get_item(0)
        geometry = monitor.get_geometry()
        max_w = int(geometry.width * 0.5)
        max_h = int(geometry.height * 0.5)

        scale = min(max_w / img_w, max_h / img_h, 1.0)
        final_w = int(img_w * scale)
        final_h = int(img_h * scale)

        self.set_default_size(final_w, final_h)
        self._picture.set_pixbuf(pixbuf)
        print("GRADIA_PIN_READY", flush=True)
