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
gi.require_version("Soup", "3.0")

from gi.repository import Gtk, Adw, GLib, Gdk, Soup, GdkPixbuf
from gradia.backend.settings import Settings
from gradia.backend.logger import Logger

import json

logger = Logger()


class ProviderSelectionWindow(Adw.Window):
    __gtype_name__ = 'ProviderSelectionWindow'

    PROVIDERS_DATA_URL = "https://gradia.alexandervanhee.be/upload-providers/provider-info.json"

    def __init__(self, parent_window: Adw.PreferencesWindow, on_provider_selected=None, **kwargs):
        super().__init__(
            title=_("Choose Provider"),
            modal=True,
            transient_for=parent_window,
            default_width=700,
            default_height=500,
            **kwargs
        )

        self.parent_window = parent_window
        self.settings = Settings()
        self.on_provider_selected = on_provider_selected
        self.session = Soup.Session()
        self.providers_data = None

        self.view_stack = Adw.ViewStack(enable_transitions=True)
        self.set_content(self.view_stack)

        self._setup_loading_page()
        self._setup_error_page()
        self._load_providers_data()

    def _setup_loading_page(self):
        loading_box = Gtk.Box(
            orientation=Gtk.Orientation.VERTICAL,
            spacing=12,
            halign=Gtk.Align.CENTER,
            valign=Gtk.Align.CENTER
        )

        spinner = Adw.Spinner.new()
        spinner.set_size_request(32, 32)

        label = Gtk.Label(label=_("Loading providers data..."), vexpand=True, hexpand=True)

        loading_box.append(spinner)
        loading_box.append(label)

        self.view_stack.add_named(loading_box, "loading")
        self.view_stack.set_visible_child_name("loading")

    def _setup_error_page(self):
        page = Adw.NavigationPage(title=_("Error"))
        header_bar = Adw.HeaderBar()
        content = Adw.ToolbarView()
        content.add_top_bar(header_bar)

        error_status_page = Adw.StatusPage.new()
        error_status_page.set_title(_("An error occurred"))
        error_status_page.set_description(_("Please try again later."))
        error_status_page.set_icon_name("dialog-error-symbolic")

        clamp = Adw.Clamp(
            maximum_size=600,
            tightening_threshold=400,
            child=error_status_page,
            margin_top=24,
            margin_bottom=24,
            margin_start=12,
            margin_end=12
        )

        content.set_content(clamp)
        page.set_child(content)

        self.view_stack.add_named(page, "error")

    def _show_content_page(self, widget: Gtk.Widget):
        if self.view_stack.get_child_by_name("content"):
            self.view_stack.remove(self.view_stack.get_child_by_name("content"))
        self.view_stack.add_named(widget, "content")
        self.view_stack.set_visible_child_name("content")

    def _show_error_message(self, message: str):
        self.view_stack.set_visible_child_name("error")

    def _load_providers_data(self):
        message = Soup.Message.new("GET", self.PROVIDERS_DATA_URL)

        def on_response(session, result, msg):
            try:
                if msg.get_status() != Soup.Status.OK:
                    raise RuntimeError(f"HTTP error status {msg.get_status()}")

                glib_bytes = session.send_and_read_finish(result)
                raw_bytes = glib_bytes.get_data()
                json_data = raw_bytes.decode('utf-8')
                self.providers_data = json.loads(json_data)
                GLib.idle_add(self._create_provider_list_page)
            except Exception as e:
                logger.error(f"Failed to load providers data from {self.PROVIDERS_DATA_URL}: {e}")
                GLib.idle_add(self._show_error_message, f"Failed to load providers: {e}")

        self.session.send_and_read_async(message, GLib.PRIORITY_DEFAULT, None, on_response, message)

    def _create_provider_list_page(self):
        page = Adw.NavigationPage(title=_("Choose Provider"))
        header_bar = Adw.HeaderBar()

        content = Adw.ToolbarView()
        content.add_top_bar(header_bar)

        scrolled = Gtk.ScrolledWindow(
            hscrollbar_policy=Gtk.PolicyType.NEVER,
            vscrollbar_policy=Gtk.PolicyType.AUTOMATIC
        )

        list_box = Gtk.ListBox(valign=Gtk.Align.START, selection_mode=Gtk.SelectionMode.NONE)
        list_box.add_css_class("boxed-list")


        for provider_id, provider_data in self.providers_data.items():
            row = Adw.ActionRow(
                title=provider_data["name"],
                subtitle=provider_data["description"],
                activatable=True
            )

            picture = Gtk.Picture(content_fit=Gtk.ContentFit.SCALE_DOWN)
            self._load_picture_from_url(picture, provider_data.get("icon_url"), 32, fallback_icon_name="image-missing-symbolic")
            row.add_prefix(picture)

            row.add_suffix(Gtk.Image.new_from_icon_name("go-next-symbolic"))
            row.provider_id = provider_id
            row.connect("activated", self._on_provider_selected)
            list_box.append(row)


        custom_row = Adw.ActionRow(
            title=_("Custom Provider"),
            subtitle=_("Create your own custom upload command"),
            activatable=True
        )

        custom_icon = Gtk.Image.new_from_icon_name("applications-engineering-symbolic")
        custom_icon.set_margin_start(8)
        custom_icon.set_margin_end(8)
        custom_row.add_prefix(custom_icon)
        custom_row.add_suffix(Gtk.Image.new_from_icon_name("go-next-symbolic"))
        custom_row.provider_id = "custom"
        custom_row.connect("activated", self._on_provider_selected)
        list_box.append(custom_row)

        scrolled.set_child(list_box)

        clamp = Adw.Clamp(
            maximum_size=600,
            tightening_threshold=400,
            child=scrolled,
            margin_top=24,
            margin_bottom=24,
            margin_start=12,
            margin_end=12
        )

        content.set_content(clamp)
        page.set_child(content)

        self.navigation_view = Adw.NavigationView()
        self.navigation_view.add(page)
        self._show_content_page(self.navigation_view)

    def _create_custom_provider_page(self):
        page = Adw.NavigationPage(title=_("Custom Provider"))

        header_bar = Adw.HeaderBar()
        save_button = Gtk.Button(label=_("Save"))
        save_button.add_css_class("suggested-action")
        save_button.connect("clicked", self._on_save_custom_provider)
        save_button.set_sensitive(False)
        header_bar.pack_end(save_button)
        self.custom_save_button = save_button

        content = Adw.ToolbarView()
        content.add_top_bar(header_bar)

        scrolled = Gtk.ScrolledWindow(
            hscrollbar_policy=Gtk.PolicyType.NEVER,
            vscrollbar_policy=Gtk.PolicyType.AUTOMATIC
        )

        clamp = Adw.Clamp(
            maximum_size=600,
            tightening_threshold=400,
            margin_top=24,
            margin_bottom=24,
            margin_start=12,
            margin_end=12
        )

        main_box = Gtk.Box(
            orientation=Gtk.Orientation.VERTICAL,
            spacing=24
        )

        command_section = Adw.PreferencesGroup(
            title=_("Upload Command"),
            description=_("Enter a custom command to upload files. Use $1 as a placeholder for the file path.")
        )

        command_row = Adw.ActionRow(
            title=_("Command")
        )
        command_row.set_activatable(False)

        command_buffer = Gtk.TextBuffer()
        command_buffer.connect("changed", self._on_custom_field_changed)
        self.custom_command_buffer = command_buffer

        command_text_view = Gtk.TextView(
            buffer=command_buffer,
            wrap_mode=Gtk.WrapMode.WORD,
            accepts_tab=False,
            monospace=True,
            height_request=80
        )

        command_scrolled = Gtk.ScrolledWindow(
            hscrollbar_policy=Gtk.PolicyType.AUTOMATIC,
            vscrollbar_policy=Gtk.PolicyType.AUTOMATIC,
            child=command_text_view,
            margin_top=6,
            margin_bottom=6,
            margin_start=6,
            margin_end=6
        )
        command_scrolled.add_css_class("card")

        command_box = Gtk.Box(
            orientation=Gtk.Orientation.VERTICAL,
            spacing=6
        )
        command_box.append(command_scrolled)

        command_row.set_child(command_box)
        command_section.add(command_row)

        main_box.append(command_section)

        clamp.set_child(main_box)
        scrolled.set_child(clamp)
        content.set_content(scrolled)
        page.set_child(content)

        return page

    def _create_provider_detail_page(self, provider_id: str):
        provider_data = self.providers_data[provider_id]

        page = Adw.NavigationPage(title=provider_data["name"])

        header_bar = Adw.HeaderBar()
        select_button = Gtk.Button(label=_("Select"))
        select_button.add_css_class("suggested-action")
        select_button.connect("clicked", self._on_select_provider, provider_id)
        header_bar.pack_end(select_button)

        content = Adw.ToolbarView()
        content.add_top_bar(header_bar)

        clamp = Adw.Clamp(maximum_size=600, tightening_threshold=400)

        main_box = Gtk.Box(
            orientation=Gtk.Orientation.VERTICAL,
            spacing=24,
            margin_top=24,
            margin_bottom=24,
            margin_start=24,
            margin_end=24
        )

        header_box = Gtk.Box(
            orientation=Gtk.Orientation.HORIZONTAL,
            spacing=12,
            halign=Gtk.Align.START
        )

        picture = Gtk.Picture(
            width_request=48,
            height_request=48,
            content_fit=Gtk.ContentFit.COVER
        )
        self._load_picture_from_url(picture, provider_data.get("icon_url"), 64, fallback_icon_name="image-missing-symbolic")

        title_box = Gtk.Box(
            orientation=Gtk.Orientation.VERTICAL,
            halign=Gtk.Align.START,
            valign=Gtk.Align.CENTER
        )

        title_label = Gtk.Label(label=provider_data["name"], halign=Gtk.Align.START)
        title_label.add_css_class("title-2")

        subtitle_label = Gtk.Label(label=provider_data["description"], halign=Gtk.Align.START)
        subtitle_label.add_css_class("dim-label")

        title_box.append(title_label)
        title_box.append(subtitle_label)

        header_box.append(picture)
        header_box.append(title_box)
        main_box.append(header_box)

        details_group = Adw.PreferencesGroup(title=_("About"), description=provider_data["details"])
        if provider_data.get("homepage_url"):
            homepage_row = Adw.ActionRow(
                title=_("Homepage"),
                subtitle=provider_data["homepage_url"],
                activatable=True
            )
            homepage_row.add_prefix(Gtk.Image.new_from_icon_name("house-symbolic"))
            homepage_row.add_suffix(Gtk.Image.new_from_icon_name("adw-external-link-symbolic"))
            homepage_row.connect("activated", self._on_link_activated, provider_data["homepage_url"])
            details_group.add(homepage_row)

        if provider_data.get("tos_url"):
            tos_row = Adw.ActionRow(
                title=_("Terms of Service"),
                subtitle=provider_data["tos_url"],
                activatable=True
            )
            tos_row.add_prefix(Gtk.Image.new_from_icon_name("text-x-generic-symbolic"))
            tos_row.add_suffix(Gtk.Image.new_from_icon_name("adw-external-link-symbolic"))
            tos_row.connect("activated", self._on_link_activated, provider_data["tos_url"])
            details_group.add(tos_row)

        main_box.append(details_group)

        features_group = Adw.PreferencesGroup(title=_("Features"))
        for feature in provider_data.get("features", []):
            row = Adw.ActionRow(title=feature["text"])
            if feature["type"] == "positive":
                icon_name = "object-select-symbolic"
                css_class = "success"
            elif feature["type"] == "negative":
                icon_name = "dialog-error-symbolic"
                css_class = "error"
            else:
                icon_name = "dialog-information-symbolic"
                css_class = "info"

            icon = Gtk.Image.new_from_icon_name(icon_name)
            icon.add_css_class(css_class)
            row.add_prefix(icon)
            features_group.add(row)
        main_box.append(features_group)

        upload_command = provider_data.get("upload_command")
        if upload_command:
            command_group = Adw.PreferencesGroup(title=_("Upload Command"))
            command_label = Gtk.Label(
                label=upload_command,
                xalign=0,
                wrap=False,
                margin_top=10,
                margin_bottom=10,
                margin_start=10,
                margin_end=10
            )
            command_label.add_css_class("monospace")

            command_scrolled_window = Gtk.ScrolledWindow(
                hscrollbar_policy=Gtk.PolicyType.AUTOMATIC,
                vscrollbar_policy=Gtk.PolicyType.NEVER,
                child=command_label,
                hexpand=True,
            )

            command_row = Adw.ActionRow(title="")
            command_row.set_activatable(False)
            command_row.set_selectable(False)
            command_row.set_child(command_scrolled_window)

            command_group.add(command_row)
            main_box.append(command_group)

        clamp.set_child(main_box)

        scrolled = Gtk.ScrolledWindow(
            hscrollbar_policy=Gtk.PolicyType.NEVER,
            vscrollbar_policy=Gtk.PolicyType.AUTOMATIC,
            child=clamp
        )

        content.set_content(scrolled)
        page.set_child(content)
        return page

    def _on_provider_selected(self, row: Adw.ActionRow):
        provider_id = row.provider_id

        if provider_id == "custom":
            custom_page = self._create_custom_provider_page()
            self.navigation_view.push(custom_page)
        else:
            detail_page = self._create_provider_detail_page(provider_id)
            self.navigation_view.push(detail_page)

    def _on_custom_field_changed(self, widget):
        start_iter = self.custom_command_buffer.get_start_iter()
        end_iter = self.custom_command_buffer.get_end_iter()
        command = self.custom_command_buffer.get_text(start_iter, end_iter, False).strip()

        can_save = bool(command)
        self.custom_save_button.set_sensitive(can_save)


    def _on_save_custom_provider(self, button: Gtk.Button):
        start_iter = self.custom_command_buffer.get_start_iter()
        end_iter = self.custom_command_buffer.get_end_iter()
        command = self.custom_command_buffer.get_text(start_iter, end_iter, False).strip()

        if command:
            if self.on_provider_selected:
                self.on_provider_selected(_("Custom"), command)
            self.close()

    def _on_select_provider(self, button: Gtk.Button, provider_id: str):
        provider_data = self.providers_data[provider_id]
        name = provider_data["name"]
        command = provider_data.get("upload_command")

        if self.on_provider_selected:
            self.on_provider_selected(name, command)

        self.close()

    def _on_link_activated(self, row: Adw.ActionRow, url: str):
        launcher = Gtk.UriLauncher.new(url)
        launcher.launch(self, None, None, None)

    def _load_picture_from_url(self, picture: Gtk.Picture, url: str, size_px: int, fallback_icon_name: str = "image-missing-symbolic"):
        if not url:
            GLib.idle_add(self._set_fallback_icon, picture, fallback_icon_name)
            return

        message = Soup.Message.new("GET", url)

        def on_response(session, result, msg):
            try:
                if msg.get_status() != Soup.Status.OK:
                    raise RuntimeError(f"HTTP error status {msg.get_status()}")

                glib_bytes = session.send_and_read_finish(result)
                raw_bytes = glib_bytes.get_data()

                loader = GdkPixbuf.PixbufLoader.new()
                loader.write(raw_bytes)
                loader.close()

                pixbuf = loader.get_pixbuf()
                if pixbuf is None:
                    raise RuntimeError("Loaded pixbuf is None")

                scaled_pixbuf = pixbuf.scale_simple(size_px, size_px, GdkPixbuf.InterpType.BILINEAR)
                if scaled_pixbuf is None:
                    raise RuntimeError("Failed to scale pixbuf")

                texture = Gdk.Texture.new_for_pixbuf(scaled_pixbuf)
                picture.set_paintable(texture)
            except Exception as e:
                logger.warn(f"Failed to load image from {url}: {e}")
                GLib.idle_add(self._set_fallback_icon, picture, fallback_icon_name)

        self.session.send_and_read_async(message, GLib.PRIORITY_DEFAULT, None, on_response, message)

    def _set_fallback_icon(self, picture: Gtk.Picture, icon_name: str):
        display = Gdk.Display.get_default()
        icon_theme = Gtk.IconTheme.get_for_display(display)
        icon_info = icon_theme.lookup_icon(icon_name, None, 32, 1, Gtk.TextDirection.NONE, Gtk.IconLookupFlags.NONE)

        if icon_info:
            picture.set_paintable(icon_info)
        else:
            picture.set_paintable(Gtk.Image.new_from_icon_name("image-missing-symbolic").get_paintable())

        picture.set_size_request(32, 32)
