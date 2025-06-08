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

from gi.repository import Gtk, Gio, Adw, Gdk, GLib

from gradia.overlay.drawing_overlay import DrawingOverlay

@Gtk.Template(resource_path="/be/alexandervanhee/gradia/ui/image_stack.ui")
class ImageStack(Adw.Bin):
    __gtype_name__ = "GradiaImageStack"

    stack: Gtk.Stack = Gtk.Template.Child()

    picture_overlay: Gtk.Overlay = Gtk.Template.Child()
    picture: Gtk.Picture = Gtk.Template.Child()

    controls_box: Gtk.Box = Gtk.Template.Child()
    erase_selected_revealer: Gtk.Revealer = Gtk.Template.Child()

    drop_target = Gtk.DropTarget.new(type=Gio.File, actions=Gdk.DragAction.COPY)

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)

        self.drawing_overlay = DrawingOverlay()
        self.drawing_overlay.set_visible(True)
        self.drawing_overlay.set_picture_reference(self.picture)
        self.drawing_overlay.set_erase_selected_revealer(self.erase_selected_revealer)

        self._setup()

    def _setup(self) -> None:
        # Add overlays
        self.picture_overlay.add_overlay(self.drawing_overlay)
        self.picture_overlay.add_overlay(self.controls_box)

        # Setup image drop controller
        self.drop_target.set_preload(True)
        self.drop_target.connect("drop", self._on_file_dropped)
        self.stack.add_controller(self.drop_target)

    def set_erase_selected_visible(self, show: bool):
        self.erase_selected_revealer.set_reveal_child(show)

    def _on_file_dropped(self, _target: Gtk.DropTarget, value: Gio.File, _x: int, _y: int) -> None:
        uri = value.get_uri()
        if uri:
            app = Gio.Application.get_default()
            action = app.lookup_action("load-drop") if app else None
            if action:
                pass
                action.activate(GLib.Variant('s', uri))
