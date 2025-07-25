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

from gi.repository import Gtk, Adw, GLib, GObject
from gradia.constants import rootdir  # pyright: ignore
from gradia.backend.settings import Settings


@Gtk.Template(resource_path=f"{rootdir}/ui/ocr_page.ui")
class OCRDownloadPage(Adw.NavigationPage):
    __gtype_name__ = 'GradiaOCRDownloadPage'

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.settings = Settings()
        self._setup_widgets()

    def _setup_widgets(self):
        pass
