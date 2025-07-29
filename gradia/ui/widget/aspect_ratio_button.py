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

from typing import Any
from gi.repository import Gtk, Gio, GLib, GObject

class AspectRatioButton(Gtk.Button):
    __gtype_name__ = "GradiaAspectRatioButton"

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self.set_tooltip_text(_("Aspect Ratio"))
        self.add_css_class("osd")
        self.add_css_class("circular")

        self.default_icon_name = "aspect-ratio-symbolic"
        self.icon = Gtk.Image.new_from_icon_name(self.default_icon_name)
        self.set_child(self.icon)

        self.popover = Gtk.Popover()
        self.popover.set_parent(self)
        self.popover.set_position(Gtk.PositionType.TOP)

        self.aspect_ratios = [
            (_("Free"), "aspect-ratio-free-symbolic", 0.0),
            (_("Square"), "aspect-ratio-square-symbolic", 1.0),
            ("4:3", "aspect-ratio-4to3-symbolic", 4.0 / 3.0),
            ("3:2", "aspect-ratio-3to2-symbolic", 3.0 / 2.0),
            ("5:4", "aspect-ratio-5to4-symbolic", 5.0 / 4.0),
            ("16:9", "aspect-ratio-16to9-symbolic", 16.0 / 9.0),
        ]

        self._setup_popover_content()
        self.connect("clicked", self._on_button_clicked)

    def _setup_popover_content(self) -> None:
        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        vbox.set_margin_top(6)
        vbox.set_margin_bottom(6)
        vbox.set_margin_start(6)
        vbox.set_margin_end(6)

        for label_text, icon_name, ratio_value in self.aspect_ratios:
            button = Gtk.Button()
            button.set_has_frame(False)

            hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
            hbox.set_halign(Gtk.Align.START)

            icon = Gtk.Image.new_from_icon_name(icon_name)
            icon.set_icon_size(Gtk.IconSize.NORMAL)
            hbox.append(icon)

            label = Gtk.Label(label=label_text)
            label.set_halign(Gtk.Align.START)
            hbox.append(label)

            button.set_child(hbox)
            button.connect("clicked", self._on_aspect_ratio_selected, ratio_value, icon_name)
            vbox.append(button)

        self.popover.set_child(vbox)

    def _on_button_clicked(self, button: Gtk.Button) -> None:
        self.popover.popup()

    def _on_aspect_ratio_selected(self, button: Gtk.Button, ratio_value: float, icon_name: str) -> None:
        self.icon.set_from_icon_name(icon_name)
        app = self.get_root().get_application()
        if app and hasattr(app, 'activate_action'):
            variant = GLib.Variant('d', ratio_value)
            app.activate_action('aspect-ratio-crop', variant)

        self.popover.popdown()

    def do_dispose(self) -> None:
        if self.popover:
            self.popover.unparent()
        super().do_dispose()

