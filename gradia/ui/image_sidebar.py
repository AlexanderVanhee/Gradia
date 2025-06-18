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
from gi.repository import Gtk, Adw
from gradia.ui.drawing_tools_group import DrawingToolsGroup
from gradia.ui.background_selector import BackgroundSelector
from gradia.constants import rootdir  # pyright: ignore
from gradia.backend.settings import Settings

@Gtk.Template(resource_path=f"{rootdir}/ui/image_sidebar.ui")
class ImageSidebar(Adw.Bin):
    __gtype_name__ = "GradiaImageSidebar"

    annotation_tools_group: DrawingToolsGroup = Gtk.Template.Child()
    background_selector_group: Adw.PreferencesGroup = Gtk.Template.Child()
    image_options_group = Gtk.Template.Child()
    disable_button: Gtk.Switch = Gtk.Template.Child()
    padding_row: Adw.SpinRow = Gtk.Template.Child()
    padding_adjustment: Gtk.Adjustment = Gtk.Template.Child()
    corner_radius_row: Adw.SpinRow = Gtk.Template.Child()
    corner_radius_adjustment: Gtk.Adjustment = Gtk.Template.Child()
    aspect_ratio_entry: Gtk.Entry = Gtk.Template.Child()
    shadow_strength_scale: Gtk.Scale = Gtk.Template.Child()
    auto_balance_row: Adw.ComboRow = Gtk.Template.Child()
    auto_balance_toggle: Gtk.Switch = Gtk.Template.Child()
    filename_row: Adw.ActionRow = Gtk.Template.Child()
    location_row: Adw.ActionRow = Gtk.Template.Child()
    processed_size_row: Adw.ActionRow = Gtk.Template.Child()

    def __init__(
        self,
        background_selector_widget: BackgroundSelector,
        on_padding_changed: Callable[[int], None],
        on_corner_radius_changed: Callable[[int], None],
        on_aspect_ratio_changed: Callable[[str], None],
        on_shadow_strength_changed: Callable[[int], None],
        on_auto_balance_changed: Callable[[bool], None],
        **kwargs
    ) -> None:
        super().__init__(**kwargs)

        self._callbacks = {
            'padding': on_padding_changed,
            'corner_radius': on_corner_radius_changed,
            'aspect_ratio': on_aspect_ratio_changed,
            'shadow_strength': on_shadow_strength_changed,
            'auto_balance': on_auto_balance_changed
        }

        self._saved_values = {
            'padding': 5,
            'corner_radius': 2,
            'aspect_ratio': "",
            'shadow_strength': 5,
            'auto_balance': False
        }

        self.image_options_group_content = self.image_options_group.get_first_child().get_first_child().get_next_sibling()

        self.background_selector_group.add(background_selector_widget)
        self._setup_widgets()
        self._connect_signals()

    def _setup_widgets(self) -> None:
        self.padding_adjustment.set_value(self._saved_values['padding'])
        self.corner_radius_adjustment.set_value(self._saved_values['corner_radius'])
        self.shadow_strength_scale.set_value(self._saved_values['shadow_strength'])

    def _connect_signals(self) -> None:
        self.padding_row.connect("output", lambda w: self._handle_change('padding', int(w.get_value())))
        self.corner_radius_row.connect("output", lambda w: self._handle_change('corner_radius', int(w.get_value())))
        self.aspect_ratio_entry.connect("changed", lambda w: self._handle_change('aspect_ratio', w.get_text()))
        self.shadow_strength_scale.connect("value-changed", lambda w: self._handle_change('shadow_strength', int(w.get_value())))
        self.auto_balance_toggle.connect("notify::active", lambda w, _: self._handle_change('auto_balance', w.get_active()))

        self.disable_button.connect("toggled", self._on_disable_toggled)
        Settings().bind_switch(self.disable_button, "image-options-lock")
        self._on_disable_toggled(self.disable_button)  # Initialize state

    def _handle_change(self, setting: str, value) -> None:
        if self.disable_button.get_active():
            defaults = {'padding': 0, 'corner_radius': 0, 'aspect_ratio': "", 'shadow_strength': 0, 'auto_balance': False}
            self._callbacks[setting](defaults[setting])
        else:
            self._saved_values[setting] = value
            self._callbacks[setting](value)

    def _on_disable_toggled(self, switch: Gtk.Switch) -> None:
        is_disabled = switch.get_active()
        self.image_options_group_content.set_sensitive(not is_disabled)

        if is_disabled:
            self._callbacks['padding'](0)
            self._callbacks['corner_radius'](0)
            self._callbacks['aspect_ratio']("")
            self._callbacks['shadow_strength'](0)
            self._callbacks['auto_balance'](False)
        else:
            self._callbacks['padding'](self._saved_values['padding'])
            self._callbacks['corner_radius'](self._saved_values['corner_radius'])
            self._callbacks['aspect_ratio'](self._saved_values['aspect_ratio'])
            self._callbacks['shadow_strength'](self._saved_values['shadow_strength'])
            self._callbacks['auto_balance'](self._saved_values['auto_balance'])
