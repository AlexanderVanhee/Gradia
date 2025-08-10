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
from typing import Optional
from gi.repository import Gtk, Gdk, GObject, GLib
from gradia.overlay.drawing_actions import DrawingMode
from gradia.ui.widget.quick_color_picker import QuickColorPicker, SimpleColorPicker
from gradia.ui.widget.drawing_tools_grid import DrawingToolsGrid
from gradia.backend.tool_config import ToolOption, ToolOptionsManager, ToolConfig
from gradia.ui.widget.font_dropdown import FontDropdown
from gradia.constants import rootdir


@Gtk.Template(resource_path=f"{rootdir}/ui/drawing_tools_group.ui")
class DrawingToolsGroup(Gtk.Box):
    __gtype_name__ = "GradiaDrawingToolsGroup"

    size_scale = Gtk.Template.Child()
    color_picker = Gtk.Template.Child()
    extra_stack = Gtk.Template.Child()
    extra_stack_revealer = Gtk.Template.Child()
    fill_0 = Gtk.Template.Child()
    fill_1 = Gtk.Template.Child()
    fill_2 = Gtk.Template.Child()
    outline_1 = Gtk.Template.Child()
    outline_2 = Gtk.Template.Child()
    drawing_tools_grid = Gtk.Template.Child()
    font_dropdown = Gtk.Template.Child()

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.tool_manager = ToolOptionsManager()
        self.current_tool_config: Optional[ToolConfig] = None
        self.current_tool_option: Optional[ToolOption] = None
        self._updating_ui = False

    @Gtk.Template.Callback()
    def on_tool_changed(self, grid: DrawingToolsGrid, tool_config: ToolConfig):
        self.current_tool_config = tool_config
        self.current_tool_option = self.tool_manager.get_tool(tool_config.mode)
        self._update_ui_for_tool(tool_config, self.current_tool_option)
        self.trigger_action()

    def _update_ui_for_tool(self, tool_config: ToolConfig, tool_option: ToolOption):
        self._updating_ui = True

        self.size_scale.set_sensitive(tool_config.has_scale)
        self.color_picker.set_sensitive(tool_config.has_primary_color)
        self.extra_stack.set_visible_child_name(tool_config.shown_stack)
        self.extra_stack_revealer.set_reveal_child(tool_config.shown_stack != "empty")

        if tool_config.mode == DrawingMode.HIGHLIGHTER:
            self.color_picker.quick_colors_alpha = 0.7
        else:
            self.color_picker.quick_colors_alpha = 1.0

        if tool_config.has_scale:
            self.size_scale.set_value(tool_option.size)

        if tool_config.has_primary_color:
            self.color_picker.set_color(tool_option.primary_color)

        self.fill_0.set_color(tool_option.fill_color, emit=False)
        self.fill_1.set_color(tool_option.fill_color, emit=False)
        self.fill_2.set_color(tool_option.fill_color, emit=False)
        self.outline_1.set_color(tool_option.border_color, emit=False)
        self.outline_2.set_color(tool_option.border_color, emit=False)
        self.font_dropdown.set_selected_font(tool_option.font)

        self._updating_ui = False

    @Gtk.Template.Callback()
    def on_fill_color_changed(self, button: SimpleColorPicker, color: Gdk.RGBA):
        if self._updating_ui or self.current_tool_option is None:
            return

        self.current_tool_option.fill_color = color
        self.fill_0.set_color(color, emit=False)
        self.fill_1.set_color(color, emit=False)
        self.fill_2.set_color(color, emit=False)
        self.trigger_action()

    @Gtk.Template.Callback()
    def on_outline_color_changed(self, button: SimpleColorPicker, color: Gdk.RGBA):
        if self._updating_ui or self.current_tool_option is None:
            return

        self.current_tool_option.border_color = color
        self.outline_1.set_color(color, emit=False)
        self.outline_2.set_color(color, emit=False)
        self.trigger_action()

    @Gtk.Template.Callback()
    def on_size_scale_changed(self, adjustment: Gtk.Adjustment):
        if self._updating_ui or self.current_tool_option is None:
            return

        self.current_tool_option.size = int(adjustment.get_value())
        self.trigger_action()

    @Gtk.Template.Callback()
    def on_primary_color_changed(self, picker: QuickColorPicker, color: Gdk.RGBA):
        if self._updating_ui or self.current_tool_option is None:
            return

        self.current_tool_option.primary_color = color
        self.trigger_action()

    @Gtk.Template.Callback()
    def on_font_changed(self, dropdown: FontDropdown, font: str):
        if self._updating_ui or self.current_tool_option is None:
            return

        self.current_tool_option.font = font
        self.trigger_action()

    def get_current_tool(self) -> Optional[ToolOption]:
        if self.current_tool_config is None:
            return None
        return self.tool_manager.get_tool(self.current_tool_config.mode)

    def set_current_tool(self, mode: DrawingMode):
        self.drawing_tools_grid.set_current_tool(mode)
        self.current_tool_config = next(
            (tc for tc in ToolConfig.get_all_tools_positions() if tc.mode == mode), None
        )
        if self.current_tool_config:
            self.current_tool_option = self.tool_manager.get_tool(mode)
            self._update_ui_for_tool(self.current_tool_config, self.current_tool_option)
            self.trigger_action()

    def trigger_action(self):
        window = self.get_root()
        if window:
            action = window.lookup_action("tool-option-changed")
            if action and self.current_tool_option:
                data_json = self.current_tool_option.serialize()
                param = GLib.Variant('s', data_json)
                action.activate(param)



