# Copyright (C) 2025 Alexander Vanhee
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.
#
# SPDX-License-Identifier: GPL-3.0-or-later

from pathlib import Path
import random
import re
import threading

from gi.repository import Adw, GLib, Gdk, GdkPixbuf, Gtk

from gradia.app_constants import PREDEFINED_GRADIENTS


class RecentFile:
    def __init__(self, path: Path) -> None:
        self.path = path
        self.folder = str(path.parent)
        self.name = str(path.parent)


class RecentImageGetter:
    MAX_RESULTS = 6
    XDG_USER_DIRS_FILE = Path.home() / ".config" / "user-dirs.dirs"
    FALLBACK_PICTURES_PATH = Path.home() / "Pictures"
    SCREENSHOTS_SUBDIR_NAME = "Screenshots"

    def __init__(self) -> None:
        pass

    def get_recent_screenshot_files(self) -> list[RecentFile]:
        screenshots_dir = self._get_screenshots_directory()
        if not screenshots_dir.exists():
            print("Screenshots directory does not exist.")
            return []

        image_extensions = {'.png', '.jpg', '.jpeg', '.webp', '.avif'}
        all_files = [f for f in screenshots_dir.iterdir()
                     if f.is_file() and f.suffix.lower() in image_extensions]

        sorted_files = sorted(all_files, key=lambda f: f.stat().st_mtime, reverse=True)
        top_files = sorted_files[:self.MAX_RESULTS]
        return [RecentFile(f) for f in top_files]

    def _get_screenshots_directory(self) -> Path:
        pictures_dir = self._get_xdg_user_dir("XDG_PICTURES_DIR") or self.FALLBACK_PICTURES_PATH
        return pictures_dir / self.SCREENSHOTS_SUBDIR_NAME

    def _get_xdg_user_dir(self, key: str) -> Path | None:
        if not self.XDG_USER_DIRS_FILE.exists():
            return None

        pattern = re.compile(rf'{key}="([^"]+)"')
        with open(self.XDG_USER_DIRS_FILE, "r") as f:
            for line in f:
                match = pattern.match(line.strip())
                if match:
                    path = match.group(1).replace("$HOME", str(Path.home()))
                    return Path(path)
        return None


@Gtk.Template(resource_path="/be/alexandervanhee/gradia/ui/recent_picker.ui")
class RecentPicker(Adw.Bin):
    __gtype_name__ = "GradiaRecentPicker"

    GRID_ROWS = 2
    GRID_COLS = 3
    FRAME_SPACING = 5
    IMAGE_WIDTH = 210
    IMAGE_HEIGHT = 120
    MAX_WIDTH_CHARS = 20
    MAX_FILENAME_LENGTH = 30
    FILENAME_TRUNCATE_LENGTH = 27

    item_grid: Gtk.Grid = Gtk.Template.Child()

    def __init__(self, callback=None, **kwargs) -> None:
        super().__init__(**kwargs)

        self.image_getter = RecentImageGetter()
        self.callback = callback
        self.image_buttons = []
        self.name_labels = []
        self.recent_files = []

        self.gradient_colors = PREDEFINED_GRADIENTS
        self.original_gradient_indexes = list(range(len(self.gradient_colors)))
        combined = list(zip(self.gradient_colors, self.original_gradient_indexes))
        random.shuffle(combined)
        self.gradient_colors, self.original_gradient_indexes = zip(*combined)
        self.gradient_colors = list(self.gradient_colors)
        self.original_gradient_indexes = list(self.original_gradient_indexes)

        self._setup_cards()
        self._load_images()

    def _setup_cards(self) -> None:
        for row in range(self.GRID_ROWS):
            for col in range(self.GRID_COLS):
                index = row * self.GRID_COLS + col

                container = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=self.FRAME_SPACING)
                container.set_size_request(self.IMAGE_WIDTH, self.IMAGE_HEIGHT)

                frame = Gtk.Frame()
                frame.set_size_request(self.IMAGE_WIDTH, self.IMAGE_HEIGHT)

                img_button = Gtk.Button(has_frame=False)
                img_button.set_size_request(self.IMAGE_WIDTH, self.IMAGE_HEIGHT)
                img_button.add_css_class("card")
                img_button.connect("clicked", lambda _btn, idx=index: self.on_image_click(idx))

                self._apply_gradient_to_button(img_button, index)

                placeholder = Gtk.Box()
                img_button.set_child(placeholder)

                frame.set_child(img_button)
                self.image_buttons.append(img_button)
                container.append(frame)

                name_label = Gtk.Label()
                name_label.set_wrap(True)
                name_label.set_max_width_chars(self.MAX_WIDTH_CHARS)
                name_label.add_css_class("caption")
                name_label.set_halign(Gtk.Align.CENTER)
                self.name_labels.append(name_label)
                container.append(name_label)

                self.item_grid.attach(container, col, row, 1, 1)

    def _apply_gradient_to_button(self, button: Gtk.Button, index: int) -> None:
        gradient_name = f"gradient-button-{index}"
        button.set_name(gradient_name)

        color_index = index % len(self.gradient_colors)
        start_color, end_color, angle = self.gradient_colors[color_index]

        css = f"""
            button#{gradient_name} {{
                background-image: linear-gradient({angle}deg, {start_color}, {end_color});
                min-width: {self.IMAGE_WIDTH}px;
                min-height: {self.IMAGE_HEIGHT}px;
                background-size: cover;
                transition: filter 0.3s ease;
            }}
            button#{gradient_name}:hover {{
                filter: brightness(1.2);
            }}
            button#{gradient_name}:active {{
                filter: brightness(0.9);
            }}
            button#{gradient_name} image {{
                border-radius: 4px;
            }}
        """

        css_provider = Gtk.CssProvider()
        css_provider.load_from_string(css)
        button.get_style_context().add_provider(
            css_provider,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
        )

    def _fade_in_widget(self, widget: Gtk.Widget) -> None:
        widget.set_opacity(0.0)
        target = Adw.PropertyAnimationTarget.new(widget, "opacity")
        animation = Adw.TimedAnimation(
            widget=widget,
            value_from=0.0,
            value_to=1.0,
            duration=300,
            easing=Adw.Easing.EASE_OUT,
            target=target,
        )
        animation.play()

    def _load_images(self) -> None:
        def load_in_thread() -> None:
            recent_files = self.image_getter.get_recent_screenshot_files()
            GLib.idle_add(self._update_display, recent_files)

        thread = threading.Thread(target=load_in_thread, daemon=True)
        thread.start()

    def _update_display(self, recent_files: list[RecentFile]) -> None:
        self.recent_files = recent_files

        for i in range(self.GRID_ROWS * self.GRID_COLS):
            if i < len(recent_files):
                file_obj = recent_files[i]

                try:
                    pixbuf = GdkPixbuf.Pixbuf.new_from_file(str(file_obj.path))

                    width = pixbuf.get_width()
                    height = pixbuf.get_height()

                    scale_x = self.IMAGE_WIDTH / width
                    scale_y = self.IMAGE_HEIGHT / height
                    scale = min(scale_x, scale_y)

                    new_width = int(width * scale)
                    new_height = int(height * scale)

                    scaled_pixbuf = pixbuf.scale_simple(
                        new_width, new_height, GdkPixbuf.InterpType.BILINEAR
                    )

                    image = Gtk.Image.new_from_pixbuf(scaled_pixbuf)
                    self.image_buttons[i].set_child(image)
                    self._fade_in_widget(image)

                except Exception as e:
                    filename = file_obj.path.name
                    if len(filename) > self.MAX_FILENAME_LENGTH:
                        filename = filename[:self.FILENAME_TRUNCATE_LENGTH] + "..."

                    error_label = Gtk.Label(label=filename)
                    self.image_buttons[i].set_child(error_label)
                    self._fade_in_widget(error_label)

                    print(f"Error loading image {file_obj.path}: {e}")
            else:
                icon = Gtk.Image.new_from_icon_name("image-missing-symbolic")
                icon.set_pixel_size(64)
                self.image_buttons[i].set_child(icon)
                self.image_buttons[i].set_sensitive(False)
                self.name_labels[i].set_text("")

    def on_image_click(self, index: int, *args) -> None:
        if index < len(self.recent_files):
            file_path = self.recent_files[index].path
            original_gradient_index = self.original_gradient_indexes[index % len(self.original_gradient_indexes)]

            if self.callback:
                self.callback(str(file_path), original_gradient_index)

    def refresh(self) -> None:
        self._load_images()
