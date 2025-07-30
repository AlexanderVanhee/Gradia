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
from gradia.ui.widget.gradient_preset_button import GradientPresetButton
from gradia.ui.widget.angle_selector import AngleSelector
from gradia.ui.widget.gradient_editor import GradientEditor
from gradia.constants import rootdir
from gradia.graphics.gradient import GradientBackground,Gradient
from typing import Optional, Callable, List, Tuple

@Gtk.Template(resource_path=f"{rootdir}/ui/selectors/gradient_selector.ui")
class GradientSelector(Adw.PreferencesGroup):
    __gtype_name__ = "GradiaGradientSelector"
    gradient_editor = Gtk.Template.Child()
    step_label = Gtk.Template.Child()
    button_revealer = Gtk.Template.Child()
    remove_button_revealer = Gtk.Template.Child()
    remove_button = Gtk.Template.Child()
    angle_entry = Gtk.Template.Child()
    angle_selector = Gtk.Template.Child()
    gradient_editor =  Gtk.Template.Child()
    type_group =  Gtk.Template.Child()
    preset_button = Gtk.Template.Child()

    def __init__(
        self,
        gradient_background: GradientBackground,
        callback: Optional[Callable[[GradientBackground], None]] = None,
        **kwargs
    ) -> None:
        super().__init__(**kwargs)
        self.gradient_background: GradientBackground = gradient_background
        self.callback: Optional[Callable[[GradientBackground], None]] = callback
        self.gradient_editor.selector = self
        self.remove_button.connect("clicked", self._on_remove_button_clicked)

        self.angle_entry.connect("activate", self._on_angle_entry_activate)
        self.gradient_editor.set_on_gradient_changed(self.on_gradient_colors_changed)

        self._updating_entry = False
        self._set_widget_properties_from_gradient(self.gradient_background.gradient)
        self.preset_button.callback = self.on_preset_selected

    def _on_remove_button_clicked(self, button):
        self.gradient_editor.remove_selected_button()

    def on_preset_selected(self, gradient: Gradient):
        self._set_widget_properties_from_gradient(gradient)
        self._notify()

    def _notify(self):
        angle = self.angle_selector.angle
        steps = self.gradient_editor.get_gradient_data()
        gradient_type = self.type_group.get_active_name()

        gradient = Gradient(
            steps=steps,
            mode=gradient_type,
            angle=angle,
        )

        self.gradient_background.gradient = gradient

        if self.callback:
            self.callback(self.gradient_background)

    def _set_widget_properties_from_gradient(self, gradient: Gradient):
        self.angle_selector.angle = gradient.angle
        self.update_angle_entry(gradient.angle)
        self.type_group.set_active_name(gradient.mode)
        self.gradient_editor.set_gradient_data(gradient.steps)


    def _validate_and_set_angle(self, angle_text: str) -> bool:
        try:
            angle_text = angle_text.replace('°', '').strip()
            angle = float(angle_text)

            angle = max(0, min(360, angle))

            self.angle_selector.angle = angle

            if angle != float(angle_text):
                self._updating_entry = True
                self.angle_entry.set_text(f"{angle:.0f}°")
                self._updating_entry = False

            return True

        except ValueError:
            self._updating_entry = True
            current_angle = getattr(self.gradient_background, 'angle', 0)
            self.angle_entry.set_text(f"{current_angle:.0f}°")
            self._updating_entry = False
            return False

    def _on_angle_entry_activate(self, entry):
        if self._updating_entry:
            return

        angle_text = entry.get_text()
        if self._validate_and_set_angle(angle_text):
            self._notify()


    @Gtk.Template.Callback()
    def on_angle_set(self, angle_selector, angle_value=None):
        if angle_value is not None:
            self.gradient_background.angle = angle_value
        self._notify()

    @Gtk.Template.Callback()
    def on_angle_changed(self, angle_selector, param_spec):
        angle_value = angle_selector.get_property("angle")
        self.update_angle_entry(angle_value)


    def update_angle_entry(self, angle_value):
        if not self._updating_entry:
            self._updating_entry = True
            self.angle_entry.set_text(f"{angle_value:.0f}°")
            self._updating_entry = False

    @Gtk.Template.Callback()
    def on_toggle_changed(self, toggle_group, param_spec):
        isradial = toggle_group.get_active_name() == "radial"
        self.angle_selector.set_sensitive(not isradial)
        self.angle_entry.set_sensitive(not isradial)
        self.angle_selector.set_opacity(0.30 if isradial else 1)
        self._notify()

    def on_gradient_colors_changed(self, gradient_data: List[Tuple[float, str]]):
        self._notify()
