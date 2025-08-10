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

class QuickColorPicker(Gtk.Box):
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

    quick_colors_alpha = GObject.Property(
        type=float,
        default=1.0,
        minimum=0.0,
        maximum=1.0,
        flags=GObject.ParamFlags.READWRITE
    )

    show_black_white = GObject.Property(
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
        self._setup_ui()
        self._setup_bindings()

    def _setup_ui(self):
        self._create_color_row()

    def _create_color_row(self):
        while self.get_first_child():
            self.remove(self.get_first_child())

        self._selected_button = None

        base_colors = [
            ((0.88, 0.11, 0.14), _("Red")),
            ((0.18, 0.76, 0.49), _("Green")),
            ((0.21, 0.52, 0.89), _("Blue")),
            ((0.96, 0.83, 0.18), _("Yellow")),
        ]

        if self.show_black_white:
            base_colors.extend([
                ((0.0, 0.0, 0.0), _("Black")),
                ((1.0, 1.0, 1.0), _("White")),
            ])

        self.color_palette = [
            (Gdk.RGBA(r, g, b, self.quick_colors_alpha), name)
            for (r, g, b), name in base_colors
        ]

        for color, name in self.color_palette:
            color_button = self._create_color_button(color, name)
            self.append(color_button)

        more_colors_button = Gtk.Button()
        more_colors_button.set_has_frame(False)
        more_colors_button.add_css_class('flat')
        more_colors_button.add_css_class('color-hover-bg')
        more_colors_icon = Gtk.Image.new_from_icon_name('color-symbolic')
        more_colors_icon.set_icon_size(Gtk.IconSize.NORMAL)
        more_colors_button.set_child(more_colors_icon)
        more_colors_button.connect('clicked', self._on_more_colors_clicked)
        more_colors_button.set_tooltip_text(_('More colors...'))
        self.append(more_colors_button)

        self._update_selection()

    def _create_color_button(self, color, name):
        button = Gtk.Button()
        button.set_has_frame(False)
        button.add_css_class('flat')
        button.add_css_class('color-hover-bg')

        checkmark = Gtk.Image.new_from_icon_name("object-select-symbolic")
        checkmark.set_pixel_size(12)
        checkmark.add_css_class("checkmark-icon")

        if is_light_color(rgba_to_hex(color)):
            checkmark.add_css_class("dark")

        overlay = Gtk.Overlay(width_request=20, height_request=20)
        overlay.add_overlay(checkmark)
        overlay.set_halign(Gtk.Align.CENTER)
        overlay.set_valign(Gtk.Align.CENTER)

        color_box = Gtk.Box()
        color_box.add_css_class('color-button')
        color_box.set_size_request(24, 24)
        overlay.set_child(color_box)

        button.set_child(overlay)

        self._apply_color_to_box(color_box, color)
        self._apply_hover_background(button, color)

        button._color = color
        button._checkmark = checkmark
        button._color_box = color_box
        button.connect('clicked', lambda btn, c=color: self._on_color_selected(c, btn))
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

    def _setup_bindings(self):
        self.connect('notify::color', self._on_color_property_changed)
        self.connect('notify::quick-colors-alpha', self._on_quick_colors_alpha_changed)
        self.connect('notify::show-black-white', self._on_show_black_white_changed)

    def _on_color_selected(self, color, button):
        if self._selected_button:
            self._selected_button._checkmark.remove_css_class("visible")

        self._selected_button = button
        button._checkmark.add_css_class("visible")

        self.set_property('color', color)
        self.emit('color-changed', color)

    def _on_more_colors_clicked(self, button):
        color_dialog = Gtk.ColorDialog()
        color_dialog.set_title(_("Choose Color"))
        color_dialog.set_with_alpha(self.with_alpha)

        toplevel = None

        color_dialog.choose_rgba(
            toplevel,
            self.get_property('color'),
            None,
            self._on_color_dialog_response
        )

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

    def _on_quick_colors_alpha_changed(self, widget, pspec):
        self._create_color_row()

    def _on_show_black_white_changed(self, widget, pspec):
        self._create_color_row()

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

    def get_show_black_white(self):
        return self.get_property('show-black-white')

    def set_show_black_white(self, show):
        self.set_property('show-black-white', show)



class SimpleColorPicker(Gtk.Button):
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
        self._update_content()
        self._update_color_style()

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

    def _update_color_style(self):
        color = self.get_property('color')

        ctx = self.get_style_context()
        if hasattr(self, "_color_css_provider"):
            ctx.remove_provider(self._color_css_provider)

        css = f"""
        button {{
            background-color: rgb({int(color.red * 255)}, {int(color.green * 255)}, {int(color.blue * 255)});
            border-radius: 9px;
            padding: 8px 12px;
        }}
        """

        provider = Gtk.CssProvider()
        provider.load_from_data(css.encode())
        ctx.add_provider(provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)
        self._color_css_provider = provider

        if is_light_color(rgba_to_hex(color)):
            self.icon.add_css_class("dark")
            self.label.add_css_class("dark")
        else:
            self.icon.remove_css_class("dark")
            self.label.remove_css_class("dark")

    def _on_clicked(self, button):
        color_dialog = Gtk.ColorDialog()
        color_dialog.set_title(_("Choose Color"))
        color_dialog.set_with_alpha(self.with_alpha)

        toplevel = None

        color_dialog.choose_rgba(
            toplevel,
            self.get_property('color'),
            None,
            self._on_color_dialog_response
        )

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
