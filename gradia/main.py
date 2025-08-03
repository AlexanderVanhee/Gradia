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
from typing import Optional

from gi.repository import Adw, Gio, Xdp

from gradia.constants import app_id  # pyright: ignore
from gradia.ui.window import GradiaMainWindow
from gradia.backend.logger import Logger
from gradia.utils.std_image_loader import StdinImageLoader
logging = Logger()


class GradiaApp(Adw.Application):
    __gtype_name__ = "GradiaApp"

    def __init__(self, version: str):
        super().__init__(
            application_id=app_id,
            flags=Gio.ApplicationFlags.HANDLES_COMMAND_LINE | Gio.ApplicationFlags.HANDLES_OPEN
        )
        self.version = version
        self.temp_dirs: list[str] = []
        self._stdin_image_path: Optional[str] = None


        self.connect("shutdown", self.on_shutdown)

    def do_command_line(self, command_line: Gio.ApplicationCommandLine) -> int:
        args = command_line.get_arguments()[1:]
        logging.info(f"Command line arguments: {args}")

        if "--help" in args or "-h" in args:
            self._print_help()
            return 0

        files_to_open = []
        screenshot_file = None

        for arg in args:
            if arg.startswith("--screenshot-file="):
                screenshot_file = arg.split("=", 1)[1]
                logging.info(f"Screenshot file detected: {screenshot_file}")
            elif not arg.startswith("--"):
                try:
                    file = Gio.File.new_for_commandline_arg(arg)
                    path = file.get_path()
                    if path:
                        files_to_open.append(path)
                        logging.debug(f"File to open detected: {path}")
                    else:
                        logging.warning(f"Argument {arg} does not have a valid path.")
                except Exception as e:
                    logging.warning(f"Failed to parse file URI {arg}.", exception=e, show_exception=True)

        if files_to_open:
            for path in files_to_open:
                self._open_window(file_path=path)
        elif screenshot_file:
            self._open_window(start_screenshot=screenshot_file)
        else:
            self.activate()

        return 0

    def _print_help(self):
        file = Gio.File.new_for_uri("resource:///be/alexandervanhee/gradia/help.txt")
        stream = file.read(None)
        contents = stream.read_bytes(4096, None).get_data().decode("utf-8")
        print(contents)

    def do_open(self, files: Sequence[Gio.File], hint: str):
        logging.debug(f"do_open called with files: {[file.get_path() for file in files]} and hint: {hint}")
        for file in files:
            path = file.get_path()
            if path:
                self._open_window(path)

    def do_activate(self):
        logging.debug("do_activate called")

        stdin_path = self._stdin_image_path
        self._stdin_image_path = None

        if stdin_path:
            logging.debug(f"Opening window with stdin image path: {stdin_path}")
            self._open_window(stdin_path)
        else:
            self._open_window(None)

    def _open_window(self, file_path: Optional[str] = None, start_screenshot: Optional[str] = None):
        logging.info(f"Opening window with file_path={file_path}")
        temp_dir = tempfile.mkdtemp()
        logging.debug(f"Created temp directory: {temp_dir}")
        self.temp_dirs.append(temp_dir)

        window = GradiaMainWindow(
            temp_dir=temp_dir,
            version=self.version,
            application=self,
            file_path=file_path,
            start_screenshot=start_screenshot
        )
        window.show()

    def on_shutdown(self, application):
        logging.info("Application shutdown started, cleaning temp directories...")
        for temp_dir in self.temp_dirs:
            try:
                if os.path.exists(temp_dir):
                    shutil.rmtree(temp_dir)
                    logging.debug(f"Deleted temp dir: {temp_dir}")
            except Exception as e:
                logging.warning(f"Failed to clean up temp dir {temp_dir}.", exception=e, show_exception=True)
        logging.info("Cleanup complete.")

def main(version: str) -> int:
    try:
        logging.info("Application starting...")
        loader = StdinImageLoader()
        image_path = loader.read_from_stdin()

        app = GradiaApp(version=version)
        app._stdin_image_path = image_path

        return app.run(sys.argv)

    except Exception as e:
        logging.critical("Application closed with an exception.", exception=e, show_exception=True)
        return 1
