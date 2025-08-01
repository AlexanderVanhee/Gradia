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

from gradia.graphics.gradient import GradientBackground
from gradia.graphics.gradient_selector import GradientSelector
from gradia.graphics.solid import SolidSelector, SolidBackground
from gradia.graphics.image import ImageSelector, ImageBackground
from gradia.graphics.background import Background
from gradia.constants import rootdir  # pyright: ignore
from gradia.backend.settings import Settings


MODES = ["solid", "gradient", "image"]

@Gtk.Template(resource_path=f"{rootdir}/ui/background_selector.ui")
class BackgroundSelector(Adw.Bin):
    __gtype_name__ = "GradiaBackgroundSelector"

    toggle_group: Adw.ToggleGroup = Gtk.Template.Child()
    stack: Gtk.Stack = Gtk.Template.Child()

    def __init__(
        self,
        callback: Optional[Callable[[Background], None]] = None,
        window: Optional[Gtk.Window] = None,
        **kwargs
    ) -> None:
        super().__init__(**kwargs)

        self.settings = Settings()
        self.solid = SolidBackground.from_json(self.settings.solid_state or '{}')
        self.gradient = GradientBackground.from_json(self.settings.gradient_state or '{}')
        self.image = ImageBackground()
        self.callback = callback
        self.current_mode = self.settings.background_mode if self.settings.background_mode in MODES else "gradient"
        self.initial_mode = self.current_mode

        self.gradient_selector = GradientSelector(self.gradient, self._on_gradient_changed)
        self.solid_selector = SolidSelector(self.solid, self._on_solid_changed)
        self.image_selector = ImageSelector(self.image, self._on_image_changed, window)

        self._setup()

    """
    Setup Methods
    """

    def _setup(self) -> None:
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
            self.settings.background_mode = active_name
            self.stack.set_visible_child_name(active_name)
            self._notify_current()

    def _on_gradient_changed(self, gradient: GradientBackground) -> None:
        self.settings.gradient_state = gradient.to_json()
        if self.current_mode == "gradient":
            self._notify_current()

    def _on_solid_changed(self, solid: SolidBackground) -> None:
        self.settings.solid_state = solid.to_json()
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
