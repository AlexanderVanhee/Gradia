# Copyright (C) 2025 Alexander Vanhee
#
# SPDX-License-Identifier: GPL-3.0-or-later

from gi.repository import Gtk, Adw, GLib, GObject
from gradia.backend.ocr import OCR
from gradia.constants import rootdir
import threading

@Gtk.Template(resource_path=f"{rootdir}/ui/ocr_dialog.ui")
class OCRDialog(Adw.Dialog):
    __gtype_name__ = 'OCRDialog'

    ocr_text_view = Gtk.Template.Child()
    ocr_stack = Gtk.Template.Child()
    ocr_spinner = Gtk.Template.Child()
    copy_ocr_button = Gtk.Template.Child()

    def __init__(self, image=None, **kwargs):
        super().__init__(**kwargs)
        self.image = image
        self.ocr = OCR()
        self._start_ocr()
        self.ocr_text_view.remove_css_class("view")

    def _start_ocr(self):
        # show the loading page
        self.ocr_stack.set_visible_child_name("loading")
        threading.Thread(target=self._run_ocr, daemon=True).start()

    def _run_ocr(self):
        try:
            text = self.ocr.extract_text(self.image)
        except Exception as e:
            text = f"OCR failed:\n{e}"

        GLib.idle_add(self._display_text, text)

    def _display_text(self, text):
        buffer = self.ocr_text_view.get_buffer()
        buffer.set_text(text)
        self.ocr_stack.set_visible_child_name("text")
        return False  # stop idle_add callback



