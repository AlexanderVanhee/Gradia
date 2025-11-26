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

from gi.repository import Gdk

HexColor = str
RGBTuple = tuple[int, int, int]

def make_rgba(r: float, g: float, b: float, a: float) -> Gdk.RGBA:
    """Utility to construct a Gdk.RGBA with the given components.

    Gdk.RGBA does not take RGBA values as constructor arguments; you must
    instantiate it and then assign the channels explicitly.
    """
    rgba = Gdk.RGBA()
    rgba.red = r
    rgba.green = g
    rgba.blue = b
    rgba.alpha = a
    return rgba

def hex_to_rgba(hex_color: HexColor, alpha: float | None = None) -> Gdk.RGBA:
    """
    Converts hexadecimal color code to `Gdk.RGBA` object.

    NOTE: If you are looking for the raw representation of
    red, green and blue channels, use `hex_to_rgb()` method instead.
    """

    rgba = Gdk.RGBA()
    rgba.parse(hex_color)

    if alpha is not None:
        rgba.alpha = alpha

    return rgba

def rgba_to_hex(rgba: Gdk.RGBA) -> HexColor:
    """
    Converts `Gdk.RGBA` object to hexadecimal representation of red, green and
    blue channels.
    """

    r = int(rgba.red * 255)
    g = int(rgba.green * 255)
    b = int(rgba.blue * 255)
    a = int(rgba.alpha * 255)
    return f"#{r:02x}{g:02x}{b:02x}{a:02x}"

def hex_to_rgb(hex_color: HexColor) -> RGBTuple:
    """
    Converts hexadecimal color code to raw representation of red, green and
    blue channels.
    """

    hex_color = hex_color.lstrip('#')
    r, g, b = (int(hex_color[i:i+2], 16) for i in (0, 2, 4))
    return (r, g, b)

def rgba_to_tuple(color: Gdk.RGBA) -> tuple[float, float, float, float]:
    return (color.red, color.green, color.blue, color.alpha)

def tuple_to_rgba(color: tuple[float, float, float, float] | None) -> Gdk.RGBA:
    rgba = Gdk.RGBA()
    if not color or len(color) != 4:
        rgba.red = 0.0
        rgba.green = 0.0
        rgba.blue = 0.0
        rgba.alpha = 1.0
        return rgba
    rgba.red = float(color[0])
    rgba.green = float(color[1])
    rgba.blue = float(color[2])
    rgba.alpha = float(color[3])
    return rgba

def has_visible_color(color):
    return any(c > 0 for c in color[:3]) or (len(color) > 3 and color[3] > 0)

def _calculate_luminance(r: float, g: float, b: float, a: float) -> float:
    if a == 0:
        return 255
    return 0.299 * r * 255 + 0.587 * g * 255 + 0.114 * b * 255

def is_light_color_hex(hex_color: str) -> bool:
    hex_color = hex_color.lstrip("#")
    if len(hex_color) == 6:
        r, g, b = [int(hex_color[i:i+2], 16)/255 for i in (0, 2, 4)]
        a = 1.0
    elif len(hex_color) == 8:
        r, g, b, a = [int(hex_color[i:i+2], 16)/255 for i in (0, 2, 4, 6)]
    else:
        raise ValueError("Invalid hex color format")
    return _calculate_luminance(r, g, b, a) > 130

def is_light_color_rgba(rgba: Gdk.RGBA) -> bool:
    return _calculate_luminance(rgba.red, rgba.green, rgba.blue, rgba.alpha) > 130

def parse_rgb_string(s: str) -> tuple[int, int, int]:
    s = s.strip().lower()
    if s.startswith("rgb(") and s.endswith(")"):
        parts = s[4:-1].split(",")
        return tuple(int(p.strip()) for p in parts)
    raise ValueError(f"Invalid rgb string: {s}")

