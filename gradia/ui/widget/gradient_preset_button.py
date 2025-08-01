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
from gi.repository import Adw, Gtk
from typing import Callable, Optional
from gi.repository import Gtk, GObject
from gradia.utils.colors import HexColor
from gradia.graphics.gradient import GradientBackground, Gradient
from gradia.app_constants import PREDEFINED_GRADIENTS

class GradientPresetButton(Gtk.MenuButton):
    __gtype_name__ = "GradiaGradientPresetButton"

    def __init__(
        self,
        callback: Optional[Callable[[Gradient], None]] = None,
        **kwargs
    ) -> None:
        super().__init__(**kwargs)
        self.callback = callback
        self.set_icon_name("view-grid-symbolic")
        self.set_valign(Gtk.Align.CENTER)
        self.add_css_class("flat")
        self._setup_popover()

    def _setup_popover(self) -> None:
        self.popover = Gtk.Popover()
        self.set_popover(self.popover)

        main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        main_box.set_spacing(8)
        main_box.set_margin_top(8)
        main_box.set_margin_bottom(8)
        main_box.set_margin_start(8)
        main_box.set_margin_end(8)

        self.flowbox = Gtk.FlowBox()
        self.flowbox.set_max_children_per_line(3)
        self.flowbox.set_selection_mode(Gtk.SelectionMode.NONE)
        self.flowbox.set_homogeneous(True)
        self.flowbox.set_row_spacing(8)
        self.flowbox.set_column_spacing(8)

        self._create_gradient_buttons()

        main_box.append(self.flowbox)
        self.popover.set_child(main_box)

    def _create_gradient_buttons(self) -> None:
        for i, gradient in enumerate(PREDEFINED_GRADIENTS[:6]):
            gradient_name = f"gradient-preset-{i}"
            button = Gtk.Button(
                name=gradient_name,
                focusable=True,
                can_focus=True,
                width_request=60,
                height_request=40
            )
            button.add_css_class("gradient-preset")
            self._apply_gradient_to_button(button, gradient)
            button.connect("clicked", self._on_gradient_button_clicked, gradient)
            self.flowbox.append(button)

    def _apply_gradient_to_button(self, button: Gtk.Button, gradient: Gradient) -> None:
        css = f"""
            button.gradient-preset {{
                background-image: {gradient.to_css()};
            }}
        """
        css_provider = Gtk.CssProvider()
        css_provider.load_from_string(css)
        button.get_style_context().add_provider(
            css_provider,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION + 3
        )

    def _on_gradient_button_clicked(self, button: Gtk.Button, gradient: Gradient) -> None:
        self.popover.popdown()
        if self.callback:
            self.callback(gradient)

    def set_callback(self, callback: Callable[[Gradient], None]) -> None:
        self.callback = callback

    def set_gradient_presets(self, gradients: list[Gradient]) -> None:
        # Clear existing buttons
        child = self.flowbox.get_first_child()
        while child:
            next_child = child.get_next_sibling()
            self.flowbox.remove(child)
            child = next_child

        # Add new gradient buttons
        for i, gradient in enumerate(gradients[:6]):
            gradient_name = f"gradient-preset-{i}"
            button = Gtk.Button(
                name=gradient_name,
                focusable=True,
                can_focus=True,
                width_request=60,
                height_request=40
            )
            button.add_css_class("gradient-preset")
            self._apply_gradient_to_button(button, gradient)
            button.connect("clicked", self._on_gradient_button_clicked, gradient)
            self.flowbox.append(button)
