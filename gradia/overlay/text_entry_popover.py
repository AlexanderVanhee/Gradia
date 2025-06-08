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

from gi.repository import Gtk, Gdk

class TextEntryPopover(Gtk.Popover):
    def __init__(self, parent, on_text_activate, on_text_changed, on_font_size_changed, font_size=14, initial_text=""):
        super().__init__()
        self.set_parent(parent)
        self.set_position(Gtk.PositionType.BOTTOM)

        hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=0)
        hbox.add_css_class("linked")

        self.entry = Gtk.Entry()
        self.entry.set_placeholder_text(_("Enter text…"))
        self.entry.set_width_chars(12)
        self.entry.connect("activate", on_text_activate)
        self.entry.connect("changed", on_text_changed)

        # Set initial text if provided
        if initial_text:
            self.entry.set_text(initial_text)
            self.entry.select_region(0, -1)

        adjustment = Gtk.Adjustment(value=font_size, lower=8.0, upper=72.0, step_increment=4.0, page_increment=4.0)
        self.spin = Gtk.SpinButton()
        self.spin.set_adjustment(adjustment)
        self.spin.set_digits(0)
        self.spin.set_size_request(60, -1)
        self.spin.connect("value-changed", on_font_size_changed)

        hbox.append(self.entry)
        hbox.append(self.spin)
        self.set_child(hbox)

    def popup_at_widget_coords(self, widget, x, y):
        allocation = widget.get_allocation()
        rect = Gdk.Rectangle()
        rect.x = allocation.x + int(x)
        rect.y = allocation.y + int(y)
        rect.width = 1
        rect.height = 1
        self.set_pointing_to(rect)
        self.popup()
        self.entry.grab_focus()
