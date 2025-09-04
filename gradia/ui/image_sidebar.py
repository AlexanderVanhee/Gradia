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

from typing import Callable
from dataclasses import dataclass
from gi.repository import Gtk, Adw
from gradia.ui.drawing_tools_group import DrawingToolsGroup
from gradia.ui.background_selector import BackgroundSelector
from gradia.ui.widget.background_aspect_ratio_selector import AspectRatioSelector
from gradia.graphics.background import Background
from gradia.constants import rootdir  # pyright: ignore
from gradia.backend.settings import Settings


@dataclass
class ImageOptions:
    background: Background
    padding: int
    corner_radius: int
    aspect_ratio: str
    shadow_strength: int
    auto_balance: bool
    rotation: int


@Gtk.Template(resource_path=f"{rootdir}/ui/image_sidebar.ui")
class ImageSidebar(Adw.Bin):
    __gtype_name__ = "GradiaImageSidebar"

    drawing_tools_group: DrawingToolsGroup = Gtk.Template.Child()
    background_selector_group: Adw.PreferencesGroup = Gtk.Template.Child()
    image_options_group = Gtk.Template.Child()
    padding_row: Adw.SpinRow = Gtk.Template.Child()
    padding_adjustment: Gtk.Adjustment = Gtk.Template.Child()
    corner_radius_row: Adw.SpinRow = Gtk.Template.Child()
    shadow_strength_row: Adw.ActionRow = Gtk.Template.Child()
    corner_radius_adjustment: Gtk.Adjustment = Gtk.Template.Child()
    shadow_strength_scale: Gtk.Scale = Gtk.Template.Child()
    auto_balance_toggle: Gtk.Switch = Gtk.Template.Child()
    filename_row: Adw.ActionRow = Gtk.Template.Child()
    location_row: Adw.ActionRow = Gtk.Template.Child()
    processed_size_row: Adw.ActionRow = Gtk.Template.Child()
    share_button: Gtk.Button = Gtk.Template.Child()
    rotate_left_button: Gtk.Button = Gtk.Template.Child()
    rotate_right_button: Gtk.Button = Gtk.Template.Child()
    aspect_ratio_selector: AspectRatioSelector = Gtk.Template.Child()

    def __init__(
        self,
        on_image_options_changed: Callable[[ImageOptions], None],
        **kwargs
    ) -> None:
        super().__init__(**kwargs)
        self._background_mode = "none"
        self.on_image_options_changed = on_image_options_changed
        self.settings = Settings()
        self._updating_widgets = False
        self._current_rotation = 0
        self._current_background = None

        self.image_options_group_content = self.image_options_group.get_first_child().get_first_child().get_next_sibling()
        self.background_selector: BackgroundSelector = BackgroundSelector(
            callback=self._on_background_changed
        )
        self.background_selector.set_current_mode_callback(self._on_background_mode_changed)

        self.background_selector_group.add(self.background_selector)

        self._setup_widgets()
        self._connect_signals()

    def _setup_widgets(self) -> None:
        self.padding_adjustment.set_value(self.settings.image_padding)
        self.corner_radius_adjustment.set_value(self.settings.image_corner_radius)
        self.shadow_strength_scale.set_value(self.settings.image_shadow_strength)
        self.auto_balance_toggle.set_active(self.settings.image_auto_balance)
        self.aspect_ratio_selector.set_ratio(self.settings.image_aspect_ratio)
        self._current_rotation = self.settings.image_rotation

    def _on_background_changed(self, updated_background: Background) -> None:
        self._current_background = updated_background
        if updated_background != None:
            self._notify_image_options_changed()

    @Gtk.Template.Callback()
    def _on_aspect_ratio_changed(self, widget, ratio) -> None:
        if not self._updating_widgets:
            self.settings.image_aspect_ratio = ratio
            self._notify_image_options_changed()

    def _connect_signals(self) -> None:
        self.padding_row.connect("output", self._on_padding_changed)
        self.corner_radius_row.connect("output", self._on_corner_radius_changed)
        self.shadow_strength_scale.connect("value-changed", self._on_shadow_strength_changed)
        self.auto_balance_toggle.connect("notify::active", self._on_auto_balance_changed)
        self.rotate_left_button.connect("clicked", self._on_rotate_left_clicked)
        self.rotate_right_button.connect("clicked", self._on_rotate_right_clicked)

    def _on_padding_changed(self, widget) -> None:
        if not self._updating_widgets:
            value = int(widget.get_value())
            self.settings.image_padding = value
            self._notify_image_options_changed()

    def _on_corner_radius_changed(self, widget) -> None:
        if not self._updating_widgets:
            value = int(widget.get_value())
            self.settings.image_corner_radius = value
            self._notify_image_options_changed()

    def _on_shadow_strength_changed(self, widget) -> None:
        if not self._updating_widgets:
            value = int(widget.get_value())
            self.settings.image_shadow_strength = value
            self._notify_image_options_changed()

    def _on_auto_balance_changed(self, widget, pspec) -> None:
        if not self._updating_widgets:
            value = widget.get_active()
            self.settings.image_auto_balance = value
            self._notify_image_options_changed()

    def _on_rotate_left_clicked(self, button: Gtk.Button) -> None:
        if not self._updating_widgets:
            self._current_rotation = (self._current_rotation - 90) % 360
            self._notify_image_options_changed()
            self.settings.image_rotation = self._current_rotation

    def _on_rotate_right_clicked(self, button: Gtk.Button) -> None:
        if not self._updating_widgets:
            self._current_rotation = (self._current_rotation + 90) % 360
            self._notify_image_options_changed()
            self.settings.image_rotation = self._current_rotation

    def _get_current_options(self) -> ImageOptions:
        return ImageOptions(
            padding=int(self.padding_adjustment.get_value()),
            corner_radius=int(self.corner_radius_adjustment.get_value()),
            aspect_ratio=self.aspect_ratio_selector.get_ratio(),
            shadow_strength=int(self.shadow_strength_scale.get_value()),
            auto_balance=self.auto_balance_toggle.get_active(),
            rotation=self._current_rotation,
            background=self._current_background
        )

    def _get_disabled_options(self) -> ImageOptions:
        return ImageOptions(
            padding=0,
            corner_radius=0,
            aspect_ratio="",
            shadow_strength=0,
            auto_balance=self.auto_balance_toggle.get_active(),
            rotation=self._current_rotation,
            background = None
        )

    def _get_settings_options(self) -> ImageOptions:
        return ImageOptions(
            padding=self.settings.image_padding,
            corner_radius=self.settings.image_corner_radius,
            aspect_ratio=self.settings.image_aspect_ratio,
            shadow_strength=self.settings.image_shadow_strength,
            auto_balance=self.settings.image_auto_balance,
            rotation=self.settings.image_rotation,
            background=None
        )

    def _notify_image_options_changed(self) -> None:
        if self._background_mode == "none":
            options = self._get_disabled_options()
        else:
            options = self._get_current_options()

        self.on_image_options_changed(options)

    def _set_selective_sensitivity(self, is_disabled: bool) -> None:
        self.padding_row.set_sensitive(not is_disabled)
        self.corner_radius_row.set_sensitive(not is_disabled)
        self.aspect_ratio_selector.set_sensitive(not is_disabled)
        self.shadow_strength_row.set_sensitive(not is_disabled)

    def _on_background_mode_changed(self, mode: str) -> None:
        self._background_mode = mode
        is_disabled = mode == "none"
        self._updating_widgets = True

        self._set_selective_sensitivity(is_disabled)

        if is_disabled:
            options = self._get_disabled_options()
        else:
            options = self._get_current_options()

        self.on_image_options_changed(options)
        self._updating_widgets = False

    def set_drawing_mode(self, mode):
        self.drawing_tools_group.set_current_tool(mode)
