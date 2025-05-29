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
import sys
import os
import tempfile
import shutil

from collections.abc import Sequence

from gi.repository import Adw, Gio

from gradia.ui.window import GradientWindow


class GradiaApp(Adw.Application):
    __gtype_name__ = "GradiaApp"

    def __init__(self, version: str):
        super().__init__(
            application_id="be.alexandervanhee.gradia",
            flags=Gio.ApplicationFlags.HANDLES_OPEN
        )
        self.temp_dir = tempfile.mkdtemp()
        self.version = version
        self.file_to_open = None

    def do_activate(self):
        self.ui = GradientWindow(self.temp_dir, version=self.version, application=self)
        self.ui.build_ui()
        self.ui.show()

    def do_open(self, files: Sequence[Gio.File], hint: str):
        self.activate()

    def do_shutdown(self):
        try:
            if hasattr(self, 'temp_dir') and os.path.exists(self.temp_dir):
                shutil.rmtree(self.temp_dir)
        except Exception as e:
            print(f"Warning: Failed to clean up temporary directory: {e}")
        finally:
            Gio.Application.do_shutdown(self)


def main(version: str):
    try:
        app = GradiaApp(version=version)
        return app.run(sys.argv)
    except Exception as e:
        print('Application closed with an exception:', e)
        return 1
