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

from gi.repository import Adw, GLib, GObject, Gdk, Gio, Gtk, Pango

from gradia.backend.settings import Settings
from gradia.constants import rootdir  # pyright: ignore
from gradia.overlay.drawing_actions import DrawingMode


class ToolConfig:
    def __init__(
        self,
        mode: DrawingMode,
        icon: str,
        column: int,
        row: int,
        stack_page: Optional[str] = None,
        color_stack_page: Optional[str] = None
    ) -> None:
        self.mode = mode
        self.icon = icon
        self.column = column
        self.row = row
        self.stack_page = stack_page
        self.color_stack_page = color_stack_page

    @staticmethod
    def get_all_tools() -> list['ToolConfig']:
        """Return all tool configurations."""

        return [
            ToolConfig(DrawingMode.SELECT, "pointer-primary-click-symbolic", 0, 0, None, None),
            ToolConfig(DrawingMode.PEN, "edit-symbolic", 1, 0, "size", "stroke"),
            ToolConfig(DrawingMode.TEXT, "text-insert2-symbolic", 2, 0, "font", "stroke"),
            ToolConfig(DrawingMode.LINE, "draw-line-symbolic", 3, 0, "size", "stroke"),
            ToolConfig(DrawingMode.ARROW, "arrow1-top-right-symbolic", 4, 0, "size", "stroke"),
            ToolConfig(DrawingMode.SQUARE, "box-small-outline-symbolic", 0, 1, "fill", "stroke"),
            ToolConfig(DrawingMode.CIRCLE, "circle-outline-thick-symbolic", 1, 1, "fill", "stroke"),
            ToolConfig(DrawingMode.HIGHLIGHTER, "marker-symbolic", 2, 1, None, "highlighter"),
            ToolConfig(DrawingMode.CENSOR, "checkerboard-big-symbolic", 3, 1, None, None),
            ToolConfig(DrawingMode.NUMBER, "one-circle-symbolic", 4, 1, "number_radius", "stroke"),
        ]


@Gtk.Template(resource_path=f"{rootdir}/ui/drawing_tools_group.ui")
class DrawingToolsGroup(Adw.PreferencesGroup):
    __gtype_name__ = "GradiaDrawingToolsGroup"

    tools_grid: Gtk.Grid = Gtk.Template.Child()

    color_stack_row: Adw.ActionRow = Gtk.Template.Child()
    color_stack: Gtk.Stack = Gtk.Template.Child()
    stroke_color_button: Gtk.ColorButton = Gtk.Template.Child()
    highlighter_color_button: Gtk.ColorButton = Gtk.Template.Child()
    size_scale: Gtk.Scale = Gtk.Template.Child()
    number_radius_scale: Gtk.Scale = Gtk.Template.Child()

    stack_row: Adw.ActionRow = Gtk.Template.Child()
    fill_font_stack: Gtk.Stack = Gtk.Template.Child()

    fill_color_button: Gtk.ColorButton = Gtk.Template.Child()
    font_string_list: Gtk.StringList = Gtk.Template.Child()

    tools_config = ToolConfig.get_all_tools()

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)

        self.settings = Settings()

        self.tool_buttons: dict[DrawingMode, Gtk.ToggleButton] = {}
        self.current_stack_page_name: str = None
        self.current_color_stack_page_name: str = None

        self.fonts = ["Caveat", "Adwaita Sans", "Adwaita Mono", "Noto Sans"]

        self._setup_annotation_tools_group()
        self._setup_font_dropdown()
        self._restore_settings()

        try:
            saved_mode = DrawingMode(self.settings.draw_mode)
        except ValueError:
            saved_mode = DrawingMode.PEN


        if saved_mode in self.tool_buttons:
            self.tool_buttons[saved_mode].set_active(True)
        else:
            self.tool_buttons[DrawingMode.PEN].set_active(True)

        self._initialize_all_actions()

    """
    Setup Methods
    """

    def _setup_annotation_tools_group(self) -> None:
        # Sets default color values for color buttons
        self.stroke_color_button.set_rgba(Gdk.RGBA(red=1, green=1, blue=1, alpha=1))
        self.highlighter_color_button.set_rgba(Gdk.RGBA(red=1, green=1, blue=0, alpha=0.5))
        self.fill_color_button.set_rgba(Gdk.RGBA(red=0, green=0, blue=0, alpha=0))

        for tool_config in self.tools_config:
            button = Gtk.ToggleButton(
                icon_name=tool_config.icon,
                tooltip_text=tool_config.mode.label(),
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

    def _initialize_all_actions(self) -> None:
        self._activate_color_action("pen-color", self.settings.pen_color)
        self._activate_color_action("highlighter-color", self.settings.highlighter_color)
        self._activate_color_action("fill-color", self.settings.fill_color)

        self._activate_double_action("pen-size", self.settings.pen_size)
        self._activate_double_action("number-radius", self.settings.number_radius)

        app = Gio.Application.get_default()
        if app:
            action = app.lookup_action("font")
            if action:
                action.activate(GLib.Variant('s', self.settings.font))

        self._activate_draw_mode_action(DrawingMode(self.settings.draw_mode))

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
        self.settings.pen_color = rgba
        self._activate_color_action("pen-color", rgba)

    @Gtk.Template.Callback()
    def _on_highlighter_color_set(self, button: Gtk.ColorButton, *args) -> None:
        rgba = button.get_rgba()
        self.settings.highlighter_color = rgba
        self._activate_color_action("highlighter-color", rgba)

    @Gtk.Template.Callback()
    def _on_fill_color_set(self, button: Gtk.ColorButton, *args) -> None:
        rgba = button.get_rgba()
        self.settings.fill_color = rgba
        self._activate_color_action("fill-color", rgba)

    @Gtk.Template.Callback()
    def _on_size_changed(self, scale: Gtk.Scale, *args) -> None:
        size_value = scale.get_value()
        self.settings.pen_size = size_value
        self._activate_double_action("pen-size", size_value)

    @Gtk.Template.Callback()
    def _on_number_radius_changed(self, scale: Gtk.Scale, *args) -> None:
        size_value = scale.get_value()
        self.settings.number_radius = size_value
        self._activate_double_action("number-radius", size_value)

    @Gtk.Template.Callback()
    def _on_font_selected(self, dropdown: Gtk.DropDown, _param: GObject.ParamSpec, *args) -> None:
        selected_index = dropdown.get_selected()
        if 0 <= selected_index < len(self.fonts):
            font_name = self.fonts[selected_index]
            self.settings.font = font_name
            app = Gio.Application.get_default()
            if app:
                action = app.lookup_action("font")
                if action:
                    action.activate(GLib.Variant('s', font_name))

    def _on_button_toggled(self, button: Gtk.ToggleButton, drawing_mode: DrawingMode) -> None:
        if button.get_active():
            self._deactivate_other_tools(drawing_mode)
            self._update_stack_for_mode(drawing_mode)
            self._update_color_stack_for_mode(drawing_mode)
            self.settings.draw_mode = drawing_mode.value
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
            self.current_stack_page_name = required_page

    def _update_color_stack_for_mode(self, drawing_mode: DrawingMode) -> None:
        required_page = None
        for tool_config in self.tools_config:
            if tool_config.mode == drawing_mode:
                required_page = tool_config.color_stack_page
                break

        if required_page is None:
            self.color_stack_row.set_sensitive(False)
        else:
            self.color_stack_row.set_sensitive(True)
            self.color_stack.set_visible_child_name(required_page)
            self.current_color_stack_page_name = required_page

    def _activate_draw_mode_action(self, drawing_mode: DrawingMode) -> None:
        app = Gio.Application.get_default()
        if app:
            action = app.lookup_action("draw-mode")
            if action:
                action.activate(GLib.Variant('s', drawing_mode.value))

    def _ensure_one_tool_active(self, button: Gtk.ToggleButton, drawing_mode: DrawingMode) -> None:
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

    def _restore_settings(self) -> None:
        """Restore all settings from persistent storage."""

        self.stroke_color_button.set_rgba(self.settings.pen_color)
        self.highlighter_color_button.set_rgba(self.settings.highlighter_color)
        self.fill_color_button.set_rgba(self.settings.fill_color)

        self.size_scale.set_value(self.settings.pen_size)
        self.number_radius_scale.set_value(self.settings.number_radius)

        saved_font = self.settings.font
        if saved_font in self.fonts:
            font_index = self.fonts.index(saved_font)
            GLib.idle_add(self._set_font_selection, font_index)

    def _set_font_selection(self, index: int) -> bool:
        font_dropdown = self.get_template_child(Gtk.DropDown, "font_dropdown")
        if font_dropdown:
            font_dropdown.set_selected(index)
        return False
