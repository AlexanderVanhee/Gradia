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

from gi.repository import Adw, Gtk, GObject, Gdk, Gsk, Graphene, GLib
from gradia.ui.widget.angle_selector import AngleSelector
from gradia.constants import rootdir
from gradia.utils.colors import is_light_color_rgba
from typing import Optional, Callable, List, Tuple
import operator
import time
import math

class GradientColorButton(Gtk.Box):
    __gtype_name__ = "GradientColorButton"

    color = GObject.Property(
        type=Gdk.RGBA,
        default=Gdk.RGBA(),
        nick="Color",
    )

    step = GObject.Property(
        type=float,
        default=0.0,
        minimum=0.0,
        maximum=1.0,
        nick="Step",
    )

    selected = GObject.Property(
        type=bool,
        default=False,
        nick="Selected",
    )

    def __init__(self, tooltip_text: str = "", **kwargs):
        super().__init__(**kwargs)
        self.set_tooltip_text(tooltip_text)
        self.add_css_class("gradient-color-picker")

        self._css_provider = Gtk.CssProvider()
        self.get_style_context().add_provider(
            self._css_provider,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION + 2
        )

        box = Gtk.Box(halign=Gtk.Align.CENTER, valign=Gtk.Align.CENTER)
        self._icon = Gtk.Image.new_from_icon_name("edit-symbolic")
        self._icon.set_pixel_size(18)
        self._icon.set_size_request(30,-1)
        self._icon.get_style_context().add_class("gradient-color-button")
        box.append(self._icon)

        self.append(box)

        self._color_dialog: Optional[Gtk.ColorDialog] = None
        self.editor: Optional["GradientEditor"] = None
        self._has_moved = False

        self.connect("notify::color", self._on_color_changed)
        self.connect("notify::step", self._on_step_changed)
        self.connect("notify::selected", self._on_selected_changed)

        default_color = Gdk.RGBA()
        default_color.parse("#000000")
        self.set_property("color", default_color)

        self._update_color_css()

    def _on_color_changed(self, *_):
        self._update_color_css()

    def _on_step_changed(self, *_):
        self.set_tooltip_text(f"{scale_correction(self.step):.0%}")
        if self.editor:
            self.editor._update_ui_for_selected_button()

    def _on_selected_changed(self, *_):
        if self.selected:
            self.add_css_class("selected")
            if self.editor:
                for other in self.editor.color_buttons:
                    if other != self:
                        other.set_selected(False)
                self.editor._update_ui_for_selected_button()
        else:
            self.remove_css_class("selected")

    def _update_color_css(self):
        rgba = self.color
        color_str = rgba.to_string()
        css = f"""
            .gradient-color-picker {{
                background-color: {color_str};
                border-radius: 9999px;
            }}
        """
        self._css_provider.load_from_string(css)

        if is_light_color_rgba(rgba):
            self._icon.get_style_context().add_class("dark")
        else:
            self._icon.get_style_context().remove_class("dark")

    def set_step(self, step: float) -> None:
        self.step = max(0.0, min(1.0, step))

    def set_selected(self, selected: bool) -> None:
        self.selected = selected

    def set_color(self, color) -> None:
        if isinstance(color, str):
            rgba = Gdk.RGBA()
            rgba.parse(color)
            self.color = rgba
        else:
            self.color = color

    def get_color(self) -> Gdk.RGBA:
        return self.color

    def get_color_string(self) -> str:
        return self.color.to_string()

    def get_step(self) -> float:
        return self.step

    def get_selected(self) -> bool:
        return self.selected

    def open_color_picker(self, on_select: Optional[Callable[[], None]] = None) -> None:
        if self._color_dialog is None:
            self._color_dialog = Gtk.ColorDialog(with_alpha=False)

        root = self.get_root()
        current_color = self.color

        def on_color_chosen(dialog, result):
            try:
                new_color = dialog.choose_rgba_finish(result)
                self.set_property("color", new_color)

                if on_select:
                    on_select()
            except GLib.Error:
                pass

        self._color_dialog.choose_rgba(
            root,
            current_color,
            None,
            on_color_chosen
        )

class GradientEditor(Gtk.Box):
    __gtype_name__ = "GradientEditor"

    def __init__(self, **kwargs):
        super().__init__(orientation=Gtk.Orientation.HORIZONTAL, **kwargs)

        self.set_hexpand(False)
        self.set_halign(Gtk.Align.CENTER)
        self.set_size_request(248, 34)
        self.add_css_class("gradient-editor")

        self.color_buttons: List[GradientColorButton] = []
        self.drag_offset: Optional[Tuple[float, float]] = None
        self.selector: Optional["GradientSelector"] = None
        self._gradient_changed_callback: Optional[Callable[[List[Tuple[float, str]]], None]] = None

        self.overlay = Gtk.Overlay()
        self.append(self.overlay)

        self.gradient_background = Gtk.Box()
        self.gradient_background.set_hexpand(False)
        self.gradient_background.set_size_request(248, 34)
        self.gradient_background.add_css_class("gradient-background")

        self.gradient_background.connect("notify::width", self._on_gradient_background_size_changed)

        self._gradient_css_provider = Gtk.CssProvider()
        self.gradient_background.get_style_context().add_provider(
            self._gradient_css_provider,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION + 1
        )

        self.button_container = Gtk.Fixed(overflow=Gtk.Overflow.VISIBLE)
        self.button_container.set_hexpand(False)
        self.button_container.set_size_request(248, 36)

        self.overlay.set_child(self.gradient_background)
        self.overlay.add_overlay(self.button_container)

        self.click_controller = Gtk.GestureClick()
        self.click_controller.connect("pressed", self._on_background_clicked)
        self.button_container.add_controller(self.click_controller)

    def set_on_gradient_changed(self, callback: Callable[[List[Tuple[float, str]]], None]):
        self._gradient_changed_callback = callback

    def _on_gradient_changed(self):
        if self._gradient_changed_callback:
            self._gradient_changed_callback(self.get_gradient_data())

    def _on_gradient_background_size_changed(self, widget, pspec):
        self._update_button_positions()

    def get_gradient_data(self) -> List[Tuple[float, str]]:
        sorted_buttons = sorted(self.color_buttons, key=lambda b: b.get_step())
        return [(btn.get_step(), btn.get_color_string()) for btn in sorted_buttons]


    def _add_color_button(self, button: GradientColorButton):
        self.color_buttons.append(button)
        button.editor = self

        button.connect("notify::color", self._on_color_changed)

        drag_controller = Gtk.GestureDrag()
        drag_controller.set_touch_only(False)
        drag_controller.connect("drag-begin", self._on_drag_begin)
        drag_controller.connect("drag-update", self._on_drag_update)
        drag_controller.connect("drag-end", self._on_drag_end)
        button.add_controller(drag_controller)

        self.button_container.put(button, 0, -2)
        self._on_gradient_changed()

    def _remove_button(self, button: GradientColorButton):
        if len(self.color_buttons) > 2:
            was_selected = button.get_selected()
            self.color_buttons.remove(button)
            self.button_container.remove(button)
            button.editor = None
            self._update_ui_for_selected_button()

            self._update_gradient_css()
            self._on_gradient_changed()

    def _get_container_pos(self, button):
        pointer = self.get_display().get_default_seat().get_pointer()
        _, px, py, _ = self.button_container.get_native().get_surface().get_device_position(pointer)
        return self.translate_coordinates(self.button_container, px, py)

    def _on_drag_begin(self, controller, start_x, start_y):
        button = controller.get_widget()
        button._has_moved = False
        button.set_selected(True)
        current_pos = self.button_container.get_child_position(button)
        container_pos = self._get_container_pos(button)
        self.drag_offset = (current_pos.x - container_pos[0], current_pos.y - container_pos[1])

    def _on_drag_update(self, controller, offset_x, offset_y):
        if self.drag_offset is None:
            return

        button = controller.get_widget()

        drag_distance = math.sqrt(offset_x * offset_x + offset_y * offset_y)
        if drag_distance > 1:
            button._has_moved = True

        container_width = self.gradient_background.get_allocated_width()
        button_width = button.get_allocated_width()

        if container_width <= 0 or button_width <= 0:
            return

        pointer_x_in_container, _ = self._get_container_pos(button)

        new_x = pointer_x_in_container + self.drag_offset[0]

        min_x = 0
        max_x = container_width - button_width
        clamped_x = max(min_x, min(max_x, new_x))

        button_center_x = clamped_x + (button_width / 2.0)
        new_step = button_center_x / container_width

        new_step = max(0.00, min(1.00, new_step))

        if not self._check_overlap_at_step(button, new_step):
            button.set_step(new_step)
            step_position = new_step * container_width - (button_width / 2.0)
            step_position = max(0, min(container_width - button_width, step_position))
            self.button_container.move(button, int(step_position), 0)
            self._update_gradient_css()

    def _on_drag_end(self, controller, offset_x, offset_y):
        button = controller.get_widget()

        if not button._has_moved:
            button.open_color_picker(on_select=lambda: self._on_gradient_changed())
        else:
            self._on_gradient_changed()

        self.drag_offset = None
        self._update_gradient_css()

    def _check_overlap_at_step(self, moving_button: GradientColorButton, step: float) -> bool:
        container_width = self.gradient_background.get_allocated_width()
        button_width = moving_button.get_allocated_width()
        if button_width <= 0:
            button_width = 34

        proposed_center = step * container_width
        proposed_left = proposed_center - (button_width / 2)
        proposed_right = proposed_left + button_width

        overlap_threshold = 0

        for other_button in self.color_buttons:
            if other_button == moving_button:
                continue

            other_step = other_button.get_step()
            other_width = other_button.get_allocated_width()
            if other_width <= 0:
                other_width = 34

            other_center = other_step * container_width
            other_left = other_center - (other_width / 2)
            other_right = other_left + other_width

            if not (proposed_right <= other_left + overlap_threshold or
                    other_right <= proposed_left + overlap_threshold):
                return True

        return False

    def _on_background_clicked(self, gesture, n_press, x, y):
        if n_press == 1:
            width = self.gradient_background.get_allocated_width()

            if len(self.color_buttons) >= 5:
                return;

            step = (x / width)
            step = max(0.0, min(1.0, step))

            min_distance = 0.13
            is_near_existing = any(abs(btn.get_step() - step) < min_distance for btn in self.color_buttons)

            if not is_near_existing:
                color = self._interpolate_color_at_step(step)
                self._create_button_at_step(step, color)

    def _create_button_at_step(self, step: float, color: Gdk.RGBA):
        button = GradientColorButton()
        button.set_step(step)
        button.set_color(color)
        button.add_css_class("gradient-editor-button")

        self._add_color_button(button)
        button.set_selected(True)
        self.color_buttons.sort(key=lambda b: b.get_step())
        self._update_button_positions()
        self._update_gradient_css()

    def _interpolate_color_at_step(self, step: float) -> Gdk.RGBA:
        sorted_buttons = sorted(self.color_buttons, key=lambda b: b.get_step())

        if step <= sorted_buttons[0].get_step():
            return sorted_buttons[0].get_color()
        if step >= sorted_buttons[-1].get_step():
            return sorted_buttons[-1].get_color()

        for i in range(len(sorted_buttons) - 1):
            btn1, btn2 = sorted_buttons[i], sorted_buttons[i + 1]
            if btn1.get_step() <= step <= btn2.get_step():
                if (btn2.get_step() - btn1.get_step()) == 0:
                    return btn1.get_color()
                t = (step - btn1.get_step()) / (btn2.get_step() - btn1.get_step())
                result = Gdk.RGBA()
                result.red = btn1.get_color().red + t * (btn2.get_color().red - btn1.get_color().red)
                result.green = btn1.get_color().green + t * (btn2.get_color().green - btn1.get_color().green)
                result.blue = btn1.get_color().blue + t * (btn2.get_color().blue - btn1.get_color().blue)
                result.alpha = btn1.get_color().alpha + t * (btn2.get_color().alpha - btn1.get_color().alpha)
                return result

        return sorted_buttons[0].get_color()

    def _on_color_changed(self, button, pspec):
        self._update_gradient_css()

    def _update_button_positions(self):
        width = 248

        for button in self.color_buttons:
            step = button.get_step()
            button_width = 34
            center_x = step * width
            x = center_x - (button_width / 2.0)
            x = max(0, min(width - button_width, x))

            x = int(x)
            self.button_container.move(button, x, 0)

        self.button_container.queue_draw()

    def _update_gradient_css(self):
        if not self.color_buttons:
            return

        self.color_buttons.sort(key=lambda b: b.get_step())
        sorted_buttons = self.color_buttons

        if len(sorted_buttons) == 1:
            color = sorted_buttons[0].get_color_string()
            css = f"""
                .gradient-background {{
                    background: {color};
                }}
            """
        else:
            stops = []
            for button in sorted_buttons:
                color = button.get_color_string()
                step = button.get_step()
                stops.append(f"{color} {step * 100}%")

            gradient_stops = ", ".join(stops)
            css = f"""
                .gradient-background {{
                    background: linear-gradient(to right, {gradient_stops});
                }}
            """
        self._gradient_css_provider.load_from_string(css)

    def _update_ui_for_selected_button(self):
        if not self.selector:
            return

        selected_button = None
        for button in self.color_buttons:
            if button.get_selected():
                selected_button = button
                break

        if selected_button:
            step = selected_button.get_step()
            self.selector.step_label.set_label(f"{scale_correction(step):.0%}")
            self.selector.button_revealer.set_reveal_child(True)
            self.selector.remove_button_revealer.set_reveal_child(len(self.color_buttons) > 2)
        else:
            self.selector.button_revealer.set_reveal_child(False)

    def get_selected_button(self) -> Optional[GradientColorButton]:
        for button in self.color_buttons:
            if button.get_selected():
                return button
        return None

    def remove_selected_button(self):
        selected_button = self.get_selected_button()
        if selected_button:
            self._remove_button(selected_button)

    def get_gradient_data(self) -> List[Tuple[float, str]]:
        sorted_buttons = sorted(self.color_buttons, key=lambda b: b.get_step())
        return [(scale_correction(btn.get_step()), btn.get_color_string()) for btn in sorted_buttons]

    def set_gradient_data(self, data: List[Tuple[float, str]]):
        for button in self.color_buttons[:]:
            self.button_container.remove(button)
        self.color_buttons.clear()

        for i, (step, color_string) in enumerate(data):
            step = reverse_scale_correction(step)
            button = GradientColorButton()
            button.set_step(step)
            button.set_color(color_string)
            button.add_css_class("gradient-editor-button")
            self._add_color_button(button)

        self._update_button_positions()
        self._update_gradient_css()

def scale_correction(value: float) -> float:
    return (value - 0.07) / (0.93 - 0.07)

def reverse_scale_correction(value: float) -> float:
    return value * (0.93 - 0.07) + 0.07
