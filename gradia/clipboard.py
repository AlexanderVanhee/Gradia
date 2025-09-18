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
import tempfile
from gi.repository import Gdk, GLib, GdkPixbuf
from gradia.backend.logger import Logger

logger = Logger()

def save_texture_to_file(texture, temp_dir: str) -> str:
    temp_path: str = os.path.join(temp_dir, f"clipboard_image_{os.urandom(6).hex()}.png")
    texture.save_to_png(temp_path)
    return temp_path

def save_pixbuf_to_path(temp_dir: str, pixbuf: GdkPixbuf.Pixbuf) -> str:
    TEMP_FILE_NAME: str = "clipboard_temp.png"
    temp_path: str = os.path.join(temp_dir, TEMP_FILE_NAME)
    pixbuf.savev(temp_path, "png", [], [])
    return temp_path


def copy_text_to_clipboard(text: str) -> None:
    display = Gdk.Display.get_default()
    if not display:
        logger.warning("Failed to retrieve `Gdk.Display` object.")
        return

    clipboard: Gdk.Clipboard = display.get_clipboard()
    text_bytes = text.encode("utf-8")
    bytes_data = GLib.Bytes.new(text_bytes)
    content_provider = Gdk.ContentProvider.new_for_bytes("text/plain;charset=utf-8", bytes_data)
    clipboard.set_content(content_provider)

def copy_pixbuf_to_clipboard(pixbuf: GdkPixbuf.Pixbuf) -> None:
    display = Gdk.Display.get_default()
    if not display:
        logger.warning("Failed to retrieve `Gdk.Display` object.")
        return

    image_bytes: bytes | None = None
    tmp_path: str | None = None
    try:
        image_bytes = save_pixbuf_in_memory(pixbuf)
    except Exception as e:
        logger.warning(f"Failed to encode pixbuf to PNG bytes: {e}")
        try:
            image_bytes, tmp_path = save_pixbuf_with_tmpfile(pixbuf)
        except Exception as e2:
            logger.warning(f"Failed to use temp file to save pixbuf: {e2}, falling back to Gdk.ContentProvider")
        finally:
            try:
                if tmp_path and os.path.exists(tmp_path):
                    os.unlink(tmp_path)
            except Exception:
                pass

    clipboard: Gdk.Clipboard = display.get_clipboard()
    if image_bytes is not None:
        provider = Gdk.ContentProvider.new_for_bytes("image/png", GLib.Bytes.new(image_bytes))
    else:
        provider: Gdk.ContentProvider = Gdk.ContentProvider.new_for_value(pixbuf)
    clipboard.set_content(provider)


def save_pixbuf_in_memory(pixbuf: GdkPixbuf.Pixbuf) -> bytes | None:
    ret = pixbuf.save_to_bufferv("png", [], [])
    if isinstance(ret, (bytes, bytearray)):
        image_bytes = bytes(ret)
    elif isinstance(ret, tuple):
        candidates = [x for x in ret if isinstance(x, (bytes, bytearray))]
        if candidates:
            image_bytes = bytes(candidates[0])
        else:
            raise RuntimeError("Unexpected return from save_to_bufferv")
    else:
        raise RuntimeError("Unexpected return from save_to_bufferv")
    return image_bytes

def save_pixbuf_with_tmpfile(pixbuf: GdkPixbuf.Pixbuf) -> tuple[bytes, str]:
    fd, tmp_path = tempfile.mkstemp(prefix="gradia_clip_", suffix=".png")
    os.close(fd)
    pixbuf.savev(tmp_path, "png", [], [])
    with open(tmp_path, "rb") as f:
        image_bytes = f.read()
    return image_bytes, tmp_path


