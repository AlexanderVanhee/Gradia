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

from gi.repository import GObject, Gtk, Adw, Gdk, Gio, GLib, Pango
from gradia.overlay.drawing_actions import DrawingMode
from gradia.constants import rootdir  # pyright: ignore


class ToolConfig:
    def __init__(self, mode: DrawingMode, icon: str, column: int, row: int, stack_page: str = None):
        self.mode = mode
        self.icon = icon
        self.column = column
        self.row = row
        self.stack_page = stack_page

    @staticmethod
    def get_all_tools():
        """Return all tool configurations."""
        return [
            ToolConfig(DrawingMode.SELECT, "pointer-primary-click-symbolic", 0, 0, None),
            ToolConfig(DrawingMode.PEN, "edit-symbolic", 1, 0, "size"),
            ToolConfig(DrawingMode.TEXT, "text-insert2-symbolic", 2, 0, "font"),
            ToolConfig(DrawingMode.LINE, "draw-line-symbolic", 3, 0, "size"),
            ToolConfig(DrawingMode.ARROW, "arrow1-top-right-symbolic", 4, 0, "size"),
            ToolConfig(DrawingMode.SQUARE, "box-small-outline-symbolic", 0, 1, "fill"),
            ToolConfig(DrawingMode.CIRCLE, "circle-outline-thick-symbolic", 1, 1, "fill"),
            ToolConfig(DrawingMode.HIGHLIGHTER, "marker-symbolic", 2, 1, None),
            ToolConfig(DrawingMode.CENSOR, "checkerboard-big-symbolic", 3, 1, None),
            ToolConfig(DrawingMode.NUMBER, "one-circle-symbolic", 4, 1, "number_radius"),
        ]


@Gtk.Template(resource_path=f"{rootdir}/ui/drawing_tools_group.ui")
class DrawingToolsGroup(Adw.PreferencesGroup):
    __gtype_name__ = "GradiaDrawingToolsGroup"

    tools_grid: Gtk.Grid = Gtk.Template.Child()

    stroke_color_button: Gtk.ColorButton = Gtk.Template.Child()

    stack_row: Adw.ActionRow = Gtk.Template.Child()
    fill_font_stack: Gtk.Stack = Gtk.Template.Child()

    fill_color_button: Gtk.ColorButton = Gtk.Template.Child()
    font_string_list: Gtk.StringList = Gtk.Template.Child()

    # Tool configurations accessible at class level
    tools_config = ToolConfig.get_all_tools()

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)

        self.tool_buttons: dict[DrawingMode, Gtk.ToggleButton] = {}
        self.current_stack_page = None

        self.fonts = ["Caveat", "Adwaita Sans", "Adwaita Mono", "Noto Sans"]

        self._setup_annotation_tools_group()
        self._setup_font_dropdown()

        self.tool_buttons[DrawingMode.PEN].set_active(True)

    """
    Setup Methods
    """

    def _setup_annotation_tools_group(self) -> None:
        self.stroke_color_button.set_rgba(Gdk.RGBA(red=0, green=0, blue=0, alpha=0))
        self.fill_color_button.set_rgba(Gdk.RGBA(red=0, green=0, blue=0, alpha=0))

        for tool_config in self.tools_config:
            button = Gtk.ToggleButton(
                icon_name=tool_config.icon,
                tooltip_text=tool_config.mode.value,
                width_request=40,
                height_request=40,
                css_classes=["flat", "circular"]
            )
            button.connect("toggled", self._on_button_toggled, tool_config.mode)
            self.tools_grid.attach(button, tool_config.column, tool_config.row, 1, 1)
            self.tool_buttons[tool_config.mode] = button

    def _setup_font_dropdown(self) -> None:
        for font in self.fonts:
            self.font_string_list.append(font)

    """
    Callbacks
    """

    # TODO: Define type for `list_item` parameter
    @Gtk.Template.Callback()
    def _font_factory_setup(self, _factory: Gtk.SignalListItemFactory, list_item, *args) -> None:
        label = Gtk.Label(halign=Gtk.Align.START)
        list_item.set_child(label)

    # TODO: Define type for `list_item` parameter
    @Gtk.Template.Callback()
    def _font_factory_bind(self, _factory: Gtk.SignalListItemFactory, list_item, *args) -> None:
        label = list_item.get_child()
        string_object = list_item.get_item()
        font_name = string_object.get_string()
        label.set_text(font_name)

        attr_list = Pango.AttrList()
        font_desc = Pango.FontDescription.from_string(f"{font_name} 12")
        attr_font = Pango.attr_font_desc_new(font_desc)
        attr_list.insert(attr_font)
        label.set_attributes(attr_list)

    @Gtk.Template.Callback()
    def _on_reset_fill_clicked(self, _button: Gtk.Button, *args) -> None:
        self.fill_color_button.set_rgba(Gdk.RGBA(0, 0, 0, 0))
        self.fill_color_button.emit("color-set")

    @Gtk.Template.Callback()
    def _on_pen_color_set(self, button: Gtk.ColorButton, *args) -> None:
        rgba = button.get_rgba()
        self._activate_color_action("pen-color", rgba)

    @Gtk.Template.Callback()
    def _on_fill_color_set(self, button: Gtk.ColorButton, *args) -> None:
        rgba = button.get_rgba()
        self._activate_color_action("fill-color", rgba)

    @Gtk.Template.Callback()
    def _on_size_changed(self, scale: Gtk.Scale, *args) -> None:
        size_value = scale.get_value()
        self._activate_double_action("pen-size", size_value)

    @Gtk.Template.Callback()
    def _on_number_radius_changed(self, scale: Gtk.Scale, *args) -> None:
        size_value = scale.get_value()
        self._activate_double_action("number-radius", size_value)

    @Gtk.Template.Callback()
    def _on_font_selected(self, dropdown: Gtk.DropDown, _param: GObject.ParamSpec, *args) -> None:
        selected_index = dropdown.get_selected()
        if 0 <= selected_index < len(self.fonts):
            font_name = self.fonts[selected_index]
            app = Gio.Application.get_default()
            if app:
                action = app.lookup_action("font")
                if action:
                    action.activate(GLib.Variant('s', font_name))

    def _on_button_toggled(self, button: Gtk.ToggleButton, drawing_mode: DrawingMode) -> None:
        if button.get_active():
            self._deactivate_other_tools(drawing_mode)
            self._update_stack_for_mode(drawing_mode)
            self._activate_draw_mode_action(drawing_mode)
        else:
            self._ensure_one_tool_active(button, drawing_mode)

    """
    Internal Methods
    """

    def _deactivate_other_tools(self, current_mode: DrawingMode) -> None:
        for mode, button in self.tool_buttons.items():
            if mode != current_mode and button.get_active():
                button.set_active(False)

    def _update_stack_for_mode(self, drawing_mode: DrawingMode) -> None:
        required_page = None
        for tool_config in self.tools_config:
            if tool_config.mode == drawing_mode:
                required_page = tool_config.stack_page
                break

        if required_page is None:
            self.stack_row.set_sensitive(False)
        else:
            self.stack_row.set_sensitive(True)
            self.fill_font_stack.set_visible_child_name(required_page)
            self.current_stack_page = required_page

    def _activate_draw_mode_action(self, drawing_mode: DrawingMode) -> None:
        app = Gio.Application.get_default()
        if app:
            action = app.lookup_action("draw-mode")
            if action:
                action.activate(GLib.Variant('s', drawing_mode.value))

    def _ensure_one_tool_active(self, button, drawing_mode: DrawingMode) -> None:
        any_active = any(
            btn.get_active() for mode, btn in self.tool_buttons.items() if mode != drawing_mode
        )
        if not any_active:
            button.set_active(True)

    def _activate_color_action(self, action_name: str, rgba: Gdk.RGBA) -> None:
        app = Gio.Application.get_default()
        if app:
            action = app.lookup_action(action_name)
            if action:
                color_str = f"{rgba.red:.3f},{rgba.green:.3f},{rgba.blue:.3f},{rgba.alpha:.3f}"
                action.activate(GLib.Variant('s', color_str))

    def _activate_double_action(self, action_name: str, size_value: float) -> None:
        app = Gio.Application.get_default()
        if app:
            action = app.lookup_action(action_name)
            if action:
                action.activate(GLib.Variant('d', size_value))
