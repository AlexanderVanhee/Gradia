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
    temp_path: str = os.path.join(temp_dir, f"clipboard_image_{os.urandom(6).hex()}.png")
    texture.save_to_png(temp_path)
    return temp_path

def save_pixbuff_to_path(temp_dir: str, pixbuff: GdkPixbuf.Pixbuf) -> str:
    TEMP_FILE_NAME: str = "clipboard_temp.png"
    temp_path: str = os.path.join(temp_dir, TEMP_FILE_NAME)
    pixbuff.savev(temp_path, "png", [], [])
    return temp_path


def copy_text_to_clipboard(text: str) -> None:
    display = Gdk.Display.get_default()
    if not display:
        print("Warning: Failed to retrieve `Gdk.Display` object.")
        return

    clipboard: Gdk.Clipboard = display.get_clipboard()
    text_bytes = text.encode("utf-8")
    bytes_data = GLib.Bytes.new(text_bytes)
    content_provider = Gdk.ContentProvider.new_for_bytes("text/plain;charset=utf-8", bytes_data)
    clipboard.set_content(content_provider)

def copy_pixbuf_to_clipboard(pixbuf: GdkPixbuf.Pixbuf) -> None:
    display = Gdk.Display.get_default()
    if not display:
        print("Warning: Failed to retrieve `Gdk.Display` object.")
        return

    clipboard: Gdk.Clipboard = display.get_clipboard()
    content_provider: Gdk.ContentProvider = Gdk.ContentProvider.new_for_value(pixbuf)
    clipboard.set_content(content_provider)
