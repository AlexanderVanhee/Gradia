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

PRESET_RATIOS = [
    ("Auto", ""),
    ("16:9", "16:9"),
    ("4:3", "4:3"),
    ("3:2", "3:2"),
    ("1:1", "1:1"),
    ("2:3", "2:3"),
    ("3:4", "3:4"),
    ("9:16", "9:16"),
    ("1.618:1", "1.618:1"),
]
PRESET_RATIOS_DICT = dict((v, l) for l, v in PRESET_RATIOS)


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
    aspect_ratio_button: Gtk.Button = Gtk.Template.Child()
    shadow_strength_scale: Gtk.Scale = Gtk.Template.Child()
    auto_balance_row: Adw.ComboRow = Gtk.Template.Child()
    auto_balance_toggle: Gtk.Switch = Gtk.Template.Child()
    filename_row: Adw.ActionRow = Gtk.Template.Child()
    location_row: Adw.ActionRow = Gtk.Template.Child()
    processed_size_row: Adw.ActionRow = Gtk.Template.Child()
    command_button: Gtk.Button = Gtk.Template.Child()

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

        self.settings = Settings()

        self.image_options_group_content = self.image_options_group.get_first_child().get_first_child().get_next_sibling()

        self.background_selector_group.add(background_selector_widget)
        self._setup_widgets()
        self._setup_aspect_ratio_popover()
        self._bind_settings()
        self._connect_signals()

    def _setup_widgets(self) -> None:
        self.padding_adjustment.set_value(self.settings.image_padding)
        self.corner_radius_adjustment.set_value(self.settings.image_corner_radius)
        self.shadow_strength_scale.set_value(self.settings.image_shadow_strength)
        self.auto_balance_toggle.set_active(self.settings.image_auto_balance)
        self.aspect_ratio_button.set_label(self._label_for_ratio_value(self.settings.image_aspect_ratio))

    def _bind_settings(self) -> None:
        self.settings.bind_switch(self.disable_button, "image-options-lock")
        self.settings.bind_switch(self.auto_balance_toggle, "image-auto-balance")

        self.settings.bind_spin_row(self.padding_row, "image-padding")
        self.settings.bind_spin_row(self.corner_radius_row, "image-corner-radius")

        self.settings.bind_scale(self.shadow_strength_scale, "image-shadow-strength")

    def _setup_aspect_ratio_popover(self) -> None:
        self.aspect_ratio_popover = Gtk.Popover()
        self.aspect_ratio_popover.set_autohide(True)
        self.aspect_ratio_popover.set_margin_top(5)

        main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)

        scrolled_window = Gtk.ScrolledWindow()
        scrolled_window.set_vexpand(True)
        scrolled_window.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scrolled_window.set_min_content_height(110)
        scrolled_window.set_margin_top(10)

        self.aspect_ratio_flowbox = Gtk.FlowBox(
            homogeneous=True,
            margin_start=5, margin_end=5,
            valign=Gtk.Align.START,
            column_spacing=10, row_spacing=10,
            max_children_per_line=3
        )
        self.aspect_ratio_flowbox.set_selection_mode(Gtk.SelectionMode.NONE)

        for label, value in PRESET_RATIOS:
            button = Gtk.Button(label=label)
            button.set_size_request(80, 40)
            button.connect("clicked", lambda b, v=value: self._on_preset_ratio_selected(v))
            self.aspect_ratio_flowbox.append(button)

        scrolled_window.set_child(self.aspect_ratio_flowbox)
        main_box.append(scrolled_window)

        bottom_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8, margin_start=8, margin_end=10, margin_bottom=10)
        bottom_box.append(Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL))

        inputs_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10, homogeneous=True)

        width_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        width_label = Gtk.Label(label="Width", halign=Gtk.Align.START)
        self.width_input = Gtk.Entry(input_purpose=Gtk.InputPurpose.NUMBER)
        self.width_input.set_max_length(4)
        width_box.append(width_label)
        width_box.append(self.width_input)

        height_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        height_label = Gtk.Label(label="Height", halign=Gtk.Align.START)
        self.height_input = Gtk.Entry(input_purpose=Gtk.InputPurpose.NUMBER)
        self.height_input.set_max_length(4)
        height_box.append(height_label)
        height_box.append(self.height_input)

        inputs_box.append(width_box)
        inputs_box.append(height_box)
        bottom_box.append(inputs_box)

        self.set_button = Gtk.Button(label="Set")
        self.set_button.add_css_class("suggested-action")
        self.set_button.connect("clicked", self._on_custom_ratio_set)
        bottom_box.append(self.set_button)

        main_box.append(bottom_box)
        self.aspect_ratio_popover.set_child(main_box)
        self.aspect_ratio_button.set_popover(self.aspect_ratio_popover)

    def _on_preset_ratio_selected(self, ratio: str) -> None:
        self.aspect_ratio_button.set_label(self._label_for_ratio_value(ratio))
        self.settings.image_aspect_ratio = ratio
        self._handle_change('aspect_ratio', ratio)
        self.aspect_ratio_popover.popdown()

    def _on_custom_ratio_set(self, button: Gtk.Button) -> None:
        width_text = self.width_input.get_text().strip()
        height_text = self.height_input.get_text().strip()

        if not width_text.isdigit() or not height_text.isdigit():
            return

        width = int(width_text)
        height = int(height_text)

        if width <= 0 or height <= 0:
            return

        custom_ratio = f"{width}:{height}"
        self.aspect_ratio_button.set_label(custom_ratio)
        self.settings.image_aspect_ratio = custom_ratio
        self._handle_change('aspect_ratio', custom_ratio)
        self.aspect_ratio_popover.popdown()

    def _connect_signals(self) -> None:
        self.padding_row.connect("output", lambda w: self._handle_change('padding', int(w.get_value())))
        self.corner_radius_row.connect("output", lambda w: self._handle_change('corner_radius', int(w.get_value())))
        self.shadow_strength_scale.connect("value-changed", lambda w: self._handle_change('shadow_strength', int(w.get_value())))
        self.auto_balance_toggle.connect("notify::active", lambda w, _: self._handle_change('auto_balance', w.get_active()))

        self.disable_button.connect("toggled", self._on_disable_toggled)
        self._on_disable_toggled(self.disable_button)

    def _handle_change(self, setting: str, value) -> None:
        if self.disable_button.get_active():
            defaults = {'padding': 0, 'corner_radius': 0, 'aspect_ratio': "", 'shadow_strength': 0, 'auto_balance': False}
            self._callbacks[setting](defaults[setting])
        else:
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
            self._callbacks['padding'](self.settings.image_padding)
            self._callbacks['corner_radius'](self.settings.image_corner_radius)
            self._callbacks['aspect_ratio'](self.settings.image_aspect_ratio)
            self._callbacks['shadow_strength'](self.settings.image_shadow_strength)
            self._callbacks['auto_balance'](self.settings.image_auto_balance)

    def _label_for_ratio_value(self, value: str) -> str:
        return PRESET_RATIOS_DICT.get(value, value if value else "Auto")
