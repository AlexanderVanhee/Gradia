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

import gi
gi.require_version("GtkSource", "5")

from gi.repository import Gtk, Adw, GtkSource, GLib, Gdk, Gio, GObject
from gradia.constants import rootdir  # pyright: ignore
from gradia.backend.logger import Logger
from gradia.backend.settings import Settings
from gradia.utils.timestamp_filename import TimestampedFilenameGenerator
import cairo
import os
import datetime

logger = Logger()

DEFAULT_LANGUAGE = "c"
DEFAULT_TEXT = '''// Gradia 🎨
#include <pthread.h>
#include <stdio.h>

void* say_hello(void* arg) {
    puts("Hello from thread!");
    return NULL;
}

int main() {
    pthread_t t;
    pthread_create(&t, NULL, say_hello, NULL);
    pthread_join(t, NULL);
}'''


DEFAULT_WINDOW_WIDTH = 600
MIN_WINDOW_WIDTH = 150
MAX_WINDOW_WIDTH = 1200


class SourceExporter:
    def __init__(self, widget_to_export: Gtk.Widget, padding: int = 24, scale: float = 2.0):
        self.widget = widget_to_export
        self.padding = padding
        self.scale = scale

    def export_to_png(self, out_path: str):
        width = self.widget.get_allocated_width()
        height = self.widget.get_allocated_height()

        total_width = int((width + self.padding * 2) * self.scale)
        total_height = int((height + self.padding * 2) * self.scale)

        surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, total_width, total_height)
        cr = cairo.Context(surface)

        self._setup_transparent_background(cr)


        if not self.widget.get_realized():
            self.widget.realize()

        snapshot = Gtk.Snapshot()
        type(self.widget).do_snapshot(self.widget, snapshot)
        render_node = snapshot.to_node()

        if render_node:
            cr.save()
            cr.scale(self.scale, self.scale)  # scale everything
            cr.translate(self.padding, self.padding)

            self._apply_rounded_clipping(cr, width, height)

            render_node.draw(cr)
            cr.restore()

        surface.write_to_png(out_path)
        logger.info(f"Exported source image to: {out_path}")

    def _setup_transparent_background(self, cr):
        cr.set_operator(cairo.OPERATOR_CLEAR)
        cr.paint()
        cr.set_operator(cairo.OPERATOR_OVER)

    def _apply_rounded_clipping(self, cr, width, height, radius=12):
        cr.new_path()
        cr.arc(radius, radius, radius, 3.14159, 3 * 3.14159 / 2)
        cr.arc(width - radius, radius, radius, 3 * 3.14159 / 2, 0)
        cr.arc(width - radius, height - radius, radius, 0, 3.14159 / 2)
        cr.arc(radius, height - radius, radius, 3.14159 / 2, 3.14159)
        cr.close_path()
        cr.clip()


class ResizeHandle(Gtk.Box):
    def __init__(self):
        super().__init__()
        self.set_size_request(10, -1)
        self.set_cursor(Gdk.Cursor.new_from_name("ew-resize"))
        self.get_style_context().add_class("resize-handle")

        separator = Gtk.Separator(orientation=Gtk.Orientation.VERTICAL)
        separator.set_valign(Gtk.Align.FILL)
        separator.set_opacity(0.0)
        self.append(separator)


class DragController:
    def __init__(self, content_box, resize_handle):
        self.content_box = content_box
        self.resize_handle = resize_handle
        self.initial_width = DEFAULT_WINDOW_WIDTH
        self.dragging = False

        self._setup_controllers()

    def _setup_controllers(self):
        self.motion_controller = Gtk.EventControllerMotion()
        self.resize_handle.add_controller(self.motion_controller)
        self.motion_controller.connect("motion", self._on_motion)

        self.drag_gesture = Gtk.GestureDrag()
        self.drag_gesture.set_button(1)
        self.resize_handle.add_controller(self.drag_gesture)

        self.drag_gesture.connect("drag-begin", self._on_drag_begin)
        self.drag_gesture.connect("drag-update", self._on_drag_update)
        self.drag_gesture.connect("drag-end", self._on_drag_end)

    def _on_drag_begin(self, gesture, start_x, start_y):
        self.initial_width = self.content_box.get_allocated_width()
        self.dragging = True

    def _on_drag_update(self, gesture, offset_x, offset_y):
        if not self.dragging:
            return

        new_width = max(MIN_WINDOW_WIDTH,
                        min(MAX_WINDOW_WIDTH, int(self.initial_width + offset_x)))

        self.content_box.set_size_request(new_width, -1)
        self.content_box.queue_allocate()

    def _on_drag_end(self, gesture, offset_x, offset_y):
        self.dragging = False

    def _on_motion(self, controller, x, y):
        if self.dragging:
            self.content_box.queue_draw()


class ResizableContainer(Gtk.Box):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.set_orientation(Gtk.Orientation.HORIZONTAL)
        self.set_halign(Gtk.Align.CENTER)
        self.set_valign(Gtk.Align.START)

        self.content_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.content_box.set_size_request(DEFAULT_WINDOW_WIDTH, -1)

        self.resize_handle = ResizeHandle()
        self.drag_controller = DragController(self.content_box, self.resize_handle)

        self.append(self.content_box)
        self.append(self.resize_handle)

    def set_child_widget(self, widget):
        child = self.content_box.get_first_child()
        if child:
            self.content_box.remove(child)

        if widget:
            self.content_box.append(widget)

    def get_content_width(self):
        return self.content_box.get_allocated_width()


class SourceViewManager:
    def __init__(self):
        self.source_view = GtkSource.View.new()
        self.source_buffer = self.source_view.get_buffer()
        self._text_changed_callback = None
        self._setup_source_view()
        self._connect_signals()

    def _setup_source_view(self):
        self.source_view.set_top_margin(10)
        self.source_view.set_right_margin(10)
        self.source_view.set_left_margin(10)
        self.source_view.set_bottom_margin(10)
        self.source_view.set_valign(Gtk.Align.START)
        self.source_buffer.set_highlight_syntax(True)
        self.source_view.set_monospace(True)
        self.source_view.set_wrap_mode(Gtk.WrapMode.WORD_CHAR)
        self.source_view.set_show_line_numbers(True)

    def _connect_signals(self):
        self.source_buffer.connect('changed', self._on_text_changed)

    def _on_text_changed(self, buffer):
        if self._text_changed_callback:
            text = buffer.get_text(buffer.get_start_iter(), buffer.get_end_iter(), False)
            self._text_changed_callback(text)

    def set_text(self, text):
        self.source_buffer.set_text(text)

    def get_text(self):
        return self.source_buffer.get_text(
            self.source_buffer.get_start_iter(),
            self.source_buffer.get_end_iter(),
            False
        )

    def set_language(self, language):
        self.source_buffer.set_language(language)

    def set_style_scheme(self, scheme):
        self.source_buffer.set_style_scheme(scheme)

    def set_show_line_numbers(self, show_numbers: bool):
        self.source_view.set_show_line_numbers(show_numbers)

    def set_text_changed_callback(self, callback):
        self._text_changed_callback = callback

    def get_view(self):
        return self.source_view

class LanguageManager:
    def __init__(self):
        self.lang_manager = GtkSource.LanguageManager.get_default()
        self.languages = sorted(self.lang_manager.get_language_ids())

    def get_languages(self):
        return self.languages

    def get_language(self, lang_id):
        return self.lang_manager.get_language(lang_id)


class StyleManager:
    def __init__(self):
        self.style_manager = GtkSource.StyleSchemeManager.get_default()
        self.settings = Gtk.Settings.get_default()
        self.theme_changed_callbacks = []

        self.style_variants = {
            'Adwaita': {
                'light': 'Adwaita',
                'dark': 'Adwaita-dark'
            },
            'Classic': {
                'light': 'classic',
                'dark': 'classic-dark'
            },
            'Cobalt': {
                'light': 'cobalt-light',
                'dark': 'cobalt'
            },
            'Kate': {
                'light': 'kate',
                'dark': 'kate-dark'
            },
            'Solarized': {
                'light': 'solarized-light',
                'dark': 'solarized-dark'
            },
            'Tango/Oblivion': {
                'light': 'tango',
                'dark': 'oblivion'
            }
        }

        self.settings.connect("notify::gtk-application-prefer-dark-theme",
                            self._on_theme_changed)

        self.current_generic_style = 'Adwaita'

    def get_generic_style_names(self):
        return list(self.style_variants.keys())

    def set_current_style(self, generic_name):
        if generic_name in self.style_variants:
            self.current_generic_style = generic_name
            self._notify_theme_changed()

    def get_current_style_id(self):
        is_dark = self.is_dark_theme()
        variant = 'dark' if is_dark else 'light'
        return self.style_variants[self.current_generic_style][variant]

    def get_current_generic_style(self):
        return self.current_generic_style

    def get_scheme(self, scheme_id=None):
        if scheme_id is None:
            scheme_id = self.get_current_style_id()
        return self.style_manager.get_scheme(scheme_id)

    def is_dark_theme(self):
        return self.settings.get_property("gtk-application-prefer-dark-theme")

    def connect_theme_changed(self, callback):
        self.theme_changed_callbacks.append(callback)

    def disconnect_theme_changed(self, callback):
        if callback in self.theme_changed_callbacks:
            self.theme_changed_callbacks.remove(callback)

    def _on_theme_changed(self, settings, param):
        self._notify_theme_changed()

    def _notify_theme_changed(self):
        current_style_id = self.get_current_style_id()
        for callback in self.theme_changed_callbacks:
            callback(current_style_id, self.current_generic_style)


class FakeWindowManager:
    def __init__(self, source_view):
        self.source_view = source_view
        self.fake_window_container = None
        self.header_bar = None
        self.title_entry = None
        self.current_style_provider = None
        self.settings = Settings()

    def create_fake_window(self):
        if self.fake_window_container:
            return self.fake_window_container

        frame = Gtk.Frame(valign=Gtk.Align.START, margin_top=12)
        frame.add_css_class("window-border")
        frame.add_css_class("card")


        self.fake_window_container = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        self.fake_window_container.get_style_context().add_class("adw-window")

        self.header_bar = Adw.HeaderBar.new()

        self.title_entry = Gtk.Entry(xalign=0.5, focus_on_click=False)
        self.title_entry.set_text(self.settings.source_snippet_title)
        self.title_entry.set_halign(Gtk.Align.CENTER)
        self.title_entry.set_valign(Gtk.Align.CENTER)
        self.title_entry.set_width_chars(45)
        self.title_entry.set_max_length(100)
        self.title_entry.set_has_frame(False)
        self.title_entry.get_style_context().add_class("title")
        self.title_entry.get_style_context().add_class("title-entry")

        def on_title_entry_changed(entry):
            new_title = entry.get_text()
            self.settings.source_snippet_title = new_title

        self.title_entry.connect("changed", on_title_entry_changed)

        self.header_bar.set_title_widget(self.title_entry)

        source_view_container = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        source_view_container.append(self.source_view)

        self.fake_window_container.append(self.header_bar)
        self.fake_window_container.append(source_view_container)

        frame.set_child(self.fake_window_container)

        return frame

    def update_header_colors(self, style_scheme):
        if not self.header_bar or not self.title_entry:
            return

        if self.current_style_provider:
            self.header_bar.get_style_context().remove_provider(self.current_style_provider)
            self.title_entry.get_style_context().remove_provider(self.current_style_provider)

        bg_color, fg_color = self._extract_header_colors(style_scheme)

        if bg_color and fg_color:
            css_data = f"""
            headerbar {{
                background: {bg_color};
                color: {fg_color};
                border-bottom: 1px solid alpha({fg_color}, 0.1);
            }}

            """

            self.current_style_provider = Gtk.CssProvider()
            self.current_style_provider.load_from_data(css_data.encode())

            self.header_bar.get_style_context().add_provider(
                self.current_style_provider,
                Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
            )
            self.title_entry.get_style_context().add_provider(
                self.current_style_provider,
                Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
            )

    def _extract_header_colors(self, style_scheme):
        scheme_id = style_scheme.get_id()

        if scheme_id in ("Adwaita", "Adwaita-dark"):
            return None, None
        text_style = style_scheme.get_style("text")
        bg_color = text_style.get_property("background")
        fg_color = text_style.get_property("foreground")

        return bg_color, fg_color


    def destroy_fake_window(self):
        if self.current_style_provider and self.header_bar:
            self.header_bar.get_style_context().remove_provider(self.current_style_provider)
            if self.title_entry:
                self.title_entry.get_style_context().remove_provider(self.current_style_provider)

        self.fake_window_container = None
        self.header_bar = None
        self.title_entry = None
        self.current_style_provider = None

    def get_container(self):
        return self.fake_window_container


@Gtk.Template(resource_path=f"{rootdir}/ui/image_generator_window.ui")
class SourceImageGeneratorWindow(Adw.Window):
    __gtype_name__ = "SourceviewtestWindow"

    export_button = Gtk.Template.Child()
    scroller = Gtk.Template.Child()
    language_dropdown = Gtk.Template.Child()
    style_scheme_dropdown = Gtk.Template.Child()
    fake_window_button = Gtk.Template.Child()
    line_numbers_button = Gtk.Template.Child()
    toolbar_view = Gtk.Template.Child()

    def __init__(self, parent_window, temp_dir=None, export_callback=None, **kwargs):
        super().__init__(
            title=_("Source Snippets"),
            modal=True,
            transient_for=parent_window,
            **kwargs
        )
        self.settings = Settings()

        self.temp_dir = temp_dir
        self.export_callback = export_callback
        self.parent_window = parent_window

        self.source_view_manager = SourceViewManager()
        self.language_manager = LanguageManager()
        self.style_manager = StyleManager()
        self.fake_window_manager = FakeWindowManager(self.source_view_manager.get_view())

        self._setup_ui()
        self._setup_dropdowns()
        self._setup_initial_state()
        self._connect_signals()

        self.settings.bind_switch(self.fake_window_button,"source-snippet-show-frame")
        self.settings.bind_switch(self.line_numbers_button,"source-snippet-show-line-numbers")

    def _setup_ui(self):
        self.resizable_container = ResizableContainer()
        self.scroller.set_child(self.resizable_container)
        self.source_view_manager.set_text(self.settings.source_snippet_code_text)
        self.style_manager.set_current_style(self.settings.source_snippet_style_scheme)
        def update_settings(text):
            self.settings.source_snippet_code_text = text

        self.source_view_manager.set_text_changed_callback(update_settings)


    def _setup_dropdowns(self):
        languages = self.language_manager.get_languages()
        self.language_dropdown.set_model(Gtk.StringList.new(languages))

        expression = Gtk.ClosureExpression.new(
            GObject.TYPE_STRING, lambda obj: obj.get_string(), None
        )

        self.language_dropdown.set_expression(expression)
        initial_language = self.settings.source_snippet_language

        if initial_language in languages:
            index = languages.index(initial_language)
            self.language_dropdown.set_selected(index)
            language = self.language_manager.get_language(initial_language)
            self.source_view_manager.set_language(language)

        generic_styles = self.style_manager.get_generic_style_names()
        self.style_scheme_dropdown.set_model(Gtk.StringList.new(generic_styles))


        default_generic_style = self.style_manager.get_current_generic_style()
        if default_generic_style in generic_styles:
            index = generic_styles.index(default_generic_style)
            self.style_scheme_dropdown.set_selected(index)

        scheme = self.style_manager.get_scheme()
        self.source_view_manager.set_style_scheme(scheme)

    def _setup_initial_state(self):
        self.fake_window_button.set_active(True)
        self.line_numbers_button.set_active(True)
        self._update_view_mode()
        self._update_line_numbers()

    def _connect_signals(self):
        self.export_button.connect("clicked", self._on_export_clicked)
        self.language_dropdown.connect("notify::selected", self._on_language_changed)
        self.style_scheme_dropdown.connect("notify::selected", self._on_style_scheme_changed)
        self.fake_window_button.connect("notify::state", self._on_fake_window_toggled)
        self.line_numbers_button.connect("notify::state", self._on_line_numbers_toggled)
        self.style_manager.connect_theme_changed(self._on_theme_changed)

    def _safely_unparent_widget(self, widget):
        parent = widget.get_parent()
        if parent:
            if hasattr(parent, 'remove'):
                parent.remove(widget)
            elif hasattr(parent, 'set_child'):
                parent.set_child(None)

    def _update_view_mode(self):
        self.resizable_container.set_child_widget(None)

        source_view = self.source_view_manager.get_view()
        self._safely_unparent_widget(source_view)

        if self.fake_window_button.get_active():
            fake_window_frame = self.fake_window_manager.create_fake_window()
            self.resizable_container.set_child_widget(fake_window_frame)
            scheme = self.style_manager.get_scheme()
            self.fake_window_manager.update_header_colors(scheme)
        else:
            frame = Gtk.Frame(valign=Gtk.Align.START, margin_top=12)
            frame.add_css_class("window-border")
            frame.add_css_class("card")
            frame.set_child(source_view)
            self.resizable_container.set_child_widget(frame)

    def _update_line_numbers(self):
        show_line_numbers = self.line_numbers_button.get_active()
        self.source_view_manager.set_show_line_numbers(show_line_numbers)

    def _on_export_clicked(self, _button):
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")

        filename = TimestampedFilenameGenerator().generate(_("Source Snippit From %Y-%m-%d %H-%M-%S")) + ".png"

        if self.temp_dir:
            output_path = os.path.join(self.temp_dir, filename)
        else:
            output_path = os.path.join(os.getcwd(), filename)

        widget_to_export = self._get_export_widget()
        widget_to_export.get_root().grab_focus()
        exporter = SourceExporter(widget_to_export)
        exporter.export_to_png(output_path)

        self.export_callback(output_path)
        self.close()

    def _on_language_changed(self, dropdown, _param):
        languages = self.language_manager.get_languages()
        index = dropdown.get_selected()
        if 0 <= index < len(languages):
            language = self.language_manager.get_language(languages[index])
            self.source_view_manager.set_language(language)
            self.settings.source_snippet_language = languages[index]

    def _on_style_scheme_changed(self, dropdown, _param):
        generic_styles = self.style_manager.get_generic_style_names()
        index = dropdown.get_selected()
        if 0 <= index < len(generic_styles):
            generic_name = generic_styles[index]
            self.style_manager.set_current_style(generic_name)
            self.settings.source_snippet_style_scheme = generic_name
            if self.fake_window_button.get_active():
                scheme = self.style_manager.get_scheme()
                self.fake_window_manager.update_header_colors(scheme)

    def _on_fake_window_toggled(self, switch, param_spec):
        if not switch.get_state():
            source_view = self.source_view_manager.get_view()
            self._safely_unparent_widget(source_view)
            self.fake_window_manager.destroy_fake_window()
        self._update_view_mode()

    def _on_line_numbers_toggled(self, switch, param_spec):
        self._update_line_numbers()

    def _on_theme_changed(self, style_id, generic_name):
        scheme = self.style_manager.get_scheme(style_id)
        self.source_view_manager.set_style_scheme(scheme)
        if self.fake_window_button.get_active():
            self.fake_window_manager.update_header_colors(scheme)

    def _get_export_widget(self) -> Gtk.Widget:
        if self.fake_window_button.get_active():
            return self.fake_window_manager.get_container()
        else:
            return self.source_view_manager.get_view()
