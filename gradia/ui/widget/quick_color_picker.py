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

class QuickColorPicker(Gtk.Box):
    __gtype_name__ = 'QuickColorPicker'

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
        self._setup_ui()
        self._setup_bindings()

    def _setup_ui(self):
        self.main_button = Gtk.Button()
        self.main_button.set_has_frame(False)
        self.main_button.add_css_class('flat')
        self.main_button.add_css_class('color-hover-bg')

        self.main_icon = Gtk.Image()
        self.main_icon.set_icon_size(Gtk.IconSize.NORMAL)
        self.main_icon.set_pixel_size(20)
        self.main_button.set_child(self.main_icon)

        self.popover = Gtk.Popover()
        self.popover.set_parent(self.main_button)
        self.popover.set_position(Gtk.PositionType.BOTTOM)

        self._setup_popover_content()

        self.main_button.connect('clicked', self._on_main_button_clicked)
        self._apply_hover_background(self.main_button, self.color)
        self.append(self.main_button)
        self._update_icon_color()

    def _setup_popover_content(self):
        popover_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)

        base_colors = [
            ((0.88, 0.11, 0.14), _("Red")),
            ((0.18, 0.76, 0.49), _("Green")),
            ((0.21, 0.52, 0.89), _("Blue")),
            ((0.96, 0.83, 0.18), _("Yellow")),
            ((0.57, 0.25, 0.67), _("Purple")),
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
            popover_box.append(color_button)

        more_colors_button = Gtk.Button()
        more_colors_button.set_has_frame(False)
        more_colors_button.add_css_class('flat')
        more_colors_button.add_css_class('color-hover-bg')
        more_colors_icon = Gtk.Image.new_from_icon_name('color-symbolic')
        more_colors_icon.set_icon_size(Gtk.IconSize.NORMAL)
        more_colors_button.set_child(more_colors_icon)
        more_colors_button.connect('clicked', self._on_more_colors_clicked)
        more_colors_button.set_tooltip_text(_('More colors...'))
        popover_box.append(more_colors_button)

        self.popover.set_child(popover_box)

    def _create_color_button(self, color, name):
        button = Gtk.Button()
        button.set_has_frame(False)
        button.add_css_class('flat')
        button.add_css_class('color-hover-bg')

        icon = Gtk.Image()
        icon.set_icon_size(Gtk.IconSize.NORMAL)
        button.set_child(icon)

        self._apply_color_to_icon(icon, color)
        self._apply_hover_background(button, color)

        button.connect('clicked', lambda btn, c=color: self._on_color_selected(c))
        button.set_tooltip_text(name)

        return button

    def _apply_color_to_icon(self, icon, color):
        if color.alpha == 0.0:
            icon.set_from_icon_name('checkerboard-symbolic')
            css_provider = Gtk.CssProvider()
            css = """
            image {
                color: unset;
                opacity: 1.0;
            }
            """
            css_provider.load_from_data(css.encode())
            icon.get_style_context().add_provider(
                css_provider,
                Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
            )
        else:
            icon.set_from_icon_name('color-picker-symbolic')
            css_provider = Gtk.CssProvider()
            css = f"""
            image {{
                color: rgba({int(color.red * 255)}, {int(color.green * 255)}, {int(color.blue * 255)}, {color.alpha});
                opacity: 1.0;
            }}
            """
            css_provider.load_from_data(css.encode())
            icon.get_style_context().add_provider(
                css_provider,
                Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
            )

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

    def _on_main_button_clicked(self, button):
        self.popover.popup()

    def _on_color_selected(self, color):
        self.set_property('color', color)
        self.popover.popdown()
        self.emit('color-changed', color)

    def _on_more_colors_clicked(self, button):
        self.popover.popdown()

        color_dialog = Gtk.ColorDialog()
        color_dialog.set_title(_("Choose Color"))
        color_dialog.set_with_alpha(self.with_alpha)

        toplevel = self.get_root()

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
        self._update_icon_color()

    def _on_quick_colors_alpha_changed(self, widget, pspec):
        self._setup_popover_content()

    def _on_show_black_white_changed(self, widget, pspec):
        self._setup_popover_content()

    def _update_icon_color(self):
        color = self.get_property('color')
        self._apply_color_to_icon(self.main_icon, color)
        self._apply_hover_background(self.main_button, color)

    def get_color(self):
        return self.get_property('color')

    def set_color(self, color):
        self.set_property('color', color)
        self.emit('color-changed', color)

    def get_show_black_white(self):
        return self.get_property('show-black-white')

    def set_show_black_white(self, show):
        self.set_property('show-black-white', show)

    def do_dispose(self):
        if self.popover:
            self.popover.unparent()
        super().do_dispose()
