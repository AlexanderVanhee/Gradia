from gi.repository import GObject, Gtk, Adw


class DropOverlay(Adw.Bin):
    __gtype_name__ = "DropOverlay"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self._drop_target = None
        self._handler_id = None

        self.overlay = Gtk.Overlay()
        self.revealer = Gtk.Revealer()
        self.status = Adw.StatusPage()

        self._setup_widgets()
        self.set_css_name("dropoverlay")

    def _setup_widgets(self):
        self.set_child(self.overlay)

        self.overlay.add_overlay(self.revealer)
        self.revealer.set_can_target(False)
        self.revealer.set_transition_type(Gtk.RevealerTransitionType.CROSSFADE)
        self.revealer.set_reveal_child(False)

        self.status.set_icon_name("document-send-symbolic")
        self.status.add_css_class("drop-overlay-status-page")
        self.revealer.set_child(self.status)

    def set_drop_target(self, drop_target):
        if self._drop_target is not None:
            self.remove_controller(self._drop_target)
            if self._handler_id is not None:
                self._drop_target.disconnect(self._handler_id)
                self._handler_id = None

        if drop_target is not None:
            self._handler_id = drop_target.connect(
                "notify::current-drop",
                self._on_current_drop_changed
            )
            self.add_controller(drop_target)

        self._drop_target = drop_target
        self.notify("drop-target")

    def get_drop_target(self):
        return self._drop_target

    def _on_current_drop_changed(self, target, pspec):
        current_drop = target.get_current_drop()
        self.revealer.set_reveal_child(current_drop is not None)

    def set_title(self, title):
        self.status.set_title(title)

    def get_title(self):
        return self.status.get_title()

    def set_child_widget(self, child):
        self.overlay.set_child(child)

    def get_child_widget(self):
        return self.overlay.get_child()

    @GObject.Property(type=str, default="", flags=GObject.ParamFlags.READWRITE)
    def title(self):
        return self.status.get_title()

    @title.setter
    def title(self, value):
        self.status.set_title(value)

    @GObject.Property(type=Gtk.DropTarget)
    def drop_target(self):
        return self._drop_target

    @drop_target.setter
    def drop_target(self, value):
        self.set_drop_target(value)

    @GObject.Property(type=Gtk.Widget)
    def child_widget(self):
        return self.overlay.get_child()

    @child_widget.setter
    def child_widget(self, value):
        self.overlay.set_child(value)

