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
    return f"#{r:02x}{g:02x}{b:02x}"

def hex_to_rgb(hex_color: HexColor) -> RGBTuple:
    """
    Converts hexadecimal color code to raw representation of red, green and
    blue channels.
    """

    hex_color = hex_color.lstrip('#')
    r, g, b = (int(hex_color[i:i+2], 16) for i in (0, 2, 4))
    return (r, g, b)

def has_visible_color(color):
    return any(c > 0 for c in color[:3]) or (len(color) > 3 and color[3] > 0)
