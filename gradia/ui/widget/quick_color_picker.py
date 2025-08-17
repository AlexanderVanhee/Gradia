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

from gi.repository import Gtk, Adw, Gdk, GObject, Gio
from gradia.utils.colors import is_light_color, rgba_to_hex

class ColorPickerMixin:
    def _get_base_colors(self, alpha=1.0, secondary=False):
        base_colors = [
            (Gdk.RGBA(0.88, 0.11, 0.14, alpha), _("Red")),
            (Gdk.RGBA(0.18, 0.76, 0.49, alpha), _("Green")),
            (Gdk.RGBA(0.21, 0.52, 0.89, alpha), _("Blue")),
            (Gdk.RGBA(0.96, 0.83, 0.18, alpha), _("Yellow")),
            (Gdk.RGBA(0.0, 0.0, 0.0, alpha), _("Black")),
            (Gdk.RGBA(1.0, 1.0, 1.0, alpha), _("White")),
            ]

        if secondary:
            base_colors.append((Gdk.RGBA(0, 0, 0, 0), _("Transparent")))


        return base_colors

    def _create_color_button(self, color, name):
        button = Gtk.Button()
        button.set_has_frame(False)
        button.add_css_class('flat')
        button.add_css_class('color-hover-bg')

        color_box = Gtk.Box()
        color_box.add_css_class('color-button')
        color_box.set_size_request(24, 24)
        button.set_child(color_box)

        self._apply_color_to_box(color_box, color)
        self._apply_hover_background(button, color)

        button.set_tooltip_text(name)
        return button

    def _apply_color_to_box(self, box, color):
        ctx = box.get_style_context()
        if hasattr(box, "_color_css_provider"):
            ctx.remove_provider(box._color_css_provider)

        if color.alpha == 0:
            css = ".color-button { background-color: #b2b2b2; }"
        elif color.alpha < 1.0:
            red = int((color.red * color.alpha + 1.0 * (1.0 - color.alpha)) * 255)
            green = int((color.green * color.alpha + 1.0 * (1.0 - color.alpha)) * 255)
            blue = int((color.blue * color.alpha + 1.0 * (1.0 - color.alpha)) * 255)
            css = f".color-button {{ background-color: rgb({red}, {green}, {blue}); }}"
        else:
            css = f".color-button {{ background-color: rgb({int(color.red * 255)}, {int(color.green * 255)}, {int(color.blue * 255)}); }}"

        provider = Gtk.CssProvider()
        provider.load_from_data(css.encode())
        ctx.add_provider(provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)

        box._color_css_provider = provider
        ctx.remove_class("transparent-color-button-small") if color.alpha > 0 else ctx.add_class("transparent-color-button-small")

    def _apply_hover_background(self, widget, color):
        if color.alpha == 0.0:
            rgba_str = "rgba(128, 128, 128, 0.15)"
        else:
            rgba_str = f"rgba({int(color.red * 255)}, {int(color.green * 255)}, {int(color.blue * 255)}, {color.alpha * 0.15})"

        css_provider = Gtk.CssProvider()
        css = f"""
        .color-hover-bg:hover {{
            background-color: {rgba_str};
        }}
        """
        css_provider.load_from_data(css.encode())
        widget.get_style_context().add_provider(
            css_provider,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
        )

    def _create_more_colors_button(self):
        more_colors_button = Gtk.Button()
        more_colors_button.set_has_frame(False)
        more_colors_button.add_css_class('flat')
        more_colors_button.add_css_class('color-hover-bg')
        more_colors_icon = Gtk.Image.new_from_icon_name('color-symbolic')
        more_colors_icon.set_icon_size(Gtk.IconSize.NORMAL)
        more_colors_button.set_child(more_colors_icon)
        more_colors_button.set_tooltip_text(_('More colors…'))
        return more_colors_button

    def _show_color_dialog(self, callback):
        color_dialog = Gtk.ColorDialog()
        color_dialog.set_title(_("Choose Color"))
        color_dialog.set_with_alpha(self.with_alpha)
        toplevel = None
        color_dialog.choose_rgba(
            toplevel,
            self.get_property('color'),
            None,
            callback
        )
    def get_selected_index(self):
        if not self._selected_button:
            return None
        return list(self).index(self._selected_button)

class QuickColorPicker(Gtk.Box, ColorPickerMixin):
    __gtype_name__ = 'GradiaQuickColorPicker'

    color = GObject.Property(
        type=Gdk.RGBA,
        default=Gdk.RGBA(0.2, 0.4, 1.0, 1.0),
        flags=GObject.ParamFlags.READWRITE
    )

    with_alpha = GObject.Property(
        type=bool,
        default=True,
        flags=GObject.ParamFlags.READWRITE
    )

    __gsignals__ = {
        'color-changed': (GObject.SignalFlags.RUN_FIRST, None, (Gdk.RGBA,))
    }

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.set_orientation(Gtk.Orientation.HORIZONTAL)
        self.set_spacing(4)
        self._selected_button = None
        self._custom_colors = None
        self._setup_ui()
        self._setup_bindings()

    def _setup_ui(self):
        self._create_color_row()

    def _create_color_row(self):
        while self.get_first_child():
            self.remove(self.get_first_child())
        self._selected_button = None

        if self._custom_colors is not None:
            self.color_palette = self._custom_colors
        else:
            self.color_palette = self._get_base_colors()

        for color, name in self.color_palette:
            color_button = self._create_color_button(color, name or rgba_to_hex(color))
            checkmark = Gtk.Image.new_from_icon_name("object-select-symbolic")
            checkmark.set_pixel_size(12)
            checkmark.add_css_class("checkmark-icon")
            if is_light_color(rgba_to_hex(color)):
                checkmark.add_css_class("dark")

            color_box = color_button.get_child()
            color_button.set_child(None)

            overlay = Gtk.Overlay(width_request=20, height_request=20)
            overlay.add_overlay(checkmark)
            overlay.set_halign(Gtk.Align.CENTER)
            overlay.set_valign(Gtk.Align.CENTER)
            overlay.set_child(color_box)
            color_button.set_child(overlay)

            color_button._color = color
            color_button._checkmark = checkmark
            color_button.connect('clicked', lambda btn, c=color: self._on_color_selected(c, btn))
            self.append(color_button)

        more_colors_button = self._create_more_colors_button()
        more_colors_button.connect('clicked', self._on_more_colors_clicked)
        self.append(more_colors_button)
        self._update_selection()

    def _setup_bindings(self):
        self.connect('notify::color', self._on_color_property_changed)

    def _on_color_selected(self, color, button):
        if self._selected_button:
            self._selected_button._checkmark.remove_css_class("visible")
        self._selected_button = button
        button._checkmark.add_css_class("visible")
        self.set_property('color', color)
        self.emit('color-changed', color)

    def _on_more_colors_clicked(self, button):
        self._show_color_dialog(self._on_color_dialog_response)

    def _on_color_dialog_response(self, dialog, result):
        try:
            color = dialog.choose_rgba_finish(result)
            if self._selected_button:
                self._selected_button._checkmark.remove_css_class("visible")
                self._selected_button = None
            self.set_property('color', color)
            self.emit('color-changed', color)
        except Exception:
            pass

    def _on_color_property_changed(self, widget, pspec):
        self._update_selection()

    def _update_selection(self):
        current_color = self.get_property('color')
        for child in self:
            if hasattr(child, '_color'):
                if self._colors_match(child._color, current_color):
                    if self._selected_button:
                        self._selected_button._checkmark.remove_css_class("visible")
                    self._selected_button = child
                    child._checkmark.add_css_class("visible")
                    break

    def _colors_match(self, color1, color2):
        tolerance = 0.01
        return (abs(color1.red - color2.red) < tolerance and
                abs(color1.green - color2.green) < tolerance and
                abs(color1.blue - color2.blue) < tolerance and
                abs(color1.alpha - color2.alpha) < tolerance)

    def get_color(self):
        return self.get_property('color')

    def set_color(self, color):
        self.set_property('color', color)
        self.emit('color-changed', color)

    def set_color_list(self, colors):
        self._custom_colors = colors
        self._create_color_row()

class SimpleColorPicker(Gtk.Button, ColorPickerMixin):
    __gtype_name__ = 'GradiaSimpleColorPicker'

    color = GObject.Property(
        type=Gdk.RGBA,
        default=Gdk.RGBA(0.2, 0.4, 1.0, 1.0),
        flags=GObject.ParamFlags.READWRITE
    )

    icon_name = GObject.Property(
        type=str,
        default="",
        flags=GObject.ParamFlags.READWRITE
    )

    text = GObject.Property(
        type=str,
        default="",
        flags=GObject.ParamFlags.READWRITE
    )

    with_alpha = GObject.Property(
        type=bool,
        default=True,
        flags=GObject.ParamFlags.READWRITE
    )

    __gsignals__ = {
        'color-changed': (GObject.SignalFlags.RUN_FIRST, None, (Gdk.RGBA,))
    }

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.set_has_frame(False)
        self.add_css_class('flat')
        self._custom_colors = None
        self._setup_ui()
        self._setup_bindings()
        self.connect('clicked', self._on_clicked)

    def _setup_ui(self):
        self.content_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        self.content_box.set_halign(Gtk.Align.CENTER)
        self.content_box.set_valign(Gtk.Align.CENTER)

        self.icon = Gtk.Image()
        self.icon.set_visible(False)

        self.label = Gtk.Label()
        self.label.set_visible(False)

        self.content_box.append(self.icon)
        self.content_box.append(self.label)

        self.set_child(self.content_box)

        self.popover = Gtk.Popover()
        self.popover.set_parent(self)
        self.popover.set_position(Gtk.PositionType.BOTTOM)
        self._setup_popover_content()

        self._update_content()
        self._update_color_style()

    def _setup_popover_content(self):
        popover_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)

        if self._custom_colors is not None:
            color_palette = self._custom_colors
        else:
            color_palette = self._get_base_colors(secondary=True)

        for color, name in color_palette:
            color_button = self._create_color_button(color, name)
            color_button.connect('clicked', lambda btn, c=color: self._on_color_selected(c))
            popover_box.append(color_button)

        more_colors_button = self._create_more_colors_button()
        more_colors_button.connect('clicked', self._on_more_colors_clicked)
        popover_box.append(more_colors_button)

        self.popover.set_child(popover_box)

    def _setup_bindings(self):
        self.connect('notify::color', self._on_color_property_changed)
        self.connect('notify::icon-name', self._on_icon_name_changed)
        self.connect('notify::text', self._on_text_changed)

    def _update_content(self):
        icon_name = self.get_property('icon-name')
        text = self.get_property('text')

        if icon_name:
            self.icon.set_from_icon_name(icon_name)
            self.icon.set_visible(True)
        else:
            self.icon.set_visible(False)

        if text:
            self.label.set_text(text)
            self.label.set_visible(True)
        else:
            self.label.set_visible(False)

        if not icon_name and not text:
            self.content_box.set_size_request(24, 24)
        else:
            self.content_box.set_size_request(-1, -1)

    def _update_color_style(self):
        color = self.get_property('color')

        ctx = self.get_style_context()
        if hasattr(self, "_color_css_provider"):
            ctx.remove_provider(self._color_css_provider)

        if color.alpha == 0:
            css = """
                button {
                    background-color: #b2b2b2;
                }
                """
            self.remove_css_class("transparent-simple-color-picker")
            self.add_css_class("transparent-simple-color-picker")
        else:
            css = f"""
                button {{
                    background-color: rgba({int(color.red * 255)}, {int(color.green * 255)}, {int(color.blue * 255)}, {color.alpha});
                }}
                """
            self.remove_css_class("transparent-simple-color-picker")

        provider = Gtk.CssProvider()
        provider.load_from_data(css.encode())
        ctx.add_provider(provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)
        self._color_css_provider = provider
        self.add_css_class("simple-color-picker")

        if is_light_color(rgba_to_hex(color)):
            self.icon.add_css_class("dark")
            self.label.add_css_class("dark")
        else:
            self.icon.remove_css_class("dark")
            self.label.remove_css_class("dark")

    def _on_clicked(self, button):
        self.popover.popup()

    def _on_color_selected(self, color):
        self.set_property('color', color)
        self.popover.popdown()
        self.emit('color-changed', color)

    def _on_more_colors_clicked(self, button):
        self.popover.popdown()
        self._show_color_dialog(self._on_color_dialog_response)

    def _on_color_dialog_response(self, dialog, result):
        try:
            color = dialog.choose_rgba_finish(result)
            self.set_property('color', color)
            self.emit('color-changed', color)
        except Exception:
            pass

    def _on_color_property_changed(self, widget, pspec):
        self._update_color_style()

    def _on_icon_name_changed(self, widget, pspec):
        self._update_content()

    def _on_text_changed(self, widget, pspec):
        self._update_content()

    def get_color(self):
        return self.get_property('color')

    def set_color(self, color, emit=True):
        self.set_property('color', color)
        if emit:
            self.emit('color-changed', color)

    def get_icon_name(self):
        return self.get_property('icon-name')

    def set_icon_name(self, icon_name):
        self.set_property('icon-name', icon_name)

    def get_text(self):
        return self.get_property('text')

    def set_text(self, text):
        self.set_property('text', text)

    def set_color_list(self, colors):
        self._custom_colors = colors
        self._setup_popover_content()

    def set_color_by_index(self, index, emit=True):
        if index == None:
            return
        palette = self._custom_colors if self._custom_colors is not None else self._get_base_colors(secondary=True)
        if 0 <= index < len(palette):
            color, _ = palette[index]
            self.set_color(color, emit=emit)

    def do_dispose(self):
        if self.popover:
            self.popover.unparent()
        super().do_dispose()

