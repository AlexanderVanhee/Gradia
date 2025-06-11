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

from collections.abc import Callable
from typing import Optional
from gi.repository import Gtk, Gio, Adw, Gdk, GLib

from gradia.overlay.drawing_overlay import DrawingOverlay
from gradia.overlay.transparency_overlay import TransparencyBackground
from gradia.ui.recent_picker import RecentPicker
from gradia.ui.drawing_tools_group import DrawingToolsGroup

@Gtk.Template(resource_path="/be/alexandervanhee/gradia/ui/header_bar.ui")
class HeaderBar(Adw.Bin):
    __gtype_name__ = "HeaderBarContainer"
    def __init__(self):
        super().__init__()

@Gtk.Template(resource_path="/be/alexandervanhee/gradia/ui/controls_overlay.ui")
class ControlsOverlay(Gtk.Box):
    __gtype_name__ = "ControlsOverlay"

    delete_revealer = Gtk.Template.Child()

    def __init__(self):
        super().__init__()

    def set_delete_visible(self, show: bool):
        self.delete_revealer.set_reveal_child(show)

def create_image_stack() -> tuple[Gtk.Stack, Gtk.Picture, Adw.Spinner, 'DrawingOverlay', 'ControlsOverlay', Gtk.Overlay]:
    stack = Gtk.Stack.new()
    stack.set_vexpand(True)
    stack.set_hexpand(True)
    stack.set_transition_type(Gtk.StackTransitionType.CROSSFADE)
    stack.set_transition_duration(200)

    picture = create_picture_widget()

    transparency_background = TransparencyBackground()
    transparency_background.set_hexpand(True)
    transparency_background.set_vexpand(True)
    transparency_background.set_picture_reference(picture)

    image_overlay = Gtk.Overlay()
    image_overlay.set_child(transparency_background)
    image_overlay.add_overlay(picture)

    drawing_overlay = create_drawing_overlay(picture)

    overlay, controls_overlay = create_image_overlay(image_overlay, drawing_overlay)

    drawing_overlay.set_controls_overlay(controls_overlay)

    stack.add_named(overlay, "image")

    spinner_box, spinner = create_spinner_widget()
    stack.add_named(spinner_box, "loading")
    stack.set_visible_child_name("loading")

    create_drop_target(stack)

    main_overlay = Gtk.Overlay()
    main_overlay.set_child(stack)

    top_bar = Adw.HeaderBar()
    top_bar.get_style_context().add_class("flat")
    top_bar.get_style_context().add_class("desktop")
    top_bar.set_show_start_title_buttons(False)
    top_bar.set_show_end_title_buttons(True)
    top_bar.set_title_widget(Gtk.Box())
    top_bar.set_valign(Gtk.Align.START)
    top_bar.set_halign(Gtk.Align.FILL)

    main_overlay.add_overlay(top_bar)

    return stack, picture, spinner, drawing_overlay, controls_overlay, main_overlay


def create_image_overlay(picture: Gtk.Picture, drawing_overlay: 'DrawingOverlay') -> Gtk.Overlay:
    overlay = Gtk.Overlay.new()
    overlay.set_child(picture)
    overlay.add_overlay(drawing_overlay)

    controls_overlay = ControlsOverlay()
    overlay.add_overlay(controls_overlay)

    return overlay, controls_overlay


def create_picture_widget() -> Gtk.Picture:
    picture = Gtk.Picture.new()
    picture.set_content_fit(Gtk.ContentFit.CONTAIN)
    picture.set_can_shrink(True)
    return picture

def create_drawing_overlay(picture: Gtk.Picture) -> 'DrawingOverlay':
    drawing_overlay = DrawingOverlay()
    drawing_overlay.set_visible(True)
    drawing_overlay.set_picture_reference(picture)
    return drawing_overlay

def create_spinner_widget() -> tuple[Gtk.Box, Adw.Spinner]:
    spinner = Adw.Spinner.new()
    spinner.set_size_request(48, 48)

    spinner_box = Gtk.Box(
        orientation=Gtk.Orientation.VERTICAL,
        spacing=0,
        halign=Gtk.Align.CENTER,
        valign=Gtk.Align.CENTER,
        margin_top=20,
        margin_bottom=20,
        margin_start=20,
        margin_end=20,
    )
    spinner_box.append(spinner)
    return spinner_box, spinner

def create_drop_target(stack: Gtk.Stack) -> None:
    drop_target = Gtk.DropTarget.new(Gio.File, Gdk.DragAction.COPY)
    drop_target.set_preload(True)

    def on_file_dropped(_target: Gtk.DropTarget, value: Gio.File, _x: int, _y: int) -> None:
        uri = value.get_uri()
        if uri:
            app = Gio.Application.get_default()
            action = app.lookup_action("load-drop") if app else None
            if action:
                action.activate(GLib.Variant('s', uri))

    drop_target.connect("drop", on_file_dropped)
    stack.add_controller(drop_target)

def create_image_options_group(
    on_padding_changed: Callable[[Adw.SpinRow], None],
    on_aspect_ratio_changed: Callable[[Gtk.Entry], None],
    on_corner_radius_changed: Callable[[Adw.SpinRow], None],
    on_shadow_strength_changed: Callable[[Gtk.Scale], None]
) -> tuple[Adw.PreferencesGroup, Adw.SpinRow, Gtk.Entry]:
    padding_group = Adw.PreferencesGroup(title=_("Image Options"))

    padding_adjustment = Gtk.Adjustment(value=5, lower=-25, upper=75, step_increment=5, page_increment=5)
    padding_row = Adw.SpinRow(title=_("Padding"), numeric=True, adjustment=padding_adjustment)
    padding_row.connect("output", on_padding_changed)
    padding_group.add(padding_row)

    corner_radius_adjustment = Gtk.Adjustment(value=2, lower=0, upper=50, step_increment=1, page_increment=1)
    corner_radius_row = Adw.SpinRow(title=_("Corner Radius"), numeric=True, adjustment=corner_radius_adjustment)
    corner_radius_row.connect("output", on_corner_radius_changed)
    padding_group.add(corner_radius_row)

    aspect_ratio_row = Adw.ActionRow(title=_("Aspect Ratio"))
    aspect_ratio_entry = Gtk.Entry(placeholder_text="16:9", valign=Gtk.Align.CENTER)
    aspect_ratio_entry.connect("changed", on_aspect_ratio_changed)
    aspect_ratio_row.add_suffix(aspect_ratio_entry)
    padding_group.add(aspect_ratio_row)

    shadow_strength_row = Adw.ActionRow(title=_("Shadow"))
    shadow_strength_scale = Gtk.Scale.new_with_range(
        orientation=Gtk.Orientation.HORIZONTAL,
        min=0,
        max=10,
        step=1
    )
    shadow_strength_scale.set_valign(Gtk.Align.CENTER)
    shadow_strength_scale.set_hexpand(True)
    shadow_strength_scale.set_draw_value(True)
    shadow_strength_scale.set_value_pos(Gtk.PositionType.RIGHT)
    shadow_strength_scale.connect("value-changed", on_shadow_strength_changed)
    shadow_strength_row.add_suffix(shadow_strength_scale)
    shadow_strength_row.set_activatable_widget(shadow_strength_scale)
    padding_group.add(shadow_strength_row)

    return padding_group, padding_row, aspect_ratio_entry

def create_file_info_group() -> tuple[Adw.PreferencesGroup, Adw.ActionRow, Adw.ActionRow, Adw.ActionRow]:
    file_info_group = Adw.PreferencesGroup(title=_("Current File"))

    filename_row = Adw.ActionRow(title=_("Name"), subtitle=_("No file loaded"))
    location_row = Adw.ActionRow(title=_("Location"), subtitle=_("No file loaded"))
    processed_size_row = Adw.ActionRow(title=_("Modified image size"), subtitle=_("N/A"))

    file_info_group.add(filename_row)
    file_info_group.add(location_row)
    file_info_group.add(processed_size_row)

    return file_info_group, filename_row, location_row, processed_size_row



def create_sidebar_ui(
    background_selector_widget: Gtk.Widget,
    on_padding_changed: Callable[[Adw.SpinRow], None],
    on_corner_radius_changed: Callable[[Adw.SpinRow], None],
    on_aspect_ratio_changed: Callable[[Gtk.Entry], None],
    on_shadow_strength_changed: Callable[[Gtk.Scale], None],
) -> dict[str, Gtk.Widget | Adw.ActionRow | Adw.SpinRow | Gtk.Entry]:
    toolbar_view = Adw.ToolbarView()
    header_bar = HeaderBar()
    toolbar_view.add_top_bar(header_bar)

    settings_scroll = Gtk.ScrolledWindow(vexpand=True)
    controls_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=20,
                           margin_start=16, margin_end=16, margin_top=16, margin_bottom=16)

    controls_box.append(DrawingToolsGroup())
    controls_box.append(background_selector_widget)

    # Add grouped UI elements
    padding_group, padding_row, aspect_ratio_entry = create_image_options_group(
        on_padding_changed, on_aspect_ratio_changed, on_corner_radius_changed, on_shadow_strength_changed)
    controls_box.append(padding_group)

    file_info_group, filename_row, location_row, processed_size_row = create_file_info_group()
    controls_box.append(file_info_group)

    settings_scroll.set_child(controls_box)
    toolbar_view.set_content(settings_scroll)

    bottom_bar = create_bottom_bar()
    toolbar_view.add_bottom_bar(bottom_bar)

    return {
        'sidebar': toolbar_view,
        'header_bar': header_bar,
        'bottom_bar': bottom_bar,
        'filename_row': filename_row,
        'location_row': location_row,
        'processed_size_row': processed_size_row,
        'padding_row': padding_row,
        'aspect_ratio_entry': aspect_ratio_entry,
    }

def create_bottom_bar() -> Adw.HeaderBar:
    bottom_bar = Adw.HeaderBar()
    bottom_bar.add_css_class("flat")
    bottom_bar.set_show_start_title_buttons(False)
    bottom_bar.set_show_end_title_buttons(False)

    action_buttons_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL,
    spacing=15, margin_top=5, margin_bottom=5)

    save_btn = Gtk.Button()
    save_btn.set_icon_name("document-save-symbolic")
    save_btn.set_tooltip_text(_("Save Image"))
    save_btn.set_action_name("app.save")
    save_btn.set_sensitive(False)
    save_btn.add_css_class("suggested-action")
    save_btn.add_css_class("pill")

    copy_btn = Gtk.Button()
    copy_btn.set_icon_name("edit-copy-symbolic")
    copy_btn.set_tooltip_text(_("Copy to Clipboard"))
    copy_btn.set_action_name("app.copy")
    copy_btn.set_sensitive(False)
    copy_btn.add_css_class("raised")
    copy_btn.add_css_class("pill")

    action_buttons_box.append(save_btn)
    action_buttons_box.append(copy_btn)
    bottom_bar.set_title_widget(action_buttons_box)

    return bottom_bar


def create_about_dialog(version: str) -> Adw.AboutDialog:
    about = Adw.AboutDialog(
        application_name="Gradia",
        version=version,
        comments=_("Make your images ready for the world"),
        website="https://github.com/AlexanderVanhee/Gradia",
        issue_url="https://github.com/AlexanderVanhee/Gradia/issues",
        developer_name="Alexander Vanhee",
        developers=[
            "Alexander Vanhee https://github.com/AlexanderVanhee",
            "tfuxu https://github.com/tfuxu",
        ],
        designers=[
            "drpetrikov https://github.com/drpetrikov "
        ],
        application_icon="be.alexandervanhee.gradia",
        # Translators: This is a place to put your credits (formats: "Name https://example.com" or "Name <email@example.com>", no quotes) and is not meant to be translated literally.
        translator_credits=_("translator-credits"),
        copyright="Copyright © 2025 Alexander Vanhee",
        license_type=Gtk.License.GPL_3_0
    )

    return about

def create_shortcuts_dialog(parent: Optional[Gtk.Window] = None) -> Gtk.ShortcutsWindow:
    SHORTCUT_GROUPS = [
        {
            "title": _("File Actions"),
            "shortcuts": [
                (_("Open File"), "<Ctrl>O"),
                (_("Save to File"), "<Ctrl>S"),
                (_("Copy Image to Clipboard"), "<Ctrl>C"),
                (_("Paste From Clipboard"), "<Ctrl>V"),
            ]
        },
        {
            "title": _("Annotations"),
            "shortcuts": [
                (_("Undo"), "<Ctrl>Z"),
                (_("Redo"), "<Ctrl><Shift>Z"),
                (_("Remove Selected"), "Delete")
            ]
        },
        {
            "title": _("General"),
            "shortcuts": [
                (_("Keyboard Shortcuts"), "<Ctrl>question"),
            ]
        }
    ]

    dialog = Gtk.ShortcutsWindow(transient_for=parent, modal=True)
    section = Gtk.ShortcutsSection()

    for group_data in SHORTCUT_GROUPS:
        group = Gtk.ShortcutsGroup(title=group_data["title"], visible=True)
        for title, accel in group_data["shortcuts"]:
            group.add_shortcut(Gtk.ShortcutsShortcut(
                title=title,
                accelerator=accel
            ))
        section.add_group(group)

    dialog.add_section(section)
    dialog.connect("close-request", lambda dialog: dialog.destroy())

    return dialog
