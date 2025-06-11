# Copyright (C) 2022 Gradience Team
# Copyright 2023-2025, tfuxu <https://github.com/tfuxu>
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
import logging
import traceback
from gradia.constants import build_type

class Logger(logging.getLoggerClass()):
    """
    This is a wrapper of `logging` module. It provides
    custom formatting for log messages.

    Attributes
    ----------
    issue_footer_levels : list, optional
        Custom list of levels on which to show issue footer.
        [Allowed values: warning, error, traceback_error, critical]
    formatter : str, optional
        Custom formatter for the logger.
    """

    log_colors = {
        "debug": 32,
        "info": 36,
        "warning": 33,
        "error": 31,
        "critical": 41
    }

    log_format = {
        'fmt': '%(message)s'
    }

    issue_footer = "If you are reporting an issue, please copy the logs printed above to the issue body."

    issue_footer_levels = [
        "error",
        "traceback_error",
        "critical"
    ]

    def __set_traceback_info(self, exception: BaseException | None = None) -> str:
        if not exception:
            exception = sys.exc_info()[1]
        traceback = self.get_traceback(exception)

        message_head = "\n\t\033[1mTraceback:\033[0m"
        message_body = f"\n\033[90m{traceback}\033[0m"
        message_body = message_body.replace("\n", "\n\t\t")

        return message_head + message_body

    def __set_exception_info(self, exception: BaseException | None = None) -> str:
        if not exception:
            exception = sys.exc_info()[1]

        message_head = "\n\t\033[1mException:\033[0m"
        message_body = f"\n{exception}"
        message_body = message_body.replace("\n", "\n\t\t")

        return message_head + message_body

    def __set_level_color(self, level: str, message: str) -> str:
        color_id = self.log_colors[level]

        return f"[\033[1;{color_id}m{level.upper()}\033[0m] {message}"

    def __init__(self, issue_footer_levels: list | None = None, fmt: str | None = None):
        """
        The constructor for Logger class.
        """

        super().__init__(name="Gradia")

        if issue_footer_levels:
            self.issue_footer_levels = issue_footer_levels

        formatter = logging.Formatter(self.log_format["fmt"])
        if fmt:
            formatter = logging.Formatter(fmt)

        if build_type == "debug":
            self.root.setLevel(logging.DEBUG)
        else:
            self.root.setLevel(logging.INFO)

        self.root.handlers = []

        handler = logging.StreamHandler()
        handler.setFormatter(formatter)
        self.root.addHandler(handler)

    def debug(self, message: str, *args, **kwargs) -> None:
        self.root.debug(self.__set_level_color("debug", str(message)))

    def info(self, message: str, *args, **kwargs) -> None:
        self.root.info(self.__set_level_color("info", str(message)))

    def warning(self, message: str, exception: BaseException | None = None,
                    show_exception: bool = False, show_traceback: bool = False, *args, **kwargs) -> None:
        if show_exception:
            message += self.__set_exception_info(exception)
        if show_traceback:
            message += self.__set_traceback_info(exception)

        self.root.warning(self.__set_level_color("warning", str(message)))
        if "warning" in self.issue_footer_levels:
            self.print_issue_footer()

    def error(self, message: str, exception: BaseException | None = None,
                show_exception: bool = False, show_traceback: bool = False, *args, **kwargs) -> None:
        if show_exception:
            message += self.__set_exception_info(exception)
        if show_traceback:
            message += self.__set_traceback_info(exception)

        self.root.error(self.__set_level_color("error", str(message)))
        if "error" in self.issue_footer_levels:
            self.print_issue_footer()

    def traceback_error(self, message: str, exception: BaseException | None = None,
                            show_exception: bool = False) -> None:
        if show_exception:
            message += self.__set_exception_info(exception)
        message += self.__set_traceback_info(exception)

        self.root.error(self.__set_level_color("error", str(message)))
        if "traceback_error" in self.issue_footer_levels:
            self.print_issue_footer()

    def critical(self, message: str, exception: BaseException | None = None,
                    show_exception: bool = False, show_traceback: bool = True, *args, **kwargs) -> None:
        if show_exception:
            message += self.__set_exception_info(exception)
        if show_traceback:
            message += self.__set_traceback_info(exception)

        self.root.critical(self.__set_level_color("critical", str(message)))
        if "critical" in self.issue_footer_levels:
            self.print_issue_footer()

    def set_silent(self) -> None:
        self.root.handlers = []

    def print_issue_footer(self) -> None:
        self.root.info(self.__set_level_color("info", self.issue_footer))

    def get_traceback(self, exception: BaseException | None) -> str | None:
        if not exception:
            return

        traceback_list = traceback.format_exception(exception)
        exception_tb = "".join(traceback_list)

        return exception_tb


"""
Use for testing only.
How to execute: python -m gradia.backend.logger
"""
# pylint: disable=W0719,W0718,W0707
if __name__ == "__main__":
    logging = Logger()

    logging.info("This is an information.")
    logging.debug("This is a debug message.")

    try:
        raise ArithmeticError("Arithmetic Error")
    except Exception:
        try:
            raise Exception("General Exception")
        except Exception as e:
            logging.traceback_error("This is an test error.", exception=e, show_exception=True)

            print(f"Retrieved traceback: {logging.get_traceback(e)}")
