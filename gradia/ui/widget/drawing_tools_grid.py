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

from typing import Optional, Callable
from gi.repository import Gtk, GObject
from gradia.overlay.drawing_actions import DrawingMode
from gradia.backend.settings import Settings
from gradia.backend.tool_config import ToolConfig
settings = Settings()

class DrawingToolsGrid(Gtk.Grid):
    __gtype_name__ = "GradiaDrawingToolsGrid"

    __gsignals__ = {
        "tool-changed": (GObject.SignalFlags.RUN_FIRST, None, (object,))
    }

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.set_row_spacing(9)
        self.set_column_spacing(18)
        self.set_column_homogeneous(True)
        self.set_row_homogeneous(True)

        self._buttons = {}
        self._current_tool = None
        self._tool_configs = {}

        self._create_tool_buttons()

        self.connect("realize", self._on_realize)

    def _on_realize(self, widget):
        initial_mode = DrawingMode(settings.draw_mode)
        self._select_tool(initial_mode)
        if initial_mode in self._tool_configs:
            self._current_tool = initial_mode
            self.emit("tool-changed", self._tool_configs[initial_mode])

        widget.disconnect_by_func(self._on_realize)

    def _create_tool_buttons(self):
        tools = ToolConfig.get_all_tools_positions()

        for tool_config in tools:
            button = Gtk.ToggleButton(
                icon_name=tool_config.icon,
                tooltip_text=tool_config.mode.label(),
                width_request=40,
                height_request=40,
                css_classes=["flat", "circular"]
            )

            button.get_first_child().set_pixel_size(18)

            self._tool_configs[tool_config.mode] = tool_config
            self._buttons[tool_config.mode] = button

            button.connect("toggled", self._on_button_toggled, tool_config.mode)

            self.attach(button, tool_config.column, tool_config.row, 1, 1)

    def _on_button_toggled(self, button: Gtk.ToggleButton, mode: DrawingMode):
        if button.get_active():
            for other_mode, other_button in self._buttons.items():
                if other_mode != mode and other_button.get_active():
                    other_button.handler_block_by_func(self._on_button_toggled)
                    other_button.set_active(False)
                    other_button.handler_unblock_by_func(self._on_button_toggled)

            old_tool = self._current_tool
            self._current_tool = mode

            settings.draw_mode = mode.value

            if old_tool != mode:
                tool_config = self._tool_configs[mode]
                self.emit("tool-changed", tool_config)
        else:
            if self._current_tool == mode:
                button.handler_block_by_func(self._on_button_toggled)
                button.set_active(True)
                button.handler_unblock_by_func(self._on_button_toggled)

    def _select_tool(self, mode: DrawingMode):
        if mode in self._buttons:
            self._buttons[mode].set_active(True)

    def get_current_tool(self) -> Optional[ToolConfig]:
        if self._current_tool:
            return self._tool_configs[self._current_tool]
        return None

    def set_current_tool(self, mode: DrawingMode):
        self._select_tool(mode)
