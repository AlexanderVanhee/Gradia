# Copyright (C) 2026 Alexander Vanhee
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

from gi.repository import Adw, Gtk

from gradia.backend.ocr import OCR
from gradia.ui.dialog.ocr_dialog import OCRDialog
from gradia.ui.preferences.ocr_model_page import OCRModelPage


def present_ocr_dialog(
    image,
    parent: Optional[Gtk.Widget] = None,
    on_dialog_shown: Optional[Callable[[OCRDialog], None]] = None,
    on_cancelled: Optional[Callable[[], None]] = None,
) -> None:
    def show():
        dialog = OCRDialog(image)
        dialog.present(parent)
        if on_dialog_shown is not None:
            on_dialog_shown(dialog)

    if len(OCR(parent).get_installed_models()) == 0:
        prefs = Adw.PreferencesDialog(content_width=600, content_height=500)
        prefs.set_title(_("OCR Language Models"))
        prefs.push_subpage(OCRModelPage(preferences_dialog=prefs, can_pop=False))

        def on_prefs_closed(*_):
            if len(OCR(parent).get_installed_models()) == 0:
                if on_cancelled is not None:
                    on_cancelled()
            else:
                show()

        prefs.connect("closed", on_prefs_closed)
        prefs.present(parent)
        return

    show()
