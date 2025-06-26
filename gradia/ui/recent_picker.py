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

import random
import re
from typing import Callable, Optional
from pathlib import Path
from gi.repository import Adw, Gtk, GLib

from gradia.app_constants import PREDEFINED_GRADIENTS
from gradia.backend.settings import Settings
from gradia.constants import rootdir  # pyright: ignore

class RecentFile:
    def __init__(self, path: Path) -> None:
        self.path = path
        self.folder = str(path.parent)
        self.name = str(path.parent)


class RecentImageGetter:
    MAX_RESULTS = 6
    FALLBACK_PICTURES_PATH = Path.home() / "Pictures"

    def __init__(self) -> None:
        pass

    def get_recent_screenshot_files(self) -> list[RecentFile]:
        screenshots_dir = self._get_screenshots_directory()
        if not screenshots_dir.exists():
            print(f"Screenshots directory does not exist: {screenshots_dir}")
            return []

        image_extensions = {'.png', '.jpg', '.jpeg', '.webp', '.avif'}
        all_files = [f for f in screenshots_dir.iterdir()
                     if f.is_file() and f.suffix.lower() in image_extensions]

        sorted_files = sorted(all_files, key=lambda f: f.stat().st_mtime, reverse=True)
        top_files = sorted_files[:self.MAX_RESULTS]

        return [RecentFile(f) for f in top_files]

    def _get_screenshots_directory(self) -> Path | None:
        """
        Get screenshots directory with fallback logic:
        1. XDG_PICTURES_DIR/(configured folder from preferences)
        2. XDG_PICTURES_DIR/Screenshots
        3. XDG_PICTURES_DIR
        """
        xdg_pictures = GLib.get_user_special_dir(GLib.USER_DIRECTORY_PICTURES)

        if not xdg_pictures:
            return None

        xdg_pictures_path = Path(xdg_pictures)

        configured_subfolder = Settings().screenshot_subfolder
        if configured_subfolder:
            subfolder_path = xdg_pictures_path / configured_subfolder
            if subfolder_path.exists():
                return subfolder_path

        screenshots_path = xdg_pictures_path / "Screenshots"
        if screenshots_path.exists():
            return screenshots_path

        return xdg_pictures_path

@Gtk.Template(resource_path=f"{rootdir}/ui/recent_picker.ui")
class RecentPicker(Adw.Bin):
    __gtype_name__ = "GradiaRecentPicker"

    GRID_ROWS = 2
    GRID_COLUMNS = 3
    FRAME_SPACING = 5
    IMAGE_WIDTH = 260
    IMAGE_HEIGHT = 160
    MAX_WIDTH_CHARS = 20
    MAX_FILENAME_LENGTH = 30
    FILENAME_TRUNCATE_LENGTH = 27

    item_grid: Gtk.Grid = Gtk.Template.Child()

    def __init__(self, callback: Optional[Callable]=None, **kwargs) -> None:
        super().__init__(**kwargs)

        self.image_getter = RecentImageGetter()
        self.callback = callback

        self.image_buttons: list[Gtk.Button] = []
        self.name_labels: list[Gtk.Label] = []
        self.recent_files: list[RecentFile] = []

        self.gradient_colors = PREDEFINED_GRADIENTS
        self.original_gradient_indexes = list(range(len(self.gradient_colors)))
        combined = list(zip(self.gradient_colors, self.original_gradient_indexes))
        random.shuffle(combined)
        self.gradient_colors, self.original_gradient_indexes = zip(*combined)
        self.gradient_colors = list(self.gradient_colors)
        self.original_gradient_indexes = list(self.original_gradient_indexes)

        self._setup_cards()
        self._load_images()

    """
    Setup Methods
    """

    def _setup_cards(self) -> None:
        for row in range(self.GRID_ROWS):
            for column in range(self.GRID_COLUMNS):
                index = row * self.GRID_COLUMNS + column

                container = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=self.FRAME_SPACING)
                container.set_size_request(self.IMAGE_WIDTH, self.IMAGE_HEIGHT)

                frame = Gtk.Frame(vexpand=True)
                frame.set_size_request(self.IMAGE_WIDTH, self.IMAGE_HEIGHT)

                image_button = Gtk.Button(has_frame=False)
                image_button.set_size_request(self.IMAGE_WIDTH, self.IMAGE_HEIGHT)
                image_button.add_css_class("card")
                image_button.connect("clicked", lambda _btn, idx=index: self._on_image_clicked(idx))

                self._apply_gradient_to_button(image_button, index)

                placeholder = Gtk.Box()
                image_button.set_child(placeholder)

                frame.set_child(image_button)
                self.image_buttons.append(image_button)
                container.append(frame)

                name_label = Gtk.Label()
                name_label.set_wrap(True)
                name_label.set_max_width_chars(self.MAX_WIDTH_CHARS)
                name_label.add_css_class("caption")
                name_label.set_halign(Gtk.Align.CENTER)
                self.name_labels.append(name_label)
                container.append(name_label)

                self.item_grid.attach(container, column, row, 1, 1)

    """
    Callbacks
    """

    def _on_image_clicked(self, index: int, *args) -> None:
        if index < len(self.recent_files):
            file_path = self.recent_files[index].path
            original_gradient_index = self.original_gradient_indexes[index % len(self.original_gradient_indexes)]

            if self.callback:
                self.callback(str(file_path), original_gradient_index)

    """
    Public Methods
    """

    def refresh(self) -> None:
        self._load_images()

    """
    Private Methods
    """

    def _apply_gradient_to_button(self, button: Gtk.Button, index: int) -> None:
        gradient_name = f"gradient-button-{index}"
        button.set_name(gradient_name)
        button.add_css_class("recent-button")

        color_index = index % len(self.gradient_colors)
        start_color, end_color, angle = self.gradient_colors[color_index]

        css = f"""
            button#{gradient_name} {{
                background-image: linear-gradient({angle}deg, {start_color}, {end_color});
                min-width: {self.IMAGE_WIDTH}px;
                min-height: {self.IMAGE_HEIGHT}px;
            }}
        """

        css_provider = Gtk.CssProvider()
        css_provider.load_from_string(css)
        button.get_style_context().add_provider(
            css_provider,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
        )

    def _load_images(self) -> None:
        recent_files = self.image_getter.get_recent_screenshot_files()
        self._update_display(recent_files)

    def _update_display(self, recent_files: list[RecentFile]) -> None:
        self.recent_files = recent_files

        for i in range(self.GRID_ROWS * self.GRID_COLUMNS):
            if i < len(recent_files):
                file = recent_files[i]

                try:
                    picture = Gtk.Picture.new_for_filename(str(file.path))
                    picture.set_margin_top(10)
                    picture.set_margin_bottom(10)
                    picture.set_margin_start(10)
                    picture.set_margin_end(10)
                    self.image_buttons[i].set_child(picture)
                    self.image_buttons[i].set_sensitive(True)


                except Exception as e:
                    filename = file.path.name
                    if len(filename) > self.MAX_FILENAME_LENGTH:
                        filename = filename[:self.FILENAME_TRUNCATE_LENGTH] + "..."

                    error_label = Gtk.Label(label=filename)
                    self.image_buttons[i].set_child(error_label)
                    self.image_buttons[i].set_sensitive(False)
                    self.name_labels[i].set_text("")
                    print(f"Error loading image {file_obj.path}: {e}")
            else:
                icon = Gtk.Image.new_from_icon_name("image-missing-symbolic")
                self.image_buttons[i].set_child(icon)
                self.image_buttons[i].set_sensitive(False)
                self.name_labels[i].set_text("")
