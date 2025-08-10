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

from gi.repository import Gdk
from gradia.overlay.drawing_actions import DrawingMode
import re

class ToolOption:
    def __init__(
        self,
        mode: DrawingMode,
        size: int = 0,
        primary_color: Gdk.RGBA = None,
        fill_color: Gdk.RGBA = None,
        border_color: Gdk.RGBA = None,
        font: str = None,
    ) -> None:
        self.mode = mode
        self.size = size
        self._primary_color_str = self._rgba_to_str(primary_color or Gdk.RGBA(0,0,0,1))
        self._fill_color_str = self._rgba_to_str(fill_color or Gdk.RGBA(1,1,1,1))
        self._border_color_str = self._rgba_to_str(border_color or Gdk.RGBA(0,0,0,1))
        self.font = font or "Adwaita Sans"

    def _rgba_to_str(self, rgba: Gdk.RGBA) -> str:
        return f"rgba({rgba.red:.2f}, {rgba.green:.2f}, {rgba.blue:.2f}, {rgba.alpha:.2f})"

    def _str_to_rgba(self, s: str) -> Gdk.RGBA:
        m = re.match(r"rgba\(([\d.]+), ([\d.]+), ([\d.]+), ([\d.]+)\)", s)
        if not m:
            return Gdk.RGBA(0,0,0,1)
        r, g, b, a = map(float, m.groups())
        return Gdk.RGBA(r, g, b, a)

    @property
    def primary_color(self) -> Gdk.RGBA:
        return self._str_to_rgba(self._primary_color_str)

    @primary_color.setter
    def primary_color(self, value: Gdk.RGBA):
        self._primary_color_str = self._rgba_to_str(value)

    @property
    def fill_color(self) -> Gdk.RGBA:
        return self._str_to_rgba(self._fill_color_str)

    @fill_color.setter
    def fill_color(self, value: Gdk.RGBA):
        self._fill_color_str = self._rgba_to_str(value)

    @property
    def border_color(self) -> Gdk.RGBA:
        return self._str_to_rgba(self._border_color_str)

    @border_color.setter
    def border_color(self, value: Gdk.RGBA):
        self._border_color_str = self._rgba_to_str(value)

    def __repr__(self):
        return (
            f"<ToolStyle size={self.size}, font='{self.font}', "
            f"primary_color={self._primary_color_str}, "
            f"fill_color={self._fill_color_str}, "
            f"border_color={self._border_color_str}>"
        )



class ToolOptionsManager:
    def __init__(self):
        self._tool_configs = {}
        self._initialize_tools()

    def _initialize_tools(self):
        for mode in DrawingMode:
            self._tool_configs[mode] = ToolOption(mode)

    def get_tool(self, mode: DrawingMode) -> ToolOption:
        return self._tool_configs[mode]


class ToolConfig:
    def __init__(
        self,
        mode: DrawingMode,
        icon: str,
        column: int,
        row: int,
        shown_stack: str = "empty",
        has_scale: bool = False,
        has_primary_color: bool = False,
    ) -> None:
        self.mode = mode
        self.icon = icon
        self.column = column
        self.row = row
        self.shown_stack = shown_stack
        self.has_scale = has_scale
        self.has_primary_color = has_primary_color

    @staticmethod
    def get_all_tools_positions():
        black = Gdk.RGBA(red=0, green=0, blue=0, alpha=1)
        white = Gdk.RGBA(red=1, green=1, blue=1, alpha=1)
        transparent = Gdk.RGBA(red=0, green=0, blue=0, alpha=0)

        return [
            ToolConfig(
                mode=DrawingMode.SELECT,
                icon="pointer-primary-click-symbolic",
                column=0,
                row=0,
                shown_stack="empty",
                has_scale=False,
                has_primary_color=False,
            ),
            ToolConfig(
                mode=DrawingMode.PEN,
                icon="edit-symbolic",
                column=1,
                row=0,
                has_scale=True,
                has_primary_color=True,
            ),
            ToolConfig(
                mode=DrawingMode.TEXT,
                icon="text-insert2-symbolic",
                column=2,
                row=0,
                shown_stack="text",
                has_primary_color=True,
            ),
            ToolConfig(
                mode=DrawingMode.LINE,
                icon="draw-line-symbolic",
                column=3,
                row=0,
                has_scale=True,
                has_primary_color=True,
            ),
            ToolConfig(
                mode=DrawingMode.ARROW,
                icon="arrow1-top-right-symbolic",
                column=4,
                row=0,
                has_scale=True,
                has_primary_color=True,
            ),
            ToolConfig(
                mode=DrawingMode.SQUARE,
                icon="box-small-outline-symbolic",
                column=0,
                row=1,
                shown_stack="fill-border",
                has_scale=True,
                has_primary_color=True,
            ),
            ToolConfig(
                mode=DrawingMode.CIRCLE,
                icon="circle-outline-thick-symbolic",
                column=1,
                row=1,
                shown_stack="fill-border",
                has_scale=True,
                has_primary_color=True,
            ),
            ToolConfig(
                mode=DrawingMode.HIGHLIGHTER,
                icon="marker-symbolic",
                column=2,
                row=1,
                shown_stack="empty",
                has_scale=True,
                has_primary_color=True,
            ),
            ToolConfig(
                mode=DrawingMode.CENSOR,
                icon="checkerboard-big-symbolic",
                column=3,
                row=1,
                has_scale=False,
                has_primary_color=False,
            ),
            ToolConfig(
                mode=DrawingMode.NUMBER,
                icon="one-circle-symbolic",
                column=4,
                row=1,
                shown_stack="fill-border",
                has_scale=True,
                has_primary_color=True,
            ),
        ]


