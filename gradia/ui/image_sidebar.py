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

from typing import Callable, Optional

from gi.repository import Gtk, Gio, Adw, Gdk, GLib

from gradia.constants import PREDEFINED_GRADIENTS
from gradia.overlay.drawing_actions import DrawingMode
from gradia.graphics.gradient import GradientBackground
from gradia.utils.colors import hex_to_rgba, rgba_to_hex, HexColor

@Gtk.Template(resource_path="/be/alexandervanhee/gradia/ui/image_sidebar.ui")
class ImageSidebar(Adw.Bin):
    __gtype_name__ = "GradiaImageSidebar"

    # `annotation_tools_group` template children
    tools_grid: Gtk.Grid = Gtk.Template.Child()

    reset_fill_button: Gtk.Button = Gtk.Template.Child()
    fill_row: Adw.ActionRow = Gtk.Template.Child()
    fill_color_button: Gtk.ColorButton = Gtk.Template.Child()

    stroke_color_button: Gtk.ColorButton = Gtk.Template.Child()

    # `gradient_selector_group` template children
    start_color_button: Gtk.ColorDialogButton = Gtk.Template.Child()
    end_color_button: Gtk.ColorDialogButton = Gtk.Template.Child()

    angle_spin_row: Adw.SpinRow = Gtk.Template.Child()
    angle_adjustment: Gtk.Adjustment = Gtk.Template.Child()

    gradient_popover: Gtk.Popover = Gtk.Template.Child()
    popover_flowbox: Gtk.FlowBox = Gtk.Template.Child()

    # `image_options_group` template children
    padding_row: Adw.SpinRow = Gtk.Template.Child()
    padding_adjustment: Gtk.Adjustment = Gtk.Template.Child()

    corner_radius_row: Adw.SpinRow = Gtk.Template.Child()
    corner_radius_adjustment: Gtk.Adjustment = Gtk.Template.Child()

    aspect_ratio_entry: Gtk.Entry = Gtk.Template.Child()
    shadow_strength_scale: Gtk.Scale = Gtk.Template.Child()

    # `file_info_group` template children
    filename_row: Adw.ActionRow = Gtk.Template.Child()
    location_row: Adw.ActionRow = Gtk.Template.Child()
    processed_size_row: Adw.ActionRow = Gtk.Template.Child()

    def __init__(
        self,
        gradient: GradientBackground,
        gradient_callback: Optional[Callable[[GradientBackground], None]],
        on_padding_changed: Callable[[Adw.SpinRow], None],
        on_corner_radius_changed: Callable[[Adw.SpinRow], None],
        on_aspect_ratio_changed: Callable[[Gtk.Entry], None],
        on_shadow_strength_changed: Callable[[Gtk.Scale], None],
        **kwargs
    ) -> None:
        super().__init__(**kwargs)

        self.gradient: GradientBackground = gradient
        self.gradient_callback: Optional[Callable[[GradientBackground], None]] = gradient_callback

        self._setup_annotation_tools_group()
        self._setup_gradient_popover()
        self._setup_gradient_selector_group()
        self._setup_image_options_group(
            on_padding_changed,
            on_corner_radius_changed,
            on_aspect_ratio_changed,
            on_shadow_strength_changed
        )

    """
    Setup Methods
    """

    def _setup_annotation_tools_group(self) -> None:
        # Set default values for color buttons
        self.fill_color_button.set_rgba(Gdk.RGBA(red=0, green=0, blue=0, alpha=0))
        self.stroke_color_button.set_rgba(Gdk.RGBA(red=1, green=1, blue=1, alpha=1))

        tools_data = [
            (DrawingMode.SELECT, "pointer-primary-click-symbolic", 0, 0),
            (DrawingMode.PEN, "edit-symbolic", 1, 0),
            (DrawingMode.TEXT, "text-insert2-symbolic", 2, 0),
            (DrawingMode.LINE, "draw-line-symbolic", 3, 0),
            (DrawingMode.ARROW, "arrow1-top-right-symbolic", 4, 0),
            (DrawingMode.SQUARE, "box-small-outline-symbolic", 0, 1),
            (DrawingMode.CIRCLE, "circle-outline-thick-symbolic", 1, 1),
            (DrawingMode.HIGHLIGHTER, "marker-symbolic", 2, 1),
            (DrawingMode.CENSOR, "checkerboard-big-symbolic", 3, 1),
            #(DrawingMode.NUMBER, "one-circle-symbolic", 4, 1),
        ]

        fill_sensitive_modes = {DrawingMode.SQUARE, DrawingMode.CIRCLE}
        tool_buttons = {}

        def on_button_toggled(button: Gtk.ToggleButton, drawing_mode: DrawingMode) -> None:
            if button.get_active():
                for mode_key, btn in tool_buttons.items():
                    if mode_key != drawing_mode and btn.get_active():
                        btn.set_active(False)

                self.fill_row.set_sensitive(drawing_mode in fill_sensitive_modes)
                app = Gio.Application.get_default()
                if app:
                    action = app.lookup_action("draw-mode")
                    if action:
                        variant = GLib.Variant('s', drawing_mode.value)
                        action.activate(variant)
            else:
                any_active = any(
                    btn.get_active() for mode_key, btn in tool_buttons.items() if mode_key != drawing_mode
                )
                if not any_active:
                    button.set_active(True)

        for drawing_mode, icon_name, col, row in tools_data:
            button = Gtk.ToggleButton(
                icon_name=icon_name,
                tooltip_text=drawing_mode.value,
                width_request=40,
                height_request=40,
                css_classes=["flat", "circular"]
            )
            button.connect("toggled", on_button_toggled, drawing_mode)
            self.tools_grid.attach(button, col, row, 1, 1)
            tool_buttons[drawing_mode] = button

        # Default tool is PEN
        if DrawingMode.PEN in tool_buttons:
            tool_buttons[DrawingMode.PEN].set_active(True)

    def _setup_gradient_popover(self) -> None:
        for i, (start, end, angle) in enumerate(PREDEFINED_GRADIENTS):
            gradient_name = f"gradient-preview-{i}"

            css = f"""
                button#{gradient_name} {{
                    background-image: linear-gradient({angle}deg, {start}, {end});
                    min-width: 60px;
                    min-height: 40px;
                    background-size: cover;
                    border-radius: 10px;
                    border: 1px solid rgba(0,0,0,0.1);
                    transition: filter 0.3s ease;
                }}
                button#{gradient_name}:hover {{
                    filter: brightness(1.2);
                }}
            """
            css_provider = Gtk.CssProvider()
            css_provider.load_from_string(css)
            Gtk.StyleContext.add_provider_for_display(
                Gdk.Display.get_default(),
                css_provider,
                Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
            )

            button_widget = Gtk.Button(name=gradient_name, focusable=False, can_focus=False)
            button_widget.connect("clicked", self._on_gradient_selected, start, end, angle)
            self.popover_flowbox.append(button_widget)

    def _setup_gradient_selector_group(self) -> None:
        # Set default values for angle adjustment and color buttons
        self.angle_adjustment.set_value(self.gradient.angle)

        self.start_color_button.set_rgba(hex_to_rgba(self.gradient.start_color))
        self.end_color_button.set_rgba(hex_to_rgba(self.gradient.end_color))

    def _setup_image_options_group(
        self,
        on_padding_changed: Callable[[Adw.SpinRow], None],
        on_corner_radius_changed: Callable[[Adw.SpinRow], None],
        on_aspect_ratio_changed: Callable[[Gtk.Entry], None],
        on_shadow_strength_changed: Callable[[Gtk.Scale], None],
    ) -> None:
        # Set default values for adjustments
        self.padding_adjustment.set_value(5)
        self.corner_radius_adjustment.set_value(2)

        self.padding_row.connect("output",
            on_padding_changed)

        self.corner_radius_row.connect("output",
            on_corner_radius_changed)

        self.aspect_ratio_entry.connect("changed",
            on_aspect_ratio_changed)

        self.shadow_strength_scale.connect("value-changed",
            on_shadow_strength_changed)

    """
    Callbacks
    """

    @Gtk.Template.Callback()
    def _on_reset_fill_clicked(self, _button: Gtk.Button, *args) -> None:
        self.fill_color_button.set_rgba(Gdk.RGBA(red=0, green=0, blue=0, alpha=0))
        self.fill_color_button.emit("color-set")

    @Gtk.Template.Callback()
    def _on_fill_color_set(self, button: Gtk.ColorButton, *args) -> None:
        app = Gio.Application.get_default()
        if app:
            action = app.lookup_action("fill-color")
            if action:
                rgba = button.get_rgba()
                color_str = f"{rgba.red:.3f},{rgba.green:.3f},{rgba.blue:.3f},{rgba.alpha:.3f}"
                variant = GLib.Variant('s', color_str)
                action.activate(variant)

    @Gtk.Template.Callback()
    def _on_pen_color_set(self, button: Gtk.ColorButton, *args) -> None:
        app = Gio.Application.get_default()
        if app:
            action = app.lookup_action("pen-color")
            if action:
                rgba = button.get_rgba()
                color_str = f"{rgba.red:.3f},{rgba.green:.3f},{rgba.blue:.3f},{rgba.alpha:.3f}"
                variant = GLib.Variant('s', color_str)
                action.activate(variant)

    @Gtk.Template.Callback()
    def _on_gradient_start_color_set(self, button: Gtk.ColorButton, *args) -> None:
        self.gradient.start_color = rgba_to_hex(button.get_rgba())
        self._gradient_notify()

    @Gtk.Template.Callback()
    def _on_gradient_end_color_set(self, button: Gtk.ColorButton, *args) -> None:
        self.gradient.end_color = rgba_to_hex(button.get_rgba())
        self._gradient_notify()

    @Gtk.Template.Callback()
    def _on_gradient_angle_output(self, row: Adw.SpinRow, *args) -> None:
        self.gradient.angle = int(row.get_value())
        self._gradient_notify()

    def _on_gradient_selected(self, _button: Gtk.Button, start: HexColor, end: HexColor, angle: int) -> None:
        self.gradient.start_color = start
        self.gradient.end_color = end
        self.gradient.angle = angle

        self.start_color_button.set_rgba(hex_to_rgba(start))
        self.end_color_button.set_rgba(hex_to_rgba(end))
        self.angle_spin_row.set_value(angle)

        self._gradient_notify()

        self.gradient_popover.popdown()

    """
    Internal Methods
    """

    def _gradient_notify(self) -> None:
        if self.gradient_callback:
            self.gradient_callback(self.gradient)
