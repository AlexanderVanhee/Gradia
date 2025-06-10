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

from collections.abc import Callable
from typing import Optional

from gi.repository import GObject, Gtk, Adw

from gradia.graphics.gradient import GradientSelector, GradientBackground
from gradia.graphics.solid import SolidSelector, SolidBackground
from gradia.graphics.image import ImageSelector, ImageBackground
from gradia.graphics.background import Background


MODES = ["solid", "gradient", "image"]

@Gtk.Template(resource_path="/be/alexandervanhee/gradia/ui/background_selector.ui")
class BackgroundSelector(Adw.Bin):
    __gtype_name__ = "GradiaBackgroundSelector"

    toggle_group: Adw.ToggleGroup = Gtk.Template.Child()
    stack: Gtk.Stack = Gtk.Template.Child()

    def __init__(
        self,
        gradient: GradientBackground,
        solid: SolidBackground,
        image: ImageBackground,
        callback: Optional[Callable[[Background], None]] = None,
        initial_mode: str = "gradient",
        window: Optional[Gtk.Window] = None,
        **kwargs
    ) -> None:
        super().__init__(**kwargs)

        self.gradient = gradient
        self.solid = solid
        self.image = image
        self.callback = callback
        self.current_mode = initial_mode if initial_mode in MODES else "gradient"
        self.initial_mode = self.current_mode

        self.gradient_selector = GradientSelector(gradient, self._on_gradient_changed)
        self.solid_selector = SolidSelector(solid, self._on_solid_changed)
        self.image_selector = ImageSelector(image, self._on_image_changed, window)

        self._setup()

    """
    Setup Methods
    """

    def _setup(self) -> None:
        # Set initial active name for toggle group
        self.toggle_group.set_active_name(self.current_mode)

        self.stack.add_named(self.solid_selector, "solid")
        self.stack.add_named(self.gradient_selector, "gradient")
        self.stack.add_named(self.image_selector, "image")
        self.stack.set_visible_child_name(self.current_mode)

    """
    Callbacks
    """

    @Gtk.Template.Callback()
    def _on_group_changed(self, group: Adw.ToggleGroup, _param: GObject.ParamSpec, *args) -> None:
        active_name = group.get_active_name()
        if active_name in MODES and active_name != self.current_mode:
            self.current_mode = active_name
            self.stack.set_visible_child_name(active_name)
            self._notify_current()

    def _on_gradient_changed(self, _gradient: GradientBackground) -> None:
        if self.current_mode == "gradient":
            self._notify_current()

    def _on_solid_changed(self, _solid: SolidBackground) -> None:
        if self.current_mode == "solid":
            self._notify_current()

    def _on_image_changed(self, _image: ImageBackground) -> None:
        if self.current_mode == "image":
            self._notify_current()

    """
    Internal Methods
    """

    # TODO: Fix callback type error
    def _notify_current(self) -> None:
        if self.callback:
            current_background = self.get_current_background()
            self.callback(current_background)

    def get_current_background(self) -> GradientBackground | SolidBackground | ImageBackground | None:
        backgrounds: dict[str, GradientBackground | SolidBackground | ImageBackground] = {
            "gradient": self.gradient,
            "solid": self.solid,
            "image": self.image
        }

        return backgrounds.get(self.current_mode)
