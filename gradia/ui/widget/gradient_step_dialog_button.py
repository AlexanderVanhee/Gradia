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

from gi.repository import Adw, Gtk, GLib, Gdk
from typing import Callable, Optional
from gradia.graphics.gradient import Gradient
from gradia.constants import rootdir
from gradia.utils.colors import parse_rgb_string


class GradientStepDialogButton(Gtk.Button):
    __gtype_name__ = "GradiaGradientStepDialogButton"

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)

        self._gradient = None
        self._callback = None
        self._dialog = None

        self.set_icon_name("edit-symbolic")
        self.set_valign(Gtk.Align.CENTER)
        self.add_css_class("flat")
        self.connect("clicked", self._on_button_clicked)

    def _on_button_clicked(self, button: Gtk.Button) -> None:
        if self._gradient is None:
            raise ValueError("No gradient set. Use set_gradient() before showing the dialog.")

        if self._dialog is None:
            self._dialog = CssGradientDialog()
            self._dialog.set_callback(self._on_dialog_apply)

        self._dialog.set_gradient(self._gradient)
        self._dialog.present(self.get_root())

    def _on_dialog_apply(self, gradient: Gradient) -> None:
        self._gradient = gradient
        if self._callback:
            self._callback(gradient)

    def set_gradient(self, gradient: Gradient) -> None:
        self._gradient = gradient

    def get_gradient(self) -> Gradient:
        return self._gradient

    def set_callback(self, callback: Callable[[Gradient], None]) -> None:
        self._callback = callback


class GradientStepRow(Adw.ActionRow):
    def __init__(self, step_index: int, position: float, color: str, on_changed_callback: Callable):
        super().__init__()

        self.step_index = step_index
        self.on_changed_callback = on_changed_callback

        self.color_button = Gtk.ColorButton()
        self.color_button.set_valign(Gtk.Align.CENTER)
        self._set_color_from_string(color)
        self.color_button.connect("color-set", self._on_color_changed)
        self.add_prefix(self.color_button)

        position_adjustment = Gtk.Adjustment(value=position * 100, lower=0, upper=100, step_increment=1, page_increment=10)
        self.position_spinbutton = Gtk.SpinButton(adjustment=position_adjustment, digits=1)
        self.position_spinbutton.set_value(position * 100)
        self.position_spinbutton.connect("value-changed", self._on_position_changed)


        position_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=0)
        position_box.append(self.position_spinbutton)

        self.remove_button = Gtk.Button(icon_name="user-trash-symbolic")
        self.remove_button.add_css_class("destructive-action")
        self.remove_button.connect("clicked", self._on_remove_clicked)

        controls_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6 , valign=Gtk.Align.CENTER)
        controls_box.append(position_box)

        controls_box.append(self.remove_button)

        self.add_suffix(controls_box)

    def _set_color_from_string(self, color_str: str):
        rgb = parse_rgb_string(color_str)
        if rgb:
            r, g, b = rgb
            rgba = Gdk.RGBA()
            rgba.red = r / 255.0
            rgba.green = g / 255.0
            rgba.blue = b / 255.0
            rgba.alpha = 1.0
            self.color_button.set_rgba(rgba)

    def _on_position_changed(self, spinbutton):
        self.on_changed_callback()

    def _on_color_changed(self, color_button):
        self.on_changed_callback()

    def _on_remove_clicked(self, button):
        self.on_changed_callback(remove_index=self.step_index)

    def get_position(self) -> float:
        return self.position_spinbutton.get_value() / 100.0

    def get_color(self) -> str:
        rgba = self.color_button.get_rgba()
        r = int(rgba.red * 255)
        g = int(rgba.green * 255)
        b = int(rgba.blue * 255)
        return f"rgb({r},{g},{b})"

    def update_remove_button_sensitivity(self, can_remove: bool):
        self.remove_button.set_sensitive(can_remove)


@Gtk.Template(resource_path=f"{rootdir}/ui/gradient_step_dialog.ui")
class CssGradientDialog(Adw.Dialog):
    __gtype_name__ = "GradiaGradientStepDialog"

    preview_box = Gtk.Template.Child()
    steps_group = Gtk.Template.Child()
    add_step_button = Gtk.Template.Child()

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)

        self._gradient = None
        self._callback = None
        self._initial_gradient = None
        self._step_rows = []

        self.add_step_button.connect("clicked", self._on_add_step_clicked)
        self.connect("closed", self._on_dialog_closed)

    def set_gradient(self, gradient: Gradient) -> None:
        self._gradient = gradient
        self._initial_gradient = gradient
        self._populate_steps()
        self._update_preview()

    def set_callback(self, callback: Callable[[Gradient], None]) -> None:
        self._callback = callback

    def _populate_steps(self):
        for row in self._step_rows:
            self.steps_group.remove(row)
        self._step_rows.clear()

        for i, (position, color) in enumerate(self._gradient.steps):
            row = GradientStepRow(i, position, color, self._on_step_changed)
            self._step_rows.append(row)
            self.steps_group.add(row)

        self._update_remove_button_sensitivity()
        self._update_add_button_visibility()

    def _update_remove_button_sensitivity(self):
        can_remove = len(self._step_rows) > 2
        for row in self._step_rows:
            row.update_remove_button_sensitivity(can_remove)

    def _on_step_changed(self, remove_index=None):
        if remove_index is not None:
            if len(self._step_rows) > 2:
                row_to_remove = self._step_rows[remove_index]
                self.steps_group.remove(row_to_remove)
                self._step_rows.remove(row_to_remove)

        steps = []
        for row in self._step_rows:
            position = row.get_position()
            color = row.get_color()
            steps.append((position, color))

        steps.sort(key=lambda x: x[0])

        self._gradient = Gradient(
            mode=self._gradient.mode,
            steps=steps,
            angle=self._gradient.angle
        )

        self._update_preview()
        self._update_remove_button_sensitivity()
        self._update_add_button_visibility()

    def _on_add_step_clicked(self, button):
        if len(self._step_rows) < 5:
            new_position = 0.5
            new_color = "rgb(128,128,128)"

            if len(self._step_rows) >= 2:
                positions = [row.get_position() for row in self._step_rows]
                positions.sort()
                for i in range(len(positions) - 1):
                    gap = positions[i + 1] - positions[i]
                    if gap > 0.1:
                        new_position = positions[i] + gap / 2
                        break

            row = GradientStepRow(len(self._step_rows), new_position, new_color, self._on_step_changed)
            self._step_rows.append(row)
            self.steps_group.add(row)

            self._on_step_changed()

    def _update_add_button_visibility(self):
        self.add_step_button.set_sensitive(len(self._step_rows) < 5)

    def _update_preview(self) -> None:
        if self._gradient is not None:
            self._apply_preview_gradient(self._gradient)

    def _apply_preview_gradient(self, gradient: Gradient) -> None:
        css = f"""
            .gradient-preview {{
                background-image: {gradient.to_css()};
            }}
        """

        css_provider = Gtk.CssProvider()
        css_provider.load_from_string(css)

        style_context = self.preview_box.get_style_context()

        style_context.add_provider(
            css_provider,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION + 5
        )

    def _on_dialog_closed(self, dialog: Adw.Dialog) -> None:
        if self._gradient and self._callback:
            if not self._initial_gradient or self._gradient.to_css() != self._initial_gradient.to_css():
                self._ensure_minimum_spacing()
                self._callback(self._gradient)

    def _ensure_minimum_spacing(self, min_gap: float = 0.18):
        steps = sorted(self._gradient.steps, key=lambda x: x[0])

        if len(steps) < 2:
            return

        adjusted = [steps[0]]

        for i in range(1, len(steps)):
            pos, color = steps[i]
            prev_pos = adjusted[-1][0]

            if pos - prev_pos < min_gap:
                pos = prev_pos + min_gap

            if pos > 1.0:
                pos = 1.0

            adjusted.append((pos, color))

        for i in range(len(adjusted) - 2, -1, -1):
            pos, color = adjusted[i]
            next_pos = adjusted[i + 1][0]

            if next_pos - pos < min_gap:
                pos = max(0.0, next_pos - min_gap)
                adjusted[i] = (pos, color)

        self._gradient = Gradient(
            mode=self._gradient.mode,
            steps=adjusted,
            angle=self._gradient.angle
        )
