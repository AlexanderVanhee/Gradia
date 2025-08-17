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
from gradia.graphics.background import Background
from gradia.constants import rootdir  # pyright: ignore
from gradia.backend.settings import Settings

PRESET_RATIOS = [
    ("Auto", ""),
    ("1:1", "1:1"),
    ("16:9", "16:9"),
    ("4:3", "4:3"),
    ("3:2", "3:2"),
    ("2:3", "2:3"),
    ("3:4", "3:4"),
    ("9:16", "9:16"),
    ("1.618:1", "1.618:1"),
]
PRESET_RATIOS_DICT = dict((v, l) for l, v in PRESET_RATIOS)


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
    aspect_ratio_row: Adw.ActionRow = Gtk.Template.Child()
    aspect_ratio_button: Gtk.Button = Gtk.Template.Child()
    shadow_strength_scale: Gtk.Scale = Gtk.Template.Child()
    auto_balance_toggle: Gtk.Switch = Gtk.Template.Child()
    filename_row: Adw.ActionRow = Gtk.Template.Child()
    location_row: Adw.ActionRow = Gtk.Template.Child()
    processed_size_row: Adw.ActionRow = Gtk.Template.Child()
    share_button: Gtk.Button = Gtk.Template.Child()
    rotate_left_button: Gtk.Button = Gtk.Template.Child()
    rotate_right_button: Gtk.Button = Gtk.Template.Child()

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
        self._setup_aspect_ratio_popover()
        self._connect_signals()



    def _setup_widgets(self) -> None:
        self.padding_adjustment.set_value(self.settings.image_padding)
        self.corner_radius_adjustment.set_value(self.settings.image_corner_radius)
        self.shadow_strength_scale.set_value(self.settings.image_shadow_strength)
        self.auto_balance_toggle.set_active(self.settings.image_auto_balance)
        self.aspect_ratio_button.set_label(self._label_for_ratio_value(self.settings.image_aspect_ratio))
        self._current_rotation = self.settings.image_rotation

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
        width_label = Gtk.Label(label=_("Width"), halign=Gtk.Align.START)
        self.width_input = Gtk.Entry(input_purpose=Gtk.InputPurpose.NUMBER)
        self.width_input.set_max_length(4)
        width_box.append(width_label)
        width_box.append(self.width_input)

        height_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        height_label = Gtk.Label(label=_("Height"), halign=Gtk.Align.START)
        self.height_input = Gtk.Entry(input_purpose=Gtk.InputPurpose.NUMBER)
        self.height_input.set_max_length(4)
        height_box.append(height_label)
        height_box.append(self.height_input)

        inputs_box.append(width_box)
        inputs_box.append(height_box)
        bottom_box.append(inputs_box)

        self.set_button = Gtk.Button(label=_("Set"))
        self.set_button.add_css_class("suggested-action")
        self.set_button.connect("clicked", self._on_custom_ratio_set)
        bottom_box.append(self.set_button)

        main_box.append(bottom_box)
        self.aspect_ratio_popover.set_child(main_box)
        self.aspect_ratio_button.set_popover(self.aspect_ratio_popover)

    def _on_background_changed(self, updated_background: Background) -> None:
        self._current_background = updated_background
        if updated_background != None:
            self._notify_image_options_changed()

    def _on_preset_ratio_selected(self, ratio: str) -> None:
        self.aspect_ratio_button.set_label(self._label_for_ratio_value(ratio))
        self.settings.image_aspect_ratio = ratio
        self._notify_image_options_changed()
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
        self.settings.image_aspect_ratio = custom_ratio
        self.aspect_ratio_button.set_label(custom_ratio)
        self._notify_image_options_changed()
        self.aspect_ratio_popover.popdown()

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
            aspect_ratio=self._ratio_value_from_label(self.aspect_ratio_button.get_label()),
            shadow_strength=int(self.shadow_strength_scale.get_value()),
            auto_balance=self.auto_balance_toggle.get_active(),
            rotation=self._current_rotation,
            background=self._current_background
        )

    def _get_default_options(self) -> ImageOptions:
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
            rotation=self.settings.image_rotation
        )

    def _notify_image_options_changed(self) -> None:
        if self._background_mode == "none":
            options = self._get_default_options()
        else:
            options = self._get_current_options()

        self.on_image_options_changed(options)

    def _set_selective_sensitivity(self, is_disabled: bool) -> None:
        self.padding_row.set_sensitive(not is_disabled)
        self.corner_radius_row.set_sensitive(not is_disabled)
        self.aspect_ratio_row.set_sensitive(not is_disabled)
        self.shadow_strength_row.set_sensitive(not is_disabled)

    def _on_background_mode_changed(self, mode: str) -> None:
        self._background_mode = mode
        is_disabled = mode == "none"
        self._updating_widgets = True

        self._set_selective_sensitivity(is_disabled)

        if is_disabled:
            options = self._get_default_options()
        else:
            options = self._get_current_options()

        self.on_image_options_changed(options)
        self._updating_widgets = False

    def _label_for_ratio_value(self, value: str) -> str:
        return PRESET_RATIOS_DICT.get(value, value if value else "Auto")

    def _ratio_value_from_label(self, label: str) -> str:
        for value, display_label in PRESET_RATIOS_DICT.items():
            if display_label == label:
                return value
        return label if label != "Auto" else ""

    def set_drawing_mode(self, mode):
        self.drawing_tools_group.set_current_tool(mode)
