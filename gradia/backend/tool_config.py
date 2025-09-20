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

from typing import List, Optional, Callable
from gi.repository import Gdk
from gradia.overlay.drawing_actions import DrawingMode
import re
import json
from gradia.backend.settings import Settings

class ToolOption:
    def __init__(
        self,
        mode: DrawingMode,
        size: int = 14,
        primary_color: Gdk.RGBA = None,
        fill_color: Gdk.RGBA = None,
        border_color: Gdk.RGBA = None,
        font: str = None,
        on_change_callback: Optional[Callable[['ToolOption'], None]] = None,
        is_temporary: bool = False,
    ) -> None:
        self.mode = mode
        self._size = size
        self._primary_color_str = self._rgba_to_str(primary_color or Gdk.RGBA(0,0,0,1))
        self._fill_color_str = self._rgba_to_str(fill_color or Gdk.RGBA(1,1,1,1))
        self._border_color_str = self._rgba_to_str(border_color or Gdk.RGBA(0,0,0,0))
        self._font = font or "Adwaita Sans"
        self._on_change_callback = on_change_callback
        self._is_temporary = is_temporary

    def _rgba_to_str(self, rgba: Gdk.RGBA) -> str:
        return f"rgba({rgba.red:.2f}, {rgba.green:.2f}, {rgba.blue:.2f}, {rgba.alpha:.2f})"

    def _str_to_rgba(self, s: str) -> Gdk.RGBA:
        m = re.match(r"rgba\(([\d.]+), ([\d.]+), ([\d.]+), ([\d.]+)\)", s)
        if not m:
            return Gdk.RGBA(0,0,0,1)
        r, g, b, a = map(float, m.groups())
        return Gdk.RGBA(r, g, b, a)

    def _notify_change(self):
        if self._on_change_callback and not self._is_temporary:
            self._on_change_callback(self)

    @property
    def size(self) -> int:
        return self._size

    @size.setter
    def size(self, value: int):
        if self._size != value:
            self._size = value
            self._notify_change()

    @property
    def primary_color(self) -> Gdk.RGBA:
        return self._str_to_rgba(self._primary_color_str)

    @primary_color.setter
    def primary_color(self, value: Gdk.RGBA):
        new_str = self._rgba_to_str(value)
        if self._primary_color_str != new_str:
            self._primary_color_str = new_str
            self._notify_change()

    @property
    def fill_color(self) -> Gdk.RGBA:
        return self._str_to_rgba(self._fill_color_str)

    @fill_color.setter
    def fill_color(self, value: Gdk.RGBA):
        new_str = self._rgba_to_str(value)
        if self._fill_color_str != new_str:
            self._fill_color_str = new_str
            self._notify_change()

    @property
    def border_color(self) -> Gdk.RGBA:
        return self._str_to_rgba(self._border_color_str)

    @border_color.setter
    def border_color(self, value: Gdk.RGBA):
        new_str = self._rgba_to_str(value)
        if self._border_color_str != new_str:
            self._border_color_str = new_str
            self._notify_change()

    @property
    def font(self) -> str:
        return self._font

    @font.setter
    def font(self, value: str):
        if self._font != value:
            self._font = value
            self._notify_change()

    def serialize(self) -> str:
        data = {
            "mode": self.mode.name,
            "size": self.size,
            "primary_color": (self.primary_color.red, self.primary_color.green, self.primary_color.blue, self.primary_color.alpha),
            "fill_color": (self.fill_color.red, self.fill_color.green, self.fill_color.blue, self.fill_color.alpha),
            "border_color": (self.border_color.red, self.border_color.green, self.border_color.blue, self.border_color.alpha),
            "font": self.font,
        }
        return json.dumps(data)

    @classmethod
    def deserialize(cls, json_str: str, on_change_callback: Optional[Callable[['ToolOption'], None]] = None) -> "ToolOption":
        def tuple_to_rgba(t):
            if not t or len(t) != 4:
                return Gdk.RGBA(0, 0, 0, 1)
            return Gdk.RGBA(t[0], t[1], t[2], t[3])

        data = json.loads(json_str)
        mode = DrawingMode[data.get("mode", "PEN")]
        return cls(
            mode=mode,
            size=data.get("size", 10),
            primary_color=tuple_to_rgba(data.get("primary_color")),
            fill_color=tuple_to_rgba(data.get("fill_color")),
            border_color=tuple_to_rgba(data.get("border_color")),
            font=data.get("font", "Adwaita Sans"),
            on_change_callback=on_change_callback,
        )

    def copy(self, is_temporary: bool = False) -> "ToolOption":
        return ToolOption(
            mode=self.mode,
            size=self.size,
            primary_color=self.primary_color,
            fill_color=self.fill_color,
            border_color=self.border_color,
            font=self.font,
            on_change_callback=self._on_change_callback if not is_temporary else None,
            is_temporary=is_temporary,
        )

    def update_without_notify(self, **kwargs):
        if 'size' in kwargs:
            self._size = kwargs['size']
        if 'primary_color' in kwargs:
            self._primary_color_str = self._rgba_to_str(kwargs['primary_color'])
        if 'fill_color' in kwargs:
            self._fill_color_str = self._rgba_to_str(kwargs['fill_color'])
        if 'border_color' in kwargs:
            self._border_color_str = self._rgba_to_str(kwargs['border_color'])
        if 'font' in kwargs:
            self._font = kwargs['font']


class ToolOptionsManager:
    def __init__(self, settings: Settings = None):
        self.settings = settings or Settings()
        self._tool_configs = {}
        self._initialize_tools()
        self._load_from_settings()

    def _initialize_tools(self):
        for mode in DrawingMode:
            self._tool_configs[mode] = ToolOption(
                mode,
                on_change_callback=self._on_tool_changed
            )

    def _load_from_settings(self):
        for mode in DrawingMode:
            key = f"tool_{mode.name.lower()}"
            saved_config = self.settings.get_tool_config_item(key)

            if saved_config:
                try:
                    tool_option = ToolOption.deserialize(
                        saved_config,
                        on_change_callback=self._on_tool_changed
                    )
                    self._tool_configs[mode] = tool_option
                except (json.JSONDecodeError, KeyError, ValueError) as e:
                    print(f"Failed to load tool config for {mode.name}: {e}")

    def _on_tool_changed(self, tool_option: ToolOption):
        key = f"tool_{tool_option.mode.name.lower()}"
        serialized = tool_option.serialize()
        self.settings.set_tool_config_item(key, serialized)

    def get_tool(self, mode: DrawingMode) -> ToolOption:
        return self._tool_configs[mode]

    def export_config(self) -> dict:
        return {
            mode.name: tool.serialize()
            for mode, tool in self._tool_configs.items()
        }

class ToolConfig:

    TEXT_COLORS = [
        (Gdk.RGBA(0.65,0.11,0.18, 1), _("Red")),
        (Gdk.RGBA(0.15,0.64,0.41, 1), _("Green")),
        (Gdk.RGBA(0.1,0.37,0.71, 1), _("Blue")),
        (Gdk.RGBA(0.9,0.65,0.04, 1), _("Yellow")),
        (Gdk.RGBA(0,0,0, 1), _("Black")),
        (Gdk.RGBA(1.0, 1.0, 1.0, 1), _("White")),
    ]

    TEXT_BACKGROUND_COLORS = [
        (Gdk.RGBA(0.96,0.38,0.32, 1), _("Red")),
        (Gdk.RGBA(0.56,0.94,0.64, 1), _("Green")),
        (Gdk.RGBA(0.6,0.76,0.95, 1), _("Blue")),
        (Gdk.RGBA(0.98,0.94,0.42, 1), _("Yellow")),
        (Gdk.RGBA(1.0, 1.0, 1.0, 1), _("White")),
        (Gdk.RGBA(0,0,0, 1), _("Black")),
        (Gdk.RGBA(0, 0, 0, 0), _("Transparent"))
    ]

    def __init__(
        self,
        mode: DrawingMode,
        icon: str,
        column: int,
        row: int,
        shown_stack: str = "empty",
        has_scale: bool = False,
        has_primary_color: bool = False,
        match_primary_to_secondary = False,
        primary_color_list = None,
        secondary_color_list = None,

    ) -> None:
        self.mode = mode
        self.icon = icon
        self.column = column
        self.row = row
        self.shown_stack = shown_stack
        self.has_scale = has_scale
        self.has_primary_color = has_primary_color
        self.primary_color_list = primary_color_list
        self.secondary_color_list = secondary_color_list
        self.match_primary_to_secondary = match_primary_to_secondary

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
                primary_color_list=ToolConfig.TEXT_COLORS,
                secondary_color_list=ToolConfig.TEXT_BACKGROUND_COLORS
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
                shown_stack="fill",
                has_scale=True,
                has_primary_color=True,
            ),
            ToolConfig(
                mode=DrawingMode.CIRCLE,
                icon="circle-outline-thick-symbolic",
                column=1,
                row=1,
                shown_stack="fill",
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
                primary_color_list=[
                        (Gdk.RGBA(0.88, 0.11, 0.14, 0.7), _("Red")),
                        (Gdk.RGBA(0.18, 0.76, 0.49, 0.7), _("Green")),
                        (Gdk.RGBA(0.21, 0.52, 0.89, 0.7), _("Blue")),
                        (Gdk.RGBA(0.96, 0.83, 0.18, 0.7), _("Yellow")),
                        (Gdk.RGBA(0.51, 0.24, 0.61, 0.7), _("Purple")),
                        (Gdk.RGBA(1.0, 1.0, 1.0, 0.7), _("White")),
                    ]
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
                match_primary_to_secondary=True,
                primary_color_list=ToolConfig.TEXT_COLORS,
                secondary_color_list=ToolConfig.TEXT_BACKGROUND_COLORS
            ),
        ]
