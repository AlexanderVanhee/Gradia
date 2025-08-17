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
gi.require_version("GtkSource", "5")

from gi.repository import Gtk, Adw, GLib, Gdk, Soup, GdkPixbuf, GtkSource, Gio
from gradia.backend.settings import Settings
from gradia.backend.logger import Logger
from gradia.constants import rel_ver
from gradia.constants import rootdir  # pyright: ignore
import json
logger = Logger()

@Gtk.Template(resource_path=f"{rootdir}/ui/preferences/provider_list_page.ui")
class ProviderListPage(Adw.NavigationPage):
    __gtype_name__ = 'ProviderListPage'

    view_stack = Gtk.Template.Child()
    loading_spinner = Gtk.Template.Child()
    loading_label = Gtk.Template.Child()
    error_status = Gtk.Template.Child()
    providers_group = Gtk.Template.Child()

    PROVIDERS_DATA_URL = f"https://gradia.alexandervanhee.be/upload-providers/{rel_ver}.json"

    def __init__(self, preferences_dialog=None,on_provider_selected=None, **kwargs):
        super().__init__(**kwargs)

        self.preferences_dialog = preferences_dialog
        self.on_provider_selected = on_provider_selected
        self.session = Soup.Session()
        self.providers_data = None
        self._load_providers_data()

    def _show_error_message(self, message: str):
        self.error_status.set_description(message)
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
                GLib.idle_add(self._populate_providers_list)
            except Exception as e:
                logger.error(f"Failed to load providers data from {self.PROVIDERS_DATA_URL}: {e}")
                GLib.idle_add(self._show_error_message, f"Failed to load providers: {e}")

        self.session.send_and_read_async(message, GLib.PRIORITY_DEFAULT, None, on_response, message)

    def _populate_providers_list(self):

        for provider_id, provider_data in self.providers_data.items():
            row = self._create_provider_row(provider_id, provider_data)
            self.providers_group.add(row)

        custom_row = self._create_custom_provider_row()
        self.providers_group.add(custom_row)

        self.view_stack.set_visible_child_name("content")

    def _create_provider_row(self, provider_id: str, provider_data: dict) -> Adw.ActionRow:
        row = Adw.ActionRow(
            title=provider_data["name"],
            subtitle=provider_data["description"],
            activatable=True
        )

        picture = Gtk.Picture(content_fit=Gtk.ContentFit.SCALE_DOWN)
        self._load_picture_from_url(
            picture,
            provider_data.get("icon_url"),
            32,
            fallback_icon_name="image-missing-symbolic"
        )
        row.add_prefix(picture)

        row.add_suffix(Gtk.Image.new_from_icon_name("go-next-symbolic"))

        row.provider_id = provider_id
        row.connect("activated", self._on_provider_selected)

        return row

    def _create_custom_provider_row(self) -> Adw.ActionRow:
        row = Adw.ActionRow(
            title=_("Custom Provider"),
            subtitle=_("Create your own custom upload command"),
            activatable=True
        )

        custom_icon = Gtk.Image.new_from_icon_name("engineering-symbolic")
        custom_icon.set_valign(Gtk.Align.CENTER)
        custom_icon.add_css_class("symbolic-circular")
        row.add_prefix(custom_icon)

        row.add_suffix(Gtk.Image.new_from_icon_name("go-next-symbolic"))

        row.provider_id = "custom"
        row.connect("activated", self._on_provider_selected)

        return row

    def _on_provider_selected(self, row: Adw.ActionRow):
        provider_id = row.provider_id

        if provider_id == "custom":
            custom_page = CustomProviderPage(
                preferences_dialog=self.preferences_dialog,
                on_provider_selected=self.on_provider_selected
            )
            self.preferences_dialog.push_subpage(custom_page)
        else:
            detail_page = ProviderDetailPage(
                preferences_dialog=self.preferences_dialog,
                provider_id=provider_id,
                providers_data=self.providers_data,
                session=self.session,
                on_provider_selected=self.on_provider_selected
            )
            self.preferences_dialog.push_subpage(detail_page)

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
                GLib.idle_add(picture.set_paintable, texture)
            except Exception as e:
                logger.warning(f"Failed to load image from {url}: {e}")
                GLib.idle_add(self._set_fallback_icon, picture, fallback_icon_name)

        self.session.send_and_read_async(message, GLib.PRIORITY_DEFAULT, None, on_response, message)

    def _set_fallback_icon(self, picture: Gtk.Picture, icon_name: str):
        display = Gdk.Display.get_default()
        icon_theme = Gtk.IconTheme.get_for_display(display)
        icon_info = icon_theme.lookup_icon(
            icon_name, None, 32, 1,
            Gtk.TextDirection.NONE,
            Gtk.IconLookupFlags.NONE
        )

        if icon_info:
            picture.set_paintable(icon_info)
        else:
            fallback_image = Gtk.Image.new_from_icon_name("image-missing-symbolic")
            picture.set_paintable(fallback_image.get_paintable())

        picture.set_size_request(32, 32)

@Gtk.Template(resource_path=f"{rootdir}/ui/preferences/custom_provider_page.ui")
class CustomProviderPage(Adw.NavigationPage):
    __gtype_name__ = 'CustomProviderPage'
    custom_save_button = Gtk.Template.Child()
    source_view = Gtk.Template.Child()

    def __init__(self, preferences_dialog: Adw.NavigationView, on_provider_selected=None, **kwargs):
        GtkSource.init()
        super().__init__(**kwargs)
        self.preferences_dialog = preferences_dialog
        self.on_provider_selected = on_provider_selected
        self._original_text = "echo $1"


        self._setup_source_view()
        self._setup_theme_monitoring()
        self._setup_buffer_monitoring()

        self.custom_save_button.add_css_class("suggested-action")
        self.source_view.add_css_class("provider-source-view")

    def _setup_source_view(self):
        buffer = self.source_view.get_buffer()
        language_manager = GtkSource.LanguageManager.get_default()
        language = language_manager.get_language('bash')
        if language:
            buffer.set_language(language)

        self._update_theme()
        buffer.set_text(self._original_text)

    def _setup_theme_monitoring(self):
        settings = Gtk.Settings.get_default()
        settings.connect('notify::gtk-application-prefer-dark-theme', self._on_theme_changed)
        adwaita_settings = Gio.Settings.new('org.gnome.desktop.interface')
        adwaita_settings.connect('changed::color-scheme', self._on_color_scheme_changed)

    def _setup_buffer_monitoring(self):
        buffer = self.source_view.get_buffer()
        buffer.connect('changed', self._on_buffer_changed)
        self._update_save_button_sensitivity()

    def _on_theme_changed(self, settings, pspec):
        self._update_theme()

    def _on_color_scheme_changed(self, settings, key):
        self._update_theme()

    def _on_buffer_changed(self, buffer):
        self._update_save_button_sensitivity()

    def _update_theme(self):
        buffer = self.source_view.get_buffer()
        style_scheme_manager = GtkSource.StyleSchemeManager.get_default()
        prefer_dark = self._is_dark_theme_preferred()
        buffer.set_style_scheme(style_scheme_manager.get_scheme('Adwaita-dark' if prefer_dark else 'Adwaita') or buffer.get_style_scheme())

    def _is_dark_theme_preferred(self):
        gtk_settings = Gtk.Settings.get_default()
        return gtk_settings.get_property('gtk-application-prefer-dark-theme')

    def _update_save_button_sensitivity(self):
        buffer = self.source_view.get_buffer()
        start_iter = buffer.get_start_iter()
        end_iter = buffer.get_end_iter()
        text = buffer.get_text(start_iter, end_iter, False).strip()
        has_changed = text != self._original_text.strip()
        is_not_empty = len(text) > 0
        self.custom_save_button.set_sensitive(has_changed and is_not_empty)

    @Gtk.Template.Callback()
    def _on_save_custom_provider(self, button: Gtk.Button):
        buffer = self.source_view.get_buffer()
        start_iter = buffer.get_start_iter()
        end_iter = buffer.get_end_iter()
        command = buffer.get_text(start_iter, end_iter, False)

        if self.on_provider_selected:
            self.on_provider_selected(_("Custom"), command)
            self.preferences_dialog.pop_subpage()
            self.preferences_dialog.pop_subpage()

        self._update_save_button_sensitivity()

@Gtk.Template(resource_path=f"{rootdir}/ui/preferences/provider_detail_page.ui")
class ProviderDetailPage(Adw.NavigationPage):
    __gtype_name__ = 'ProviderDetailPage'

    title_label = Gtk.Template.Child()
    subtitle_label = Gtk.Template.Child()
    provider_picture = Gtk.Template.Child()
    details_group = Gtk.Template.Child()
    homepage_row = Gtk.Template.Child()
    tos_row = Gtk.Template.Child()
    features_group = Gtk.Template.Child()
    command_group = Gtk.Template.Child()
    command_label = Gtk.Template.Child()

    def __init__(self, preferences_dialog: Adw.NavigationView, provider_id: str, providers_data: dict,
                 session: Soup.Session, on_provider_selected=None, **kwargs):
        self.provider_data = providers_data[provider_id]
        super().__init__(title=self.provider_data["name"], **kwargs)

        self.preferences_dialog = preferences_dialog
        self.provider_id = provider_id
        self.providers_data = providers_data
        self.session = session
        self.on_provider_selected = on_provider_selected
        self.homepage_url = None
        self.tos_url = None

        self._setup_ui()

    def _setup_ui(self):
        self.title_label.set_label(self.provider_data["name"])
        self.subtitle_label.set_label(self.provider_data["description"])
        self.details_group.set_description(self.provider_data["details"])

        self._load_picture_from_url(self.provider_picture, self.provider_data.get("icon_url"), 64)

        if self.provider_data.get("homepage_url"):
            self.homepage_url = self.provider_data["homepage_url"]
            self.homepage_row.set_subtitle(self.homepage_url)
            self.homepage_row.set_visible(True)

        if self.provider_data.get("tos_url"):
            self.tos_url = self.provider_data["tos_url"]
            self.tos_row.set_subtitle(self.tos_url)
            self.tos_row.set_visible(True)

        self._setup_features()
        self._setup_command()

    def _setup_features(self):
        for feature in self.provider_data.get("features", []):
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
            self.features_group.add(row)

    def _setup_command(self):
        upload_command = self.provider_data.get("upload_command")
        if upload_command:
            self.command_label.set_label(upload_command)
            self.command_group.set_visible(True)

    @Gtk.Template.Callback()
    def _on_select_provider(self, button: Gtk.Button):
        name = self.provider_data["name"]
        command = self.provider_data.get("upload_command")

        if self.on_provider_selected:
            self.on_provider_selected(name, command)

        self.preferences_dialog.pop_subpage()
        self.preferences_dialog.pop_subpage()

    @Gtk.Template.Callback()
    def _on_link_activated(self, row: Adw.ActionRow):
        if row == self.homepage_row and self.homepage_url:
            url = self.homepage_url
        elif row == self.tos_row and self.tos_url:
            url = self.tos_url
        else:
            return

        launcher = Gtk.UriLauncher.new(url)
        launcher.launch(None, None, None, None)

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
