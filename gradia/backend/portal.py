from gi.repository import Gio, GLib
import uuid

class Portal:
    def __init__(self, app_id="be.alexandervanhee.gradia", reason="Allows Gradia to run in background and listen for it's global screenshot shortcut"):
        self.app_id = app_id
        self.reason = reason
        self.connection = Gio.bus_get_sync(Gio.BusType.SESSION, None)
        self.response_handler = None

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
        self._pending_callbacks = {}

    def request_background_permission(self, autostart=True, callback=None):
        handle_token = str(uuid.uuid4()).replace('-', '')

        options_dict = {
            "handle_token": GLib.Variant("s", handle_token),
            "reason": GLib.Variant("s", self.reason),
            "autostart": GLib.Variant("b", autostart),
            "dbus-activatable": GLib.Variant("b", False)
        }

        params = GLib.Variant("(sa{sv})", ("", options_dict))
        self._pending_callbacks[handle_token] = callback

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

    def _on_portal_response(self, connection, sender, path, interface, signal, parameters, user_data):
        response_code, results = parameters.unpack()
        handle_token = path.rsplit("/", 1)[-1]

        callback = self._pending_callbacks.pop(handle_token, None)

        if response_code == 0:
            background_allowed = results.get("background", False)
            autostart_allowed = results.get("autostart", False)
            if callback:
                callback(background_allowed, autostart_allowed, "Success")
        else:
            if callback:
                callback(False, False, f"Request failed with code: {response_code}")

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
