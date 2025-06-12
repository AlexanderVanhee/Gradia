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

from gi.repository import Gtk, Gio, Adw, GLib

from gradia.ui.recent_picker import RecentPicker
from gradia.constants import rootdir  # pyright: ignore

@Gtk.Template(resource_path=f"{rootdir}/ui/welcome_page.ui")
class WelcomePage(Adw.Bin):
    __gtype_name__ = "GradiaWelcomePage"

    recent_picker: RecentPicker = Gtk.Template.Child()

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)

        self.recent_picker.callback = self._on_recent_image_click

    """
    Callbacks
    """

    def _on_recent_image_click(self, path: str, gradient_index: int) -> None:
        app = Gio.Application.get_default()
        if app:
            action = app.lookup_action("open-path-with-gradient")
            if action:
                param = GLib.Variant('(si)', (path, gradient_index))
                action.activate(param)
