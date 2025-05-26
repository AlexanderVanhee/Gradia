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
import tempfile
import shutil
import locale


from gi.repository import Adw, Gio
from gradia.ui.window import GradientWindow

class GradiaApp(Adw.Application):
    def __init__(self, version=None):
        super().__init__(
            application_id="be.alexandervanhee.gradia",
            flags=Gio.ApplicationFlags.HANDLES_OPEN
        )
        self.temp_dir = tempfile.mkdtemp()
        self.version = version
        self.file_to_open = None

    def do_activate(self):
        self.ui = GradientWindow(self, self.temp_dir, version=self.version)
        self.ui.build_ui()
        self.ui.show()

    def do_open(self, files, n_files, hint):
        self.activate()

    def do_shutdown(self):
        shutil.rmtree(self.temp_dir)
        Adw.Application.do_shutdown(self)

def main(version=None):
    try:
        app = GradiaApp(version=version)
        return app.run(sys.argv)
    except Exception as e:
        print('Application closed with an exception:', e)
        return 1

