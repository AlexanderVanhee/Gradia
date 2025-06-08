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

from typing import Optional, Callable
from gi.repository import Gtk, Gdk, Adw, GLib, Gio, GdkPixbuf
from PIL import Image
from gradia.graphics.background import Background
import threading
import tempfile
import os
import io

PRESET_IMAGES = [
    "/be/alexandervanhee/gradia/images/preset1.avif",
    "/be/alexandervanhee/gradia/images/preset2.avif",
    "/be/alexandervanhee/gradia/images/preset3.avif",
    "/be/alexandervanhee/gradia/images/preset4.avif",
    "/be/alexandervanhee/gradia/images/preset5.avif",
    "/be/alexandervanhee/gradia/images/preset6.avif",
]

class ImageBackground(Background):
    def __init__(self, file_path: Optional[str] = None) -> None:
        self.file_path: Optional[str] = file_path
        self.image: Optional[Image.Image] = None

        if file_path:
            self.load_image(file_path)
        else:
            if PRESET_IMAGES:
                self.load_image(PRESET_IMAGES[0])

    def load_image(self, path: str) -> None:
        self.file_path = path
        try:
            if path.startswith("/") and Gio.resources_lookup_data(path, Gio.ResourceLookupFlags.NONE):
                # Load from GResource
                resource_data = Gio.resources_lookup_data(path, Gio.ResourceLookupFlags.NONE)
                bytes_data = resource_data.get_data()
                byte_stream = io.BytesIO(bytes_data)
                self.image = Image.open(byte_stream).convert("RGBA")
            else:
                self.image = Image.open(path).convert("RGBA")
        except Exception as e:
            self.image = None
            print(f"Error loading image: {e}")

    def prepare_image(self, width: int, height: int) -> Optional[Image.Image]:
        if not self.image:
            return None

        img = self.image
        img_ratio = img.width / img.height
        target_ratio = width / height

        if img_ratio > target_ratio:
            new_height = height
            new_width = int(new_height * img_ratio)
        else:
            new_width = width
            new_height = int(new_width / img_ratio)

        img_resized = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
        left = (new_width - width) // 2
        top = (new_height - height) // 2
        right = left + width
        bottom = top + height

        return img_resized.crop((left, top, right, bottom))

    def get_name(self) -> str:
        return f"image-{self.file_path or 'none'}"



class ImageSelector:
    def __init__(
        self,
        image_background: ImageBackground,
        callback: Optional[Callable[[ImageBackground], None]] = None,
        parent_window: Optional[Gtk.Window] = None
    ) -> None:
        self.image_background = image_background
        self.callback = callback
        self.preview_picture = Gtk.Picture()
        self.popover: Optional[ImagePresetPopover] = None
        self._setup_drag_and_drop()
        self._setup_gesture()
        self.widget = self._build()
        self._update_preview()
        self.parent_window = parent_window

    def _build(self) -> Adw.PreferencesGroup:
        group = Adw.PreferencesGroup(title=_("Image Background"))

        icon_button = Gtk.Button(
            icon_name="columns-symbolic",
            tooltip_text=_("Image Presets"),
            valign=Gtk.Align.CENTER,
            focusable=False,
            can_focus=False
        )
        icon_button.connect("clicked", self._toggle_popover)
        icon_button.get_style_context().add_class("flat")
        group.set_header_suffix(icon_button)

        button_row = Adw.ActionRow()
        file_button = Gtk.Button(
            label=_("Select Image"),
            margin_start=8, margin_end=8, margin_top=8, margin_bottom=8
        )
        file_button.connect("clicked", self._on_select_clicked)
        button_row.set_child(file_button)
        button_row.set_activatable(False)
        group.add(button_row)

        preview_row = Adw.ActionRow()
        preview_row.set_activatable(False)
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, hexpand=True, halign=Gtk.Align.CENTER)
        self.preview_picture.set_size_request(250, 88)
        self.preview_picture.set_content_fit(Gtk.ContentFit.COVER)
        frame = Gtk.Frame(margin_top=8, margin_bottom=8)
        frame.set_child(self.preview_picture)
        box.append(frame)
        preview_row.set_child(box)
        group.add(preview_row)

        return group

    def _setup_drag_and_drop(self) -> None:
        drop_target = Gtk.DropTarget.new(Gio.File, Gdk.DragAction.COPY)
        drop_target.connect("drop", self._on_image_drop)
        self.preview_picture.add_controller(drop_target)

    def _setup_gesture(self) -> None:
        gesture = Gtk.GestureClick.new()
        gesture.connect("pressed", self._on_preview_clicked)
        self.preview_picture.add_controller(gesture)

    def _on_preview_clicked(self, gesture: Gtk.GestureClick, n_press: int, x: float, y: float) -> None:
        self._on_select_clicked(None)

    def _on_image_drop(self, drop_target: Gtk.DropTarget, file: Gio.File, x: int, y: int) -> bool:
        file_path = file.get_path()
        if file_path:
            self._load_image_async(file_path)
            return True
        return False

    def _on_select_clicked(self, _button: Optional[Gtk.Button]) -> None:
        file_dialog = Gtk.FileDialog()
        file_filter = Gtk.FileFilter()
        file_filter.set_name(_("Image files"))
        file_filter.add_mime_type("image/png")
        file_filter.add_mime_type("image/jpg")
        file_filter.add_mime_type("image/jpeg")
        file_filter.add_mime_type("image/webp")
        file_filter.add_mime_type("image/avif")
        filter_list = Gio.ListStore.new(Gtk.FileFilter)
        filter_list.append(file_filter)
        file_dialog.set_filters(filter_list)

        file_dialog.open(self.parent_window, None, self._on_file_dialog_ready)

    def _on_file_dialog_ready(self, file_dialog: Gtk.FileDialog, result: Gio.AsyncResult) -> None:
        try:
            file = file_dialog.open_finish(result)
            file_path = file.get_path()
            if file_path:
                self._load_image_async(file_path)
        except GLib.Error as e:
            print(f"FileDialog cancelled or failed: {e.message}")

    def _load_image_async(self, file_path: str) -> None:
        def load_in_background():
            try:
                self.image_background.load_image(file_path)
                GLib.idle_add(self._on_image_loaded)
            except Exception as e:
                print(f"Error loading image: {e}")
        thread = threading.Thread(target=load_in_background, daemon=True)
        thread.start()

    def _on_image_loaded(self) -> None:
        self._update_preview()
        if self.callback:
            self.callback(self.image_background)

    def _update_preview(self) -> None:
        if self.image_background.image:
            def save_and_update():
                try:
                    image = self.image_background.image.copy()

                    max_width = 400
                    if image.width > max_width:
                        ratio = max_width / image.width
                        new_size = (int(image.width * ratio), int(image.height * ratio))
                        image = image.resize(new_size, Image.LANCZOS)

                    with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as temp_file:
                        temp_path = temp_file.name
                        image.save(temp_path, 'PNG')

                    GLib.idle_add(self._set_preview_image, temp_path)
                except Exception as e:
                    print(f"Error saving preview: {e}")

            thread = threading.Thread(target=save_and_update, daemon=True)
            thread.start()
        else:
            self.preview_picture.set_paintable(None)

    def _set_preview_image(self, temp_path: str) -> None:
        self.preview_picture.set_filename(temp_path)

        def cleanup_temp_file():
            try:
                os.unlink(temp_path)
            except Exception:
                pass
            return False

        GLib.timeout_add(100, cleanup_temp_file)
        return False

    def _toggle_popover(self, button: Gtk.Button) -> None:
        if self.popover:
            self.popover.popdown()
            self.popover = None

        self.popover = ImagePresetPopover(button, self._load_image_async)
        self.popover.popup()



class ImagePresetPopover(Gtk.Popover):
    def __init__(self, parent_button: Gtk.Widget, on_select: callable) -> None:
        super().__init__()
        self.set_parent(parent_button)
        self.set_autohide(True)
        self.set_has_arrow(True)

        self.flowbox = Gtk.FlowBox(
            max_children_per_line=3,
            selection_mode=Gtk.SelectionMode.NONE,
            valign=Gtk.Align.CENTER,
            margin_top=10,
            margin_bottom=10,
            margin_start=10,
            margin_end=10,
            row_spacing=10,
            column_spacing=10,
            homogeneous=True
        )

        for path in PRESET_IMAGES:
            button_widget = self._create_preset_button(path, on_select)
            self.flowbox.append(button_widget)

        self.set_child(self.flowbox)

    def _create_preset_button(self, path: str, on_select: callable) -> Gtk.Button:
        button_widget = Gtk.Button(focusable=False, can_focus=False)
        button_widget.set_size_request(80, 60)
        button_widget.get_style_context().add_class("flat")

        stack = Gtk.Stack()
        stack.set_transition_type(Gtk.StackTransitionType.CROSSFADE)
        stack.set_transition_duration(200)
        stack.set_hexpand(True)
        stack.set_vexpand(True)

        spinner = Adw.Spinner.new()
        spinner.set_size_request(32, 32)
        spinner.set_hexpand(False)
        spinner.set_vexpand(False)
        spinner.set_halign(Gtk.Align.CENTER)
        spinner.set_valign(Gtk.Align.CENTER)
        stack.add_named(spinner, "loading")

        picture = Gtk.Picture()
        picture.set_content_fit(Gtk.ContentFit.COVER)
        picture.set_halign(Gtk.Align.FILL)
        picture.set_valign(Gtk.Align.FILL)
        picture.set_hexpand(True)
        picture.set_vexpand(True)
        stack.add_named(picture, "image")

        error_icon = Gtk.Image.new_from_icon_name("image-missing-symbolic")
        error_icon.set_pixel_size(24)
        error_icon.set_halign(Gtk.Align.CENTER)
        error_icon.set_valign(Gtk.Align.CENTER)
        stack.add_named(error_icon, "error")

        css_provider = Gtk.CssProvider()
        button_id = f"preset-button-{abs(hash(path)) % 10000}"
        button_widget.set_name(button_id)

        css = f"""
            button#{button_id} {{
                min-width: 80px;
                min-height: 60px;
                padding: 0;
                border-radius: 10px;
                border: 1px solid rgba(0,0,0,0.1);
                transition: filter 0.3s ease;
            }}
            button#{button_id}:hover {{
                filter: brightness(1.1);
            }}
            button#{button_id} picture {{
                border-radius: 9px;
            }}
        """
        css_provider.load_from_string(css)
        Gtk.StyleContext.add_provider_for_display(
            Gdk.Display.get_default(),
            css_provider,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
        )

        button_widget.set_child(stack)

        button_widget.connect("clicked", lambda b, p=path: self._select(p, on_select))

        self._load_image_async(path, picture, stack)

        return button_widget

    def _load_image_async(self, resource_path: str, picture: Gtk.Picture, stack: Gtk.Stack) -> None:
        def load_in_background():
            try:
                resource = Gio.resources_lookup_data(resource_path, Gio.ResourceLookupFlags.NONE)
                data = resource.get_data()

                loader = GdkPixbuf.PixbufLoader.new()
                loader.write(data)
                loader.close()
                pixbuf = loader.get_pixbuf()

                if pixbuf is None:
                    raise RuntimeError("Failed to load pixbuf from resource data")

                GLib.idle_add(self._on_image_loaded, picture, stack, pixbuf)

            except Exception as e:
                print(f"Error loading preset image {resource_path}: {e}")
                GLib.idle_add(self._on_image_error, stack)

        thread = threading.Thread(target=load_in_background, daemon=True)
        thread.start()

    def _on_image_loaded(self, picture: Gtk.Picture, stack: Gtk.Stack, pixbuf: GdkPixbuf.Pixbuf) -> bool:
        try:
            max_width, max_height = 80, 60

            width = pixbuf.get_width()
            height = pixbuf.get_height()

            scale_width = max_width
            scale_height = int(height * max_width / width)

            if scale_height > max_height:
                scale_height = max_height
                scale_width = int(width * max_height / height)

            if width > max_width or height > max_height:
                scaled_pixbuf = pixbuf.scale_simple(scale_width, scale_height, GdkPixbuf.InterpType.BILINEAR)
            else:
                scaled_pixbuf = pixbuf

            picture.set_pixbuf(scaled_pixbuf)
            stack.set_visible_child_name("image")
        except Exception as e:
            print(f"Error setting image pixbuf: {e}")
            stack.set_visible_child_name("error")

        return False

    def _on_image_error(self, stack: Gtk.Stack) -> bool:
        stack.set_visible_child_name("error")
        return False

    def _select(self, path: str, callback: callable) -> None:
        callback(path)
        self.popdown()
