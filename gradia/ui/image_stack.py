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
from gradia.backend.ocr import OCR
from gradia.clipboard import copy_text_to_clipboard

@Gtk.Template(resource_path=f"{rootdir}/ui/image_stack.ui")
class ImageStack(Adw.Bin):
    __gtype_name__ = "GradiaImageStack"
    __gsignals__ = {
        "sidebar-toggled": (GObject.SignalFlags.RUN_FIRST, None, (bool,))
    }

    stack: Gtk.Stack = Gtk.Template.Child()

    picture_overlay: Gtk.Overlay = Gtk.Template.Child()
    drawing_overlay: DrawingOverlay = Gtk.Template.Child()

    picture: Gtk.Picture = Gtk.Template.Child()
    transparency_background: TransparencyBackground = Gtk.Template.Child()
    crop_overlay: CropOverlay = Gtk.Template.Child()
    crop_overlay_revealer: Gtk.Revealer = Gtk.Template.Child()

    erase_selected_revealer: Gtk.Revealer = Gtk.Template.Child()
    right_controls_revealer: Gtk.Revealer = Gtk.Template.Child()
    ocr_revealer: Gtk.Revealer = Gtk.Template.Child()
    ocr_text_view : Gtk.TextView = Gtk.Template.Child()

    drop_overlay: DropOverlay = Gtk.Template.Child()

    reset_crop_revealer: Gtk.Revealer = Gtk.Template.Child()
    confirm_crop_revealer: Gtk.Revealer = Gtk.Template.Child()

    bottom_sheet: Adw.BottomSheet = Gtk.Template.Child()

    crop_enabled: bool = False
    crop_has_been_enabled: bool = False


    def __init__(self, window: Adw.Window, **kwargs) -> None:
        super().__init__(**kwargs)
        self._setup()
        self.window = window

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
        self.ocr_revealer.set_reveal_child(True)
        self.crop_overlay_revealer.set_reveal_child(True)
        self.crop_overlay_revealer.set_sensitive(False)

        self.ocr_text_view.get_style_context().remove_class("view")

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
        self.ocr_revealer.set_reveal_child(not self.crop_enabled)
        self.confirm_crop_revealer.set_reveal_child(self.crop_enabled)
        self.crop_overlay_revealer.set_sensitive(self.crop_enabled)

        if self.crop_enabled:
            self.reset_crop_revealer.set_visible(True)

        self.emit("sidebar-toggled", self.crop_enabled)

        self.reset_crop_revealer.set_reveal_child(self.crop_enabled)

        if self.crop_enabled and not self.crop_has_been_enabled:
            self.crop_overlay.set_crop_rectangle(0.1, 0.1, 0.8, 0.8)
            self.crop_has_been_enabled = True

    def _update_ocr_ui_state(self) -> None:
        self.right_controls_revealer.set_reveal_child(not self.ocr_enabled)
        self.bottom_sheet.set_open(self.ocr_enabled)
        self.crop_overlay_revealer.set_reveal_child(not self.ocr_enabled)
        self.emit("sidebar-toggled", self.ocr_enabled)


    def on_ocr(self) -> None:
        self.ocr_enabled = True
        ocr = OCR()
        extracted_text = ocr.extract_text(self.window.processed_path)
        if not extracted_text.strip():
            self.window._show_notification(_("No text found in image"))
        else:
            buffer = self.ocr_text_view.get_buffer()
            buffer.set_text(extracted_text)
            self._update_ocr_ui_state()

    @Gtk.Template.Callback()
    def _on_sheet_shown_changed(self, bottom_sheet, pspec):
        if not bottom_sheet.get_open():
            self.ocr_enabled = False
            self._update_ocr_ui_state()

    @Gtk.Template.Callback()
    def _on_copy_ocr_clicked(self, button: Gtk.Button) -> None:
        buffer = self.ocr_text_view.get_buffer()
        start_iter, end_iter = buffer.get_bounds()
        text = buffer.get_text(start_iter, end_iter, True)
        copy_text_to_clipboard(text)
        self.window._show_notification(_("Result copied to clipboard"))

