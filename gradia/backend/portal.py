from gi.repository import Gio, GLib, Gtk, Gdk
import uuid

class XdgPortal:
    def __init__(self, reason="Allows Gradia to run in background and listen for it's global screenshot shortcut"):
        self.reason = reason
        self.connection = Gio.bus_get_sync(Gio.BusType.SESSION, None)
        self.response_handler = None
        self.session_handle = None
        self.connection.signal_subscribe(
            "org.freedesktop.portal.Desktop",
            "org.freedesktop.portal.Request",
            "Response",
            None,
            None,
            Gio.DBusSignalFlags.NONE,
            self._on_portal_response,
            None
        )
        self.connection.signal_subscribe(
            "org.freedesktop.portal.Desktop",
            "org.freedesktop.portal.GlobalShortcuts",
            "Activated",
            None,
            None,
            Gio.DBusSignalFlags.NONE,
            self._on_shortcut_activated,
            None
        )
        self._pending_callbacks = {}
        self._shortcut_callback = None

    def request_background_permission(self, autostart=True, callback=None, force_dialog=True):
        handle_token = str(uuid.uuid4()).replace('-', '')
        options_dict = {
            "handle_token": GLib.Variant("s", handle_token),
            "reason": GLib.Variant("s", self.reason),
            "autostart": GLib.Variant("b", autostart),
            "dbus-activatable": GLib.Variant("b", False)
        }

        if force_dialog:
            options_dict["modal"] = GLib.Variant("b", True)
            options_dict["ask"] = GLib.Variant("b", True)

        params = GLib.Variant("(sa{sv})", ("", options_dict))
        self._pending_callbacks[handle_token] = ("background", callback)
        self.connection.call(
            "org.freedesktop.portal.Desktop",
            "/org/freedesktop/portal/desktop",
            "org.freedesktop.portal.Background",
            "RequestBackground",
            params,
            GLib.VariantType("(o)"),
            Gio.DBusCallFlags.NONE,
            -1,
            None,
            None
        )
        return True

    def create_session(self, callback=None):
        handle_token = str(uuid.uuid4()).replace('-', '')
        session_token = str(uuid.uuid4()).replace('-', '')
        options_dict = {
            "handle_token": GLib.Variant("s", handle_token),
            "session_handle_token": GLib.Variant("s", session_token)
        }
        params = GLib.Variant("(a{sv})", (options_dict,))
        self._pending_callbacks[handle_token] = ("session", callback)
        self.connection.call(
            "org.freedesktop.portal.Desktop",
            "/org/freedesktop/portal/desktop",
            "org.freedesktop.portal.GlobalShortcuts",
            "CreateSession",
            params,
            GLib.VariantType("(o)"),
            Gio.DBusCallFlags.NONE,
            -1,
            None,
            None
        )
        return True

    def bind_shortcuts(self, shortcuts, parent_window=None, callback=None, force_dialog=False):
        if not self.session_handle:
            raise Exception("Session not created. Call create_session first.")

        handle_token = str(uuid.uuid4()).replace('-', '')
        shortcuts_array = []

        for shortcut_id, shortcut_data in shortcuts.items():
            shortcut_dict = {
                "description": GLib.Variant("s", shortcut_data.get("description", "")),
                "preferred_trigger": GLib.Variant("s", shortcut_data.get("preferred_trigger", ""))
            }

            if force_dialog:
                shortcut_dict["preferred_trigger"] = GLib.Variant("s", "")

            shortcuts_array.append((shortcut_id, shortcut_dict))

        options_dict = {
            "handle_token": GLib.Variant("s", handle_token)
        }


        params = GLib.Variant("(oa(sa{sv})sa{sv})",
                              (self.session_handle, shortcuts_array, "", options_dict))
        self._pending_callbacks[handle_token] = ("bind", callback)
        self.connection.call(
            "org.freedesktop.portal.Desktop",
            "/org/freedesktop/portal/desktop",
            "org.freedesktop.portal.GlobalShortcuts",
            "BindShortcuts",
            params,
            GLib.VariantType("(o)"),
            Gio.DBusCallFlags.NONE,
            -1,
            None,
            None
        )
        return True

    def list_shortcuts(self, callback=None):
        if not self.session_handle:
            raise Exception("Session not created. Call create_session first.")
        handle_token = str(uuid.uuid4()).replace('-', '')
        options_dict = {
            "handle_token": GLib.Variant("s", handle_token)
        }
        params = GLib.Variant("(oa{sv})", (self.session_handle, options_dict))
        self._pending_callbacks[handle_token] = ("list", callback)
        self.connection.call(
            "org.freedesktop.portal.Desktop",
            "/org/freedesktop/portal/desktop",
            "org.freedesktop.portal.GlobalShortcuts",
            "ListShortcuts",
            params,
            GLib.VariantType("(o)"),
            Gio.DBusCallFlags.NONE,
            -1,
            None,
            None
        )
        return True

    def set_shortcut_activated_callback(self, callback):
        self._shortcut_callback = callback

    def _on_portal_response(self, connection, sender, path, interface, signal, parameters, user_data):
        response_code, results = parameters.unpack()
        handle_token = path.rsplit("/", 1)[-1]
        callback_info = self._pending_callbacks.pop(handle_token, None)
        if not callback_info:
            return
        request_type, callback = callback_info
        if request_type == "background":
            if response_code == 0:
                background_allowed = results.get("background", False)
                autostart_allowed = results.get("autostart", False)
                if callback:
                    callback(background_allowed, autostart_allowed, "Success")
            else:
                if callback:
                    callback(False, False, f"Request failed with code: {response_code}")
        elif request_type == "session":
            if response_code == 0:
                self.session_handle = results.get("session_handle", "")
                if callback:
                    callback(True, self.session_handle)
            else:
                if callback:
                    callback(False, f"Session creation failed with code: {response_code}")
        elif request_type == "bind":
            if response_code in [0, 2]:
                shortcuts = results.get("shortcuts", [])
                if callback:
                    callback(True, shortcuts)
            else:
                if callback:
                    callback(False, f"Bind shortcuts failed with code: {response_code}")
        elif request_type == "list":
            if response_code == 0:
                shortcuts = results.get("shortcuts", [])
                if callback:
                    callback(True, shortcuts)
            else:
                if callback:
                    callback(False, f"List shortcuts failed with code: {response_code}")
        elif request_type == "configure":
            if response_code == 0:
                shortcuts = results.get("shortcuts", [])
                if callback:
                    callback(True, shortcuts, "Configuration successful")
            elif response_code == 1:
                if callback:
                    callback(False, [], "User cancelled configuration")
            else:
                if callback:
                    callback(False, [], f"Configuration failed with code: {response_code}")

    def _on_shortcut_activated(self, connection, sender, path, interface, signal, parameters, user_data):
        session_handle, shortcut_id, timestamp, options = parameters.unpack()
        if self._shortcut_callback:
            self._shortcut_callback("activated", shortcut_id, timestamp)

    def set_background_status(self, message):
        if len(message) >= 96:
            message = message[:95]
        options_dict = {
            "message": GLib.Variant("s", message)
        }
        params = GLib.Variant("(a{sv})", (options_dict,))
        self.connection.call(
            "org.freedesktop.portal.Desktop",
            "/org/freedesktop/portal/desktop",
            "org.freedesktop.portal.Background",
            "SetStatus",
            params,
            None,
            Gio.DBusCallFlags.NONE,
            -1,
            None,
            None
        )
        return True
