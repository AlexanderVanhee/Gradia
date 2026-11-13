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

import gi
from gi.repository import Gtk, Adw, GLib
from gradia.constants import rootdir
from gradia.backend.logger import Logger
from gradia.backend.ocr import OCR

logger = Logger()

@Gtk.Template(resource_path=f"{rootdir}/ui/preferences/ocr_model_page.ui")
class OCRModelPage(Adw.NavigationPage):
    __gtype_name__ = 'OCRModelPage'

    models_list = Gtk.Template.Child()
    search_entry = Gtk.Template.Child()
    models_stack = Gtk.Template.Child()

    def __init__(self, preferences_dialog=None, window=None, can_pop=True, **kwargs):
        super().__init__(**kwargs)
        self.preferences_dialog = preferences_dialog
        self.ocr = OCR(window)
        self.model_rows = []
        self._all_models = []
        self._setup_models()
        self.set_can_pop(can_pop)
        self.search_entry.connect("search-changed", self._on_search_changed)

    def _setup_models(self):
        installed_models = set(self.ocr.get_installed_models())
        downloadable_models = self.ocr.get_downloadable_models()

        downloadable_models.sort(key=lambda x: (x.code not in installed_models, x.name))

        self._all_models = downloadable_models

        for model in downloadable_models:
            row = self._build_row(model, installed_models)
            self.models_list.append(row)
            self.model_rows.append((model, row))

    def _build_row(self, model, installed_models):
        code = model.code
        name = model.name
        size = model.size
        is_installed = code in installed_models

        row = Adw.ActionRow(
            title=name,
            subtitle=GLib.format_size(size),
            activatable=True
        )

        if is_installed:
            delete_button = Gtk.Button(
                icon_name="user-trash-symbolic",
                tooltip_text="Delete Model",
                valign=Gtk.Align.CENTER,
            )
            delete_button.add_css_class("flat")
            delete_button.add_css_class("destructive-action")
            delete_button.connect("clicked", self._on_delete_model, code, name)
            row.add_suffix(delete_button)

            status_icon = Gtk.Image.new_from_icon_name("object-select-symbolic")
            status_icon.set_margin_end(10)
            status_icon.add_css_class("success")
            row.add_suffix(status_icon)
        else:
            download_button = Gtk.Button(
                icon_name="folder-download-symbolic",
                tooltip_text="Download Model",
                valign=Gtk.Align.CENTER
            )
            download_button.add_css_class("flat")
            download_button.connect("clicked", self._on_download_model, code, name)
            row.add_suffix(download_button)

        return row

    def _on_search_changed(self, entry):
        query = entry.get_text().strip().lower()
        any_visible = False
        for model, row in self.model_rows:
            visible = not query or query in model.name.lower() or query in model.code.lower()
            row.set_visible(visible)
            if visible:
                any_visible = True
        self.models_stack.set_visible_child_name("empty" if query and not any_visible else "list")

    def _on_download_model(self, button, model_code, model_name):
        button.set_sensitive(False)
        button.set_child(Adw.Spinner())

        def on_download_complete(success, message):
            if success:
                GLib.idle_add(self._refresh_models)
                toast = Adw.Toast(title=_("Downloaded '{}' Successfully").format(model_name), timeout=3)
                self.preferences_dialog.add_toast(toast)
            else:
                button.set_sensitive(True)
                button.set_child(Gtk.Image.new_from_icon_name("folder-download-symbolic"))
                logger.error(f"Download failed: {message}")
                toast = Adw.Toast(title=_("Failed to Download '{}'").format(model_name), timeout=5)
                self.preferences_dialog.add_toast(toast)

        self.ocr.download_model(model_code, on_download_complete)

    def _on_delete_model(self, button, model_code, model_name):
        try:
            self.ocr.delete_model(model_code)
            self._refresh_models()
        except ValueError as e:
            logger.error(str(e))

    def _refresh_models(self):
        for _, row in self.model_rows:
            self.models_list.remove(row)

        self.model_rows.clear()
        self._all_models = []
        self._setup_models()
        query = self.search_entry.get_text().strip().lower()
        if query:
            self._on_search_changed(self.search_entry)
        return False
