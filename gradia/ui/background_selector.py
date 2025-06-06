# Copyright (C) 2025 Alexander Vanhee
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

from collections.abc import Callable
from typing import Optional
from gi.repository import Gtk, Adw
from gradia.graphics.gradient import GradientSelector, GradientBackground
from gradia.graphics.solid import SolidSelector, SolidBackground
from gradia.graphics.image import ImageSelector, ImageBackground
from gradia.graphics.background import Background

MODES = ["solid", "gradient", "image"]

class BackgroundSelector:

    def __init__(
        self,
        gradient: GradientBackground,
        solid: SolidBackground,
        image: ImageBackground,
        callback: Optional[Callable[[Background], None]] = None,
        initial_mode: str = "gradient",
        window: Optional[Gtk.Window] = None
    ) -> None:
        self.gradient = gradient
        self.solid = solid
        self.image = image
        self.callback = callback
        self.current_mode = initial_mode if initial_mode in MODES else "gradient"
        self.initial_mode = self.current_mode

        self.gradient_selector = GradientSelector(gradient, self._on_gradient_changed)
        self.solid_selector = SolidSelector(solid, self._on_solid_changed)
        self.image_selector = ImageSelector(image, self._on_image_changed, window)

        self.widget = self._build()

    def _build(self) -> Gtk.Box:
        main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)

        self.toggle_group = Adw.ToggleGroup()
        self.toggle_group.add_css_class("round")
        self.toggle_group.set_homogeneous(True)

        self.toggle_buttons = {}

        for mode in MODES:
            toggle = Adw.Toggle(name=mode)
            label = mode.capitalize()
            toggle.set_child(Gtk.Label(label=_(label)))
            self.toggle_group.add(toggle)
            self.toggle_buttons[mode] = toggle

        self.toggle_group.set_active_name(self.current_mode)
        self.toggle_group.connect("notify::active-name", self._on_group_changed)
        main_box.append(self.toggle_group)

        self.stack = Gtk.Stack()
        self.stack.set_transition_type(Gtk.StackTransitionType.CROSSFADE)
        self.stack.set_transition_duration(250)
        self.stack.set_hexpand(True)
        self.stack.set_valign(Gtk.Align.START)

        self.stack.add_named(self.solid_selector.widget, "solid")
        self.stack.add_named(self.gradient_selector.widget, "gradient")
        self.stack.add_named(self.image_selector.widget, "image")
        self.stack.set_visible_child_name(self.current_mode)

        main_box.append(self.stack)

        return main_box

    def _on_group_changed(self, group: Adw.ToggleGroup, _param) -> None:
        active_name = group.get_active_name()
        if active_name in MODES and active_name != self.current_mode:
            self.current_mode = active_name
            self.stack.set_visible_child_name(active_name)
            self._notify_current()

    def _on_gradient_changed(self, gradient: GradientBackground) -> None:
        if self.current_mode == "gradient":
            self._notify_current()

    def _on_solid_changed(self, solid: SolidBackground) -> None:
        if self.current_mode == "solid":
            self._notify_current()

    def _on_image_changed(self, image: ImageBackground) -> None:
        if self.current_mode == "image":
            self._notify_current()

    def _notify_current(self) -> None:
        if self.callback:
            current_background = {
                "gradient": self.gradient,
                "solid": self.solid,
                "image": self.image
            }.get(self.current_mode)
            self.callback(current_background)

    def get_current_background(self) -> Background:
        return {
            "gradient": self.gradient,
            "solid": self.solid,
            "image": self.image
        }.get(self.current_mode)

