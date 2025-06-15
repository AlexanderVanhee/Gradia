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

from typing import Callable, Optional

from gi.repository import Gdk, Gtk

from gradia.constants import rootdir  # pyright: ignore

@Gtk.Template(resource_path=f"{rootdir}/ui/text_entry_popover.ui")
class TextEntryPopover(Gtk.Popover):
    __gtype_name__ = "GradiaTextEntryPopover"

    container: Gtk.Box = Gtk.Template.Child()

    entry: Gtk.Entry = Gtk.Template.Child()

    spin: Gtk.SpinButton = Gtk.Template.Child()
    size_adjustment: Gtk.Adjustment = Gtk.Template.Child()

    def __init__(
        self,
        parent: Gtk.Widget,
        on_text_activate: Callable,
        on_text_changed: Callable,
        on_font_size_changed: Callable,
        font_size: float | int = 14,
        initial_text: Optional[str] = "",
        **kwargs
    ) -> None:
        super().__init__(**kwargs)

        self.set_parent(parent)

        self.container.add_css_class("linked")

        self.entry.connect("activate", on_text_activate)
        self.entry.connect("changed", on_text_changed)

        # Set initial text if provided
        if initial_text:
            self.entry.set_text(initial_text)
            self.entry.select_region(0, -1)

        self.size_adjustment.set_value(font_size)
        self.spin.connect("value-changed", on_font_size_changed)

    """
    Public Methods
    """

    def popup_at_widget_coords(self, widget: Gtk.Widget, x: float, y: float) -> None:
        allocation = widget.get_allocation()

        rect = Gdk.Rectangle()
        rect.x = allocation.x + int(x)
        rect.y = allocation.y + int(y)
        rect.width = 1
        rect.height = 1

        self.set_pointing_to(rect)
        self.popup()

        self.entry.grab_focus()
