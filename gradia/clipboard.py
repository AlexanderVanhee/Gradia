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

import os
from gi.repository import Gdk, GLib, GdkPixbuf

def save_texture_to_file(texture, temp_dir: str) -> str:
    temp_path: str = os.path.join(temp_dir, "clipboard_image.png")
    texture.save_to_png(temp_path)
    return temp_path

def save_pixbuff_to_path(temp_dir: str, pixbuff: GdkPixbuf.Pixbuf) -> str:
    TEMP_FILE_NAME: str = "clipboard_temp.png"
    temp_path: str = os.path.join(temp_dir, TEMP_FILE_NAME)
    pixbuff.savev(temp_path, "png", [], [])
    return temp_path

def copy_file_to_clipboard(local_path: str) -> None:
    with open(local_path, "rb") as f:
        png_data: bytes = f.read()

    bytes_data: GLib.Bytes = GLib.Bytes.new(png_data)
    clipboard: Gdk.Clipboard = Gdk.Display.get_default().get_clipboard()
    content_provider: Gdk.ContentProvider = Gdk.ContentProvider.new_for_bytes("image/png", bytes_data)
    clipboard.set_content(content_provider)