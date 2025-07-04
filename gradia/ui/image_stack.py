# Copyright (C) 2025 tfuxu, Alexander Vanhee
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

from gi.repository import Adw, Gio, Gtk, Gdk, GLib

from gradia.constants import rootdir  # pyright: ignore
from gradia.overlay.drawing_overlay import DrawingOverlay
from gradia.overlay.transparency_overlay import TransparencyBackground

@Gtk.Template(resource_path=f"{rootdir}/ui/image_stack.ui")
class ImageStack(Adw.Bin):
    __gtype_name__ = "GradiaImageStack"

    stack: Gtk.Stack = Gtk.Template.Child()

    picture_overlay: Gtk.Overlay = Gtk.Template.Child()
    drawing_overlay: DrawingOverlay = Gtk.Template.Child()

    picture: Gtk.Picture = Gtk.Template.Child()
    transparency_background: TransparencyBackground = Gtk.Template.Child()

    controls_box: Gtk.Box = Gtk.Template.Child()
    erase_selected_revealer: Gtk.Revealer = Gtk.Template.Child()

    drop_target: Gtk.DropTarget = Gtk.Template.Child()

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)

        self._setup()

    def set_erase_selected_visible(self, show: bool) -> None:
        self.erase_selected_revealer.set_reveal_child(show)

    def _setup(self) -> None:
        self.transparency_background.set_picture_reference(self.picture)
        self.drawing_overlay.set_picture_reference(self.picture)
        self.drawing_overlay.set_erase_selected_revealer(self.erase_selected_revealer)

        # Setup image drop controller
        self.drop_target.set_gtypes([Gio.File])
        self.drop_target.connect("drop", self._on_file_dropped)

    def _on_file_dropped(self, _target: Gtk.DropTarget, value: Gio.File, _x: int, _y: int) -> bool:
        uri = value.get_uri()
        if uri:
            app = Gio.Application.get_default()
            action = app.lookup_action("load-drop") if app else None
            if action:
                action.activate(GLib.Variant('s', uri))
                return True
        return False
