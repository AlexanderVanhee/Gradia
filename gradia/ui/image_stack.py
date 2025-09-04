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

from gi.repository import Adw, Gio, Gtk, Gdk, GLib, GObject, Graphene

from gradia.constants import rootdir
from gradia.overlay.drawing_overlay import DrawingOverlay
from gradia.overlay.transparency_overlay import TransparencyBackground
from gradia.overlay.crop_overlay import CropOverlay
from gradia.overlay.drop_overlay import DropOverlay
from gradia.ui.widget.aspect_ratio_button import AspectRatioButton
from gradia.overlay.zoom_controller import ZoomController

@Gtk.Template(resource_path=f"{rootdir}/ui/image_stack.ui")
class ImageStack(Adw.Bin):
    __gtype_name__ = "GradiaImageStack"
    __gsignals__ = {
        "crop-toggled": (GObject.SignalFlags.RUN_FIRST, None, (bool,)),
        "zoom-changed": (GObject.SignalFlags.RUN_FIRST, None, (float,))
    }

    stack: Gtk.Stack = Gtk.Template.Child()

    main_overlay: Gtk.Overlay = Gtk.Template.Child()
    zoomable_widget: ZoomController = Gtk.Template.Child()
    picture_overlay: Gtk.Overlay = Gtk.Template.Child()
    drawing_overlay: DrawingOverlay = Gtk.Template.Child()

    picture: Gtk.Picture = Gtk.Template.Child()
    transparency_background: TransparencyBackground = Gtk.Template.Child()
    crop_overlay: CropOverlay = Gtk.Template.Child()

    erase_controls_revealer: Gtk.Revealer = Gtk.Template.Child()
    crop_controls_revealer: Gtk.Revealer = Gtk.Template.Child()
    right_controls_revealer: Gtk.Revealer = Gtk.Template.Child()

    drop_overlay: DropOverlay = Gtk.Template.Child()

    crop_options_revealer: Gtk.Revealer = Gtk.Template.Child()
    confirm_crop_revealer: Gtk.Revealer = Gtk.Template.Child()

    zoom_label: Gtk.Label = Gtk.Template.Child()
    zoom_out_button: Gtk.Button = Gtk.Template.Child()
    zoom_in_button: Gtk.Button = Gtk.Template.Child()
    reset_zoom_button: Gtk.Button = Gtk.Template.Child()
    zoom_info_revealer: Gtk.Revealer = Gtk.Template.Child()
    sidebar_revealer: Gtk.Revealer = Gtk.Template.Child()
    sidebar_button: Gtk.Button = Gtk.Template.Child()

    crop_enabled: bool = False
    crop_has_been_enabled: bool = False

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self._compact = False
        self._setup()

    @GObject.Property(type=bool, default=False)
    def compact(self) -> bool:
        return self._compact

    @compact.setter
    def compact(self, value: bool) -> None:
        if self._compact != value:
            self._compact = value
            self._update_compact_ui()

    def _update_compact_ui(self) -> None:
        self.sidebar_button.set_visible(self._compact)
        zoom_level = self.zoomable_widget.get_property("zoom-level")
        self.zoom_label.set_visible(not self._compact)

    def set_erase_selected_visible(self, show: bool) -> None:
        self.erase_controls_revealer.set_reveal_child(show)

    def _setup(self) -> None:
        self.transparency_background.set_picture_reference(self.picture)
        self.crop_overlay.set_picture_reference(self.picture)
        self.crop_overlay.set_can_target(False)
        self.drawing_overlay.set_picture_reference(self.picture)
        self.drawing_overlay.set_erase_selected_revealer(self.erase_controls_revealer)
        self.right_controls_revealer.set_reveal_child(True)

        self.zoomable_widget.set_child_widgets(
            self.picture_overlay,
            self.drawing_overlay,
            self.crop_overlay,
            self.transparency_background,
            self.picture
        )

        self.zoomable_widget.connect("notify::zoom-level", self._on_zoom_level_changed)

        drop_target = Gtk.DropTarget.new(Gio.File, Gdk.DragAction.COPY)
        drop_target.set_preload(True)
        drop_target.connect("drop", self._on_file_dropped)
        self.drop_overlay.drop_target = drop_target

    def is_compact(self) -> bool:
        return self._compact

    def _on_zoom_level_changed(self, widget, pspec) -> None:
        zoom_level = widget.get_property("zoom-level")
        percentage = int(zoom_level * 100)
        self.zoom_label.set_visible(not self._compact)
        self.zoom_label.set_text(f"{percentage}%")
        self.emit("zoom-changed", zoom_level)

        self.zoom_out_button.set_sensitive(zoom_level > widget.min_zoom)
        self.zoom_in_button.set_sensitive(zoom_level < widget.max_zoom)

        self.zoom_info_revealer.set_reveal_child(zoom_level != 1)

    def _on_file_dropped(self, _target: Gtk.DropTarget, value: Gio.File, _x: int, _y: int) -> bool:
        uri = value.get_uri()
        if uri:
            window = self.get_root()
            action = window.lookup_action("load-drop") if window else None
            if action:
                action.activate(GLib.Variant('s', uri))
                return True
        return False

    def reset_crop_selection(self) -> None:
        self.crop_overlay.set_crop_rectangle(0.0, 0.0, 1, 1)
        self.crop_overlay.aspect_ratio = 0
        self.crop_has_been_enabled = False
        self.on_toggle_crop()

    def on_toggle_crop(self) -> None:
        self.crop_enabled = not self.crop_enabled
        self.crop_overlay.interactive = self.crop_enabled
        self.crop_overlay.set_can_target(self.crop_enabled)
        self.right_controls_revealer.set_reveal_child(not self.crop_enabled)
        self.right_controls_revealer.set_sensitive(not self.crop_enabled)
        self.confirm_crop_revealer.set_reveal_child(self.crop_enabled)
        self.sidebar_revealer.set_reveal_child(not self.crop_enabled)
        self.zoomable_widget.disable_zoom = self.crop_enabled
        self.sidebar_button.set_sensitive(not self.crop_enabled)
        if not self._compact:
            self._show_sidebar(not self.crop_enabled)
        self.crop_options_revealer.set_reveal_child(self.crop_enabled)

        if self.crop_enabled and not self.crop_has_been_enabled:
            self.crop_overlay.set_crop_rectangle(0.1, 0.1, 0.8, 0.8)
            self.crop_has_been_enabled = True

    def _show_sidebar(self, value):
        window = self.get_root()
        action = window.lookup_action("sidebar-shown")
        if action:
            action.activate(GLib.Variant('b', value))
            return True

    def set_aspect_ratio(self, ratio: float) -> None:
        if self.crop_enabled:
            self.crop_overlay.aspect_ratio = ratio

    def zoom_in(self, factor: float = 1.2) -> None:
        self.zoomable_widget.zoom_in(factor)

    def zoom_out(self, factor: float = 0.8) -> None:
        self.zoomable_widget.zoom_out(factor)

    def reset_zoom(self) -> None:
        self.zoomable_widget.reset_zoom()

    def set_zoom_level(self, zoom_level: float) -> None:
        self.zoomable_widget.zoom_level = zoom_level

    def get_zoom_level(self) -> float:
        return self.zoomable_widget.zoom_level

    def on_image_loaded(self) -> None:
        self.reset_zoom()
        self._on_zoom_level_changed(self.zoomable_widget, None)
