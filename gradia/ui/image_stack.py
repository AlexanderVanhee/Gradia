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

from gi.repository import Adw, Gio, Gtk, Gdk, GLib, GObject

from gradia.constants import rootdir  # pyright: ignore
from gradia.overlay.drawing_overlay import DrawingOverlay
from gradia.overlay.transparency_overlay import TransparencyBackground
from gradia.overlay.crop_overlay import CropOverlay
from gradia.overlay.drop_overlay import DropOverlay

@Gtk.Template(resource_path=f"{rootdir}/ui/image_stack.ui")
class ImageStack(Adw.Bin):
    __gtype_name__ = "GradiaImageStack"
    __gsignals__ = {
        "crop-toggled": (GObject.SignalFlags.RUN_FIRST, None, (bool,))
    }

    stack: Gtk.Stack = Gtk.Template.Child()

    picture_overlay: Gtk.Overlay = Gtk.Template.Child()
    drawing_overlay: DrawingOverlay = Gtk.Template.Child()

    picture: Gtk.Picture = Gtk.Template.Child()
    transparency_background: TransparencyBackground = Gtk.Template.Child()
    crop_overlay: CropOverlay = Gtk.Template.Child()

    erase_selected_revealer: Gtk.Revealer = Gtk.Template.Child()
    right_controls_revealer: Gtk.Revealer = Gtk.Template.Child()

    drop_overlay: DropOverlay = Gtk.Template.Child()

    reset_crop_revealer: Gtk.Revealer = Gtk.Template.Child()

    crop_enabled: bool = False
    crop_has_been_enabled: bool = False


    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self._setup()

    def set_erase_selected_visible(self, show: bool) -> None:
        self.erase_selected_revealer.set_reveal_child(show)

    def _setup(self) -> None:
        self.transparency_background.set_picture_reference(self.picture)
        self.crop_overlay.set_picture_reference(self.picture)
        self.crop_overlay.set_can_target(False)
        self.drawing_overlay.set_picture_reference(self.picture)
        self.drawing_overlay.set_erase_selected_revealer(self.erase_selected_revealer)
        self.right_controls_revealer.set_reveal_child(True)
        self.reset_crop_revealer.set_visible(False)

        drop_target = Gtk.DropTarget.new(Gio.File, Gdk.DragAction.COPY)
        drop_target.set_preload(True)

        drop_target.connect("drop", self._on_file_dropped)
        drop_target.set_preload(True)

        self.drop_overlay.drop_target = drop_target

        self.reset_crop_revealer.connect("notify::reveal-child", self._on_reset_crop_reveal_changed)

    def _on_file_dropped(self, _target: Gtk.DropTarget, value: Gio.File, _x: int, _y: int) -> bool:
        uri = value.get_uri()
        if uri:
            app = Gio.Application.get_default()
            action = app.lookup_action("load-drop") if app else None
            if action:
                action.activate(GLib.Variant('s', uri))
                return True
        return False

    def _on_reset_crop_reveal_changed(self, revealer: Gtk.Revealer, _pspec: GObject.ParamSpec) -> None:
        if not revealer.get_reveal_child():
            GLib.timeout_add(300, lambda: revealer.set_visible(False))

    def reset_crop_selection(self) -> None:
        self.crop_overlay.set_crop_rectangle(0.0, 0.0, 1, 1)
        self.crop_has_been_enabled = False
        self.on_toggle_crop()

    def on_toggle_crop(self) -> None:
        self.crop_enabled = not self.crop_enabled
        self.crop_overlay.set_interaction_enabled(self.crop_enabled)
        self.crop_overlay.set_can_target(self.crop_enabled)
        self.right_controls_revealer.set_reveal_child(not self.crop_enabled)

        if self.crop_enabled:
            self.reset_crop_revealer.set_visible(True)

        self.emit("crop-toggled", self.crop_enabled)

        self.reset_crop_revealer.set_reveal_child(self.crop_enabled)

        if self.crop_enabled and not self.crop_has_been_enabled:
            self.crop_overlay.set_crop_rectangle(0.1, 0.1, 0.8, 0.8)
            self.crop_has_been_enabled = True

