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

from gi.repository import Gtk, Adw, GLib, GObject, Gio
from gradia.backend.ocr import OCR
from gradia.constants import rootdir
from gradia.clipboard import copy_text_to_clipboard
import threading

@Gtk.Template(resource_path=f"{rootdir}/ui/ocr_dialog.ui")
class OCRDialog(Adw.Dialog):
    __gtype_name__ = 'OCRDialog'

    ocr_text_view = Gtk.Template.Child()
    ocr_stack = Gtk.Template.Child()
    ocr_spinner = Gtk.Template.Child()
    copy_ocr_button = Gtk.Template.Child()
    toast_overlay = Gtk.Template.Child()
    language_button = Gtk.Template.Child()

    def __init__(self, image=None, **kwargs):
        super().__init__(**kwargs)
        self.image = image
        self.ocr = OCR()
        self.primary_lang = "eng"
        self.secondary_lang = None
        self._setup_language_button()
        self._start_ocr()
        self.ocr_text_view.remove_css_class("view")

    def _setup_language_button(self):
        available_models = self.ocr.get_downloadable_models()
        installed_models = self.ocr.get_installed_models()
        current_model = self.ocr.get_current_model()

        menu = Gio.Menu()

        for model in available_models:
            if model.code in installed_models:
                menu.append(model.name, f"ocr.select_language::{model.code}")

        self.language_button.set_menu_model(menu)

        action_group = Gio.SimpleActionGroup()
        select_action = Gio.SimpleAction.new_stateful(
            "select_language",
            GLib.VariantType.new("s"),
            GLib.Variant.new_string(current_model)
        )
        select_action.connect("activate", self._on_language_selected)
        action_group.add_action(select_action)
        self.insert_action_group("ocr", action_group)

        for model in available_models:
            if model.code == current_model:
                self.language_button.set_label(model.name)
                self.primary_lang = current_model
                break

    def _on_language_selected(self, action, parameter):
        lang_code = parameter.get_string()
        action.set_state(parameter)

        available_models = self.ocr.get_downloadable_models()
        for model in available_models:
            if model.code == lang_code:
                self.language_button.set_label(model.name)
                break

        self.primary_lang = lang_code
        self._start_ocr()

    def _start_ocr(self):
        self.ocr_stack.set_visible_child_name("loading")
        threading.Thread(target=self._run_ocr, daemon=True).start()

    def _run_ocr(self):
        try:
            text = self.ocr.extract_text(self.image, self.primary_lang)
        except Exception as e:
            text = f"OCR failed:\n{e}"

        GLib.idle_add(self._display_text, text)

    def _display_text(self, text):
        buffer = self.ocr_text_view.get_buffer()
        buffer.set_text(text)

        if text.strip():
            self.ocr_stack.set_visible_child_name("text")
        else:
            self.ocr_stack.set_visible_child_name("no-text")

        return False

    @Gtk.Template.Callback()
    def _on_copy_ocr_clicked(self, button):
        buffer = self.ocr_text_view.get_buffer()
        start_iter = buffer.get_start_iter()
        end_iter = buffer.get_end_iter()
        text = buffer.get_text(start_iter, end_iter, False)

        if text.strip():
            copy_text_to_clipboard(text)
            toast = Adw.Toast.new(_("Copied!"))
            toast.set_timeout(1)
            self.toast_overlay.add_toast(toast)
