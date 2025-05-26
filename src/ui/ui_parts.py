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

from gi.repository import Gtk, Gio, Adw, Gdk

def create_header_bar(save_btn_ref, on_open_clicked, on_save_clicked, on_copy_from_clicked, on_copy_to_clicked):
    header_bar = Adw.HeaderBar()

    # Open button
    open_btn = Gtk.Button.new_from_icon_name("document-open-symbolic")
    open_btn.get_style_context().add_class("flat")
    open_btn.set_tooltip_text(_("Open Image"))
    open_btn.connect("clicked", on_open_clicked)
    header_bar.pack_start(open_btn)

    # Copy from clipboard button
    copy_btn = Gtk.Button.new_from_icon_name("clipboard-symbolic")
    copy_btn.get_style_context().add_class("flat")
    copy_btn.set_tooltip_text(_("Paste from Clipboard"))
    copy_btn.connect("clicked", on_copy_from_clicked)
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

    # Save button with icon and label inside a box
    button_content = Adw.ButtonContent(
        icon_name="document-save-symbolic",
        # Translators: The prefixed underscore is used to indicate a mnemonic. Do NOT remove it.
        label=_("_Save Image"),
        use_underline=True
    )

    save_btn = Gtk.Button(child=button_content)
    save_btn.get_style_context().add_class("suggested-action")
    save_btn.connect("clicked", on_save_clicked)
    save_btn.set_sensitive(False)
    save_btn_ref[0] = save_btn

    # Copy to clipboard button (right)
    copy_right_btn = Gtk.Button.new_from_icon_name("edit-copy-symbolic")
    copy_right_btn.get_style_context().add_class("suggested-action")
    copy_right_btn.set_tooltip_text(_("Copy to Clipboard"))
    copy_right_btn.set_sensitive(False)
    copy_right_btn.connect("clicked", on_copy_to_clicked)
    save_btn_ref[1] = copy_right_btn

    # Group the two buttons in a linked box
    right_buttons_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=0)
    right_buttons_box.get_style_context().add_class("linked")
    right_buttons_box.append(save_btn)
    right_buttons_box.append(copy_right_btn)

    header_bar.pack_end(right_buttons_box)

    return header_bar

def create_image_stack(on_file_dropped, on_open_clicked):
    stack = Gtk.Stack.new()
    stack.set_vexpand(True)
    stack.set_hexpand(True)

    # Picture widget
    picture = Gtk.Picture.new()
    picture.set_content_fit(Gtk.ContentFit.CONTAIN)
    picture.set_can_shrink(True)
    stack.add_named(picture, "image")

    # Loading spinner inside centered box with margins
    spinner = Gtk.Spinner.new()
    spinner.set_vexpand(False)
    spinner.set_hexpand(False)

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
    stack.add_named(spinner_box, "loading")

    # Drop target for drag & drop
    drop_target = Gtk.DropTarget.new(Gio.File, Gdk.DragAction.COPY)
    drop_target.set_preload(True)
    drop_target.connect("drop", on_file_dropped)
    stack.add_controller(drop_target)

    # Status page with button child
    # Translators: The prefixed underscore is used to indicate a mnemonic. Do NOT remove it.
    open_status_btn = Gtk.Button.new_with_label(_("_Open Image…"))
    open_status_btn.set_use_underline(True)
    open_status_btn.set_halign(Gtk.Align.CENTER)
    style_context = open_status_btn.get_style_context()
    style_context.add_class("suggested-action")
    style_context.add_class("pill")
    style_context.add_class("text-button")
    open_status_btn.connect("clicked", on_open_clicked)

    status_page = Adw.StatusPage.new()
    status_page.set_icon_name("image-x-generic-symbolic")
    status_page.set_title(_("No Image Loaded"))
    status_page.set_description(_("Drag and drop one here"))
    status_page.set_child(open_status_btn)

    stack.add_named(status_page, "empty")
    stack.set_visible_child_name("empty")

    return stack, picture, spinner

def create_image_options_group(on_padding_changed, on_aspect_ratio_changed, on_corner_radius_changed, on_shadow_strength_changed):
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

    shadow_strength_row = Adw.ActionRow(title="Shadow")
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

def create_file_info_group():
    file_info_group = Adw.PreferencesGroup(title="Current File")

    filename_row = Adw.ActionRow(title=_("Name"), subtitle=_("No file loaded"))
    location_row = Adw.ActionRow(title=_("Location"), subtitle=_("No file loaded"))
    processed_size_row = Adw.ActionRow(title=_("Modified image size"), subtitle="N/A")

    file_info_group.add(filename_row)
    file_info_group.add(location_row)
    file_info_group.add(processed_size_row)

    return file_info_group, filename_row, location_row, processed_size_row


def create_sidebar_ui(gradient_selector_widget, on_padding_changed, on_corner_radius_changed, text_selector_widget, on_aspect_ratio_changed, on_shadow_strength_changed):

    sidebar_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
    settings_scroll = Gtk.ScrolledWindow(vexpand=True)
    controls_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=20,
                           margin_start=16, margin_end=16, margin_top=16, margin_bottom=16)

    controls_box.append(gradient_selector_widget)
    # Add grouped UI elements
    padding_group, padding_row, aspect_ratio_entry = create_image_options_group(
        on_padding_changed, on_aspect_ratio_changed, on_corner_radius_changed, on_shadow_strength_changed)
    controls_box.append(padding_group)

    controls_box.append(text_selector_widget)

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

def create_about_dialog(version):
    about = Adw.AboutDialog(
        application_name="Gradia",
        version=version,
        comments=_("Make your images ready for the world"),
        website="https://github.com/AlexanderVanhee/Gradia",
        developer_name="Alexander Vanhee",
        application_icon="be.alexandervanhee.gradia"
    )
    about.set_developers(["Alexander Vanhee"])
    about.set_license_type(Gtk.License.GPL_3_0)

    return about

def create_shortcuts_dialog(parent=None):
    SHORTCUT_GROUPS = [
        {
            "title": _("File Actions"),
            "shortcuts": [
                (_("Open file"), "<Ctrl>O"),
                (_("Save to file"), "<Ctrl>S"),
                (_("Copy modified image to clipboard"), "<Ctrl>C"),
                (_("Paste from clipboard"), "<Ctrl>V"),
            ]
        },
        {
            "title": _("General"),
            "shortcuts": [
                (_("Keyboard shortcuts"), "<Ctrl>question"),
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
