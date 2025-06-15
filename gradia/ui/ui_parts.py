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

from typing import Optional
from gi.repository import Gtk, Gio, Adw, Gdk, GLib

from gradia.overlay.drawing_overlay import DrawingOverlay
from gradia.overlay.transparency_overlay import TransparencyBackground
from gradia.constants import rootdir  # pyright: ignore


@Gtk.Template(resource_path=f"{rootdir}/ui/controls_overlay.ui")
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
                (_("Settings"), "<Ctrl>comma"),
                (_("Toggle Utility Pane"), "F9"),
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
