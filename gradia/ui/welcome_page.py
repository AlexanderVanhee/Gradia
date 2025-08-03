# Copyright (C) 2025 tfuxu, Alexander Vanhee
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

from gi.repository import Adw, GLib, Gdk, Gio, Gtk

from gradia.constants import rootdir  # pyright: ignore
from gradia.ui.recent_picker import RecentPicker
from gradia.overlay.drop_overlay import DropOverlay

@Gtk.Template(resource_path=f"{rootdir}/ui/welcome_page.ui")
class WelcomePage(Adw.Bin):
    __gtype_name__ = "GradiaWelcomePage"

    recent_picker: RecentPicker = Gtk.Template.Child()
    drop_overlay: DropOverlay = Gtk.Template.Child()

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)

        self.recent_picker.callback = self._on_recent_image_click
        self._setup_drag_and_drop()

    """
    Setup Methods
    """

    def _setup_drag_and_drop(self) -> None:
        drop_target = Gtk.DropTarget.new(Gio.File, Gdk.DragAction.COPY)
        drop_target.set_preload(True)

        drop_target.connect("drop", self._on_file_dropped)
        self.drop_overlay.drop_target = drop_target

    """
    Callbacks
    """

    def _on_file_dropped(self, _target: Gtk.DropTarget, value: Gio.File, _x: int, _y: int) -> bool:
        uri = value.get_uri()
        if uri:
            window = self.get_root()
            action = window.lookup_action("load-drop") if window else None
            if action:
                action.activate(GLib.Variant('s', uri))
                return True
        return False

    def refresh_recent_picker(self) -> None:
        self.recent_picker.refresh()

    """
    Callbacks
    """
    def _on_recent_image_click(self, path: str, gradient_index: int) -> None:
        window = self.get_root()
        if window:
            action = window.lookup_action("open-path")
            if action:
                param = GLib.Variant('s', path)
                action.activate(param)

