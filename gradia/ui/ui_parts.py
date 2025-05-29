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

from gradia.ui.drawing_actions import DrawingMode
from gradia.ui.drawing_overlay import DrawingOverlay

def create_header_bar() -> Adw.HeaderBar:
    header_bar = Adw.HeaderBar()

    # Open button
    open_btn = Gtk.Button.new_from_icon_name("document-open-symbolic")
    open_btn.get_style_context().add_class("flat")
    open_btn.set_tooltip_text(_("Open Image"))
    open_btn.set_action_name("app.open")
    header_bar.pack_start(open_btn)

    # Copy from clipboard button
    copy_btn = Gtk.Button.new_from_icon_name("clipboard-symbolic")
    copy_btn.get_style_context().add_class("flat")
    copy_btn.set_tooltip_text(_("Paste from Clipboard"))
    copy_btn.set_action_name("app.paste")
    header_bar.pack_start(copy_btn)

    # About menu button with popover menu
    about_menu_btn = Gtk.MenuButton(icon_name="open-menu-symbolic")
    about_menu_btn.get_style_context().add_class("flat")
    about_menu_btn.set_tooltip_text(_("Main Menu"))
    about_menu_btn.set_primary(True)

    menu = Gio.Menu()
    menu.append(_("Keyboard Shortcuts"), "app.shortcuts")
    menu.append(_("About Gradia"), "app.about")

    popover = Gtk.PopoverMenu()
    popover.set_menu_model(menu)
    about_menu_btn.set_popover(popover)
    header_bar.pack_end(about_menu_btn)

    # Translators: The prefixed underscore is used to indicate a mnemonic. Do NOT remove it.
    label = Gtk.Label(label=_("_Save Image"), use_underline=True)
    save_btn = Gtk.Button(child=label)
    save_btn.get_style_context().add_class("suggested-action")
    save_btn.set_action_name("app.save")
    save_btn.set_sensitive(False)

    # Copy to clipboard button (right)
    copy_right_btn = Gtk.Button.new_from_icon_name("edit-copy-symbolic")
    copy_right_btn.get_style_context().add_class("suggested-action")
    copy_right_btn.set_tooltip_text(_("Copy to Clipboard"))
    copy_right_btn.set_sensitive(False)
    copy_right_btn.set_action_name("app.copy")

    # Group the two buttons in a linked box
    right_buttons_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=0)
    right_buttons_box.get_style_context().add_class("linked")
    right_buttons_box.append(save_btn)
    right_buttons_box.append(copy_right_btn)
    header_bar.pack_end(right_buttons_box)

    return header_bar


def create_image_stack() -> tuple[Gtk.Stack, Gtk.Picture, Adw.Spinner, 'DrawingOverlay']:
    stack = Gtk.Stack.new()
    stack.set_vexpand(True)
    stack.set_hexpand(True)

    picture = create_picture_widget()
    drawing_overlay = create_drawing_overlay(picture)
    overlay = create_image_overlay(picture, drawing_overlay)

    stack.add_named(overlay, "image")

    spinner_box, spinner = create_spinner_widget()
    stack.add_named(spinner_box, "loading")

    status_page = create_status_page()
    stack.add_named(status_page, "empty")

    stack.set_visible_child_name("empty")

    create_drop_target(stack)

    return stack, picture, spinner, drawing_overlay

def create_image_overlay(picture: Gtk.Picture, drawing_overlay: 'DrawingOverlay') -> Gtk.Overlay:
    overlay = Gtk.Overlay.new()
    overlay.set_child(picture)
    overlay.add_overlay(drawing_overlay)

    controls_overlay = create_controls_overlay()
    overlay.add_overlay(controls_overlay)

    return overlay

def create_controls_overlay() -> Gtk.Box:
    undo_btn = Gtk.Button.new_from_icon_name("edit-undo-symbolic")
    redo_btn = Gtk.Button.new_from_icon_name("edit-redo-symbolic")
    reset_btn = Gtk.Button.new_from_icon_name("user-trash-symbolic")

    for btn in (undo_btn, redo_btn, reset_btn):
        btn.get_style_context().add_class("osd")
        btn.get_style_context().add_class("circular")


    button_box = Gtk.Box(
        orientation=Gtk.Orientation.HORIZONTAL,
        spacing=6,
        halign=Gtk.Align.END,
        valign=Gtk.Align.END,
        margin_end=12,
        margin_bottom=12,
    )

    undo_btn.set_action_name("app.undo")
    redo_btn.set_action_name("app.redo")
    reset_btn.set_action_name("app.clear")

    button_box.append(undo_btn)
    button_box.append(redo_btn)
    button_box.append(reset_btn)

    return button_box


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

def create_status_page() -> Adw.StatusPage:
    open_status_btn = Gtk.Button.new_with_label(_("_Open Image…"))
    open_status_btn.set_use_underline(True)
    open_status_btn.set_halign(Gtk.Align.CENTER)

    style_context = open_status_btn.get_style_context()
    style_context.add_class("pill")
    style_context.add_class("text-button")
    style_context.add_class("suggested-action")

    open_status_btn.set_action_name("app.open")

    status_page = Adw.StatusPage.new()
    status_page.set_icon_name("image-x-generic-symbolic")
    status_page.set_title(_("No Image Loaded"))
    status_page.set_description(_("Drag and drop one here"))
    status_page.set_child(open_status_btn)

    return status_page

def create_drop_target(stack: Gtk.Stack) -> None:
    drop_target = Gtk.DropTarget.new(Gio.File, Gdk.DragAction.COPY)
    drop_target.set_preload(True)

    def on_file_dropped(_target: Gtk.DropTarget, *value: Gio.File, _x: int, _y: int) -> None:
        app = Gio.Application.get_default()
        action = app.lookup_action("load-drop") if app else None
        if action:
            action.activate(None)

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

def create_drawing_tools_group() -> Adw.PreferencesGroup:
    tools_group = Adw.PreferencesGroup(title=_("Annotation Tools"))

    # Drawing mode buttons
    tools_row = Adw.ActionRow()
    tools_grid = Gtk.Grid(margin_start=6, margin_end=6, margin_top=6, margin_bottom=6)
    tools_grid.set_row_spacing(6)
    tools_grid.set_column_spacing(6)
    tools_grid.set_halign(Gtk.Align.CENTER)
    tools_grid.set_valign(Gtk.Align.CENTER)

    tools_data = [
        (DrawingMode.SELECT, "pointer-primary-click-symbolic", 0, 0),
        (DrawingMode.PEN, "edit-symbolic", 1, 0),
        (DrawingMode.TEXT, "text-insert2-symbolic", 2, 0),
        (DrawingMode.LINE, "draw-line-symbolic", 3, 0),
        (DrawingMode.ARROW, "arrow1-top-right-symbolic", 4, 0),
        (DrawingMode.SQUARE, "box-small-outline-symbolic", 0, 1),
        (DrawingMode.CIRCLE, "circle-outline-thick-symbolic", 1, 1),
    ]

    fill_sensitive_modes = {DrawingMode.SQUARE, DrawingMode.CIRCLE}
    tool_buttons = {}

    # Fill color row with reset button
    fill_row = Adw.ActionRow(title=_("Fill Color"))
    fill_row.set_sensitive(False)

    reset_fill_button = Gtk.Button(icon_name="edit-clear-symbolic")
    reset_fill_button.get_style_context().add_class("flat")
    reset_fill_button.set_tooltip_text(_("Reset Fill"))
    reset_fill_button.set_valign(Gtk.Align.CENTER)

    fill_color_button = Gtk.ColorButton()
    fill_color_button.set_valign(Gtk.Align.CENTER)
    fill_color_button.set_rgba(Gdk.RGBA(red=0, green=0, blue=0, alpha=0))


    def on_button_toggled(button: Gtk.ToggleButton, drawing_mode):
        if button.get_active():
            for mode_key, btn in tool_buttons.items():
                if mode_key != drawing_mode and btn.get_active():
                    btn.set_active(False)

            fill_row.set_sensitive(drawing_mode in fill_sensitive_modes)
            app = Gio.Application.get_default()
            if app:
                action = app.lookup_action("draw-mode")
                if action:
                    variant = GLib.Variant('s', drawing_mode.value)
                    action.activate(variant)
        else:
            any_active = any(
                btn.get_active() for mode_key, btn in tool_buttons.items() if mode_key != drawing_mode
            )
            if not any_active:
                button.set_active(True)

    for drawing_mode, icon_name, col, row in tools_data:
        button = Gtk.ToggleButton()
        button.set_icon_name(icon_name)
        button.set_tooltip_text(_(drawing_mode.value.capitalize()))
        button.get_style_context().add_class("flat")
        button.get_style_context().add_class("circular")
        button.set_size_request(40, 40)
        button.connect("toggled", on_button_toggled, drawing_mode)
        tools_grid.attach(button, col, row, 1, 1)
        tool_buttons[drawing_mode] = button

    # Default tool is PEN
    if DrawingMode.PEN in tool_buttons:
        tool_buttons[DrawingMode.PEN].set_active(True)

    tools_row.set_child(tools_grid)
    tools_group.add(tools_row)

    # Stroke color row
    stroke_color_row = Adw.ActionRow(title=_("Stroke Color"))
    stroke_color_button = Gtk.ColorButton()
    stroke_color_button.set_valign(Gtk.Align.CENTER)
    stroke_color_button.set_rgba(Gdk.RGBA(red=1, green=1, blue=1, alpha=1))
    stroke_color_row.add_suffix(stroke_color_button)
    tools_group.add(stroke_color_row)


    def on_reset_fill_clicked(_btn):
        fill_color_button.set_rgba(Gdk.RGBA(red=0, green=0, blue=0, alpha=0))
        fill_color_button.emit("color-set")

    reset_fill_button.connect("clicked", on_reset_fill_clicked)

    fill_row.add_suffix(reset_fill_button)
    fill_row.add_suffix(fill_color_button)
    tools_group.add(fill_row)

    # Color-set handlers
    def on_color_set(color_btn: Gtk.ColorButton):
        app = Gio.Application.get_default()
        if app:
            action = app.lookup_action("pen-color")
            if action:
                rgba = color_btn.get_rgba()
                color_str = f"{rgba.red:.3f},{rgba.green:.3f},{rgba.blue:.3f},{rgba.alpha:.3f}"
                variant = GLib.Variant('s', color_str)
                action.activate(variant)

    def on_fill_color_set(color_btn: Gtk.ColorButton):
        app = Gio.Application.get_default()
        if app:
            action = app.lookup_action("fill-color")
            if action:
                rgba = color_btn.get_rgba()
                color_str = f"{rgba.red:.3f},{rgba.green:.3f},{rgba.blue:.3f},{rgba.alpha:.3f}"
                variant = GLib.Variant('s', color_str)
                action.activate(variant)

    stroke_color_button.connect("color-set", on_color_set)
    fill_color_button.connect("color-set", on_fill_color_set)

    return tools_group

def create_sidebar_ui(
    gradient_selector_widget: Gtk.Widget,
    on_padding_changed: Callable[[Adw.SpinRow], None],
    on_corner_radius_changed: Callable[[Adw.SpinRow], None],
    on_aspect_ratio_changed: Callable[[Gtk.Entry], None],
    on_shadow_strength_changed: Callable[[Gtk.Scale], None],
) -> dict[str, Gtk.Widget | Adw.ActionRow | Adw.SpinRow | Gtk.Entry]:
    sidebar_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
    settings_scroll = Gtk.ScrolledWindow(vexpand=True)
    controls_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=20,
                           margin_start=16, margin_end=16, margin_top=16, margin_bottom=16)

    drawing_tools_group = create_drawing_tools_group()
    controls_box.append(drawing_tools_group)

    controls_box.append(gradient_selector_widget)
    # Add grouped UI elements
    padding_group, padding_row, aspect_ratio_entry = create_image_options_group(
        on_padding_changed, on_aspect_ratio_changed, on_corner_radius_changed, on_shadow_strength_changed)
    controls_box.append(padding_group)


    file_info_group, filename_row, location_row, processed_size_row = create_file_info_group()
    controls_box.append(file_info_group)

    settings_scroll.set_child(controls_box)
    sidebar_box.append(settings_scroll)

    return {
        'sidebar': sidebar_box,
        'filename_row': filename_row,
        'location_row': location_row,
        'processed_size_row': processed_size_row,
        'padding_row': padding_row,
        'aspect_ratio_entry': aspect_ratio_entry,
    }

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
