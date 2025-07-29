from gi.repository import Adw, Gtk
from typing import Callable, Optional
from gi.repository import Gtk, GObject
from gradia.utils.colors import HexColor
from gradia.graphics.gradient import GradientBackground
from gradia.app_constants import PREDEFINED_GRADIENTS

class GradientPresetButton(Gtk.MenuButton):
    __gtype_name__ = "GradiaGradientPresetButton"

    def __init__(
        self,
        callback: Optional[Callable[[HexColor, HexColor, int], None]] = None,
        **kwargs
    ) -> None:
        super().__init__(**kwargs)

        self.callback = callback

        self.set_icon_name("view-grid-symbolic")
        self.set_valign(Gtk.Align.CENTER)
        self.add_css_class("flat")

        self._setup_popover()

    def _setup_popover(self) -> None:
        self.popover = Gtk.Popover()
        self.set_popover(self.popover)

        main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        main_box.set_spacing(8)
        main_box.set_margin_top(8)
        main_box.set_margin_bottom(8)
        main_box.set_margin_start(8)
        main_box.set_margin_end(8)

        self.flowbox = Gtk.FlowBox()
        self.flowbox.set_max_children_per_line(3)
        self.flowbox.set_selection_mode(Gtk.SelectionMode.NONE)
        self.flowbox.set_homogeneous(True)
        self.flowbox.set_row_spacing(8)
        self.flowbox.set_column_spacing(8)

        self._create_gradient_buttons()

        main_box.append(self.flowbox)
        self.popover.set_child(main_box)

    def _create_gradient_buttons(self) -> None:
        for i, (start, end, angle) in enumerate(PREDEFINED_GRADIENTS[:6]):
            gradient_name = f"gradient-preset-{i}"

            button = Gtk.Button(
                name=gradient_name,
                focusable=True,
                can_focus=True,
                width_request=60,
                height_request=40
            )
            button.add_css_class("gradient-preset")

            self._apply_gradient_to_button(button, start, end, angle)

            button.connect("clicked", self._on_gradient_button_clicked, start, end, angle)

            self.flowbox.append(button)

    def _apply_gradient_to_button(self, button: Gtk.Button, start: str, end: str, angle: int) -> None:
        css = f"""
            button.gradient-preset {{
                background-image: linear-gradient({angle}deg, {start}, {end});
            }}
        """

        css_provider = Gtk.CssProvider()
        css_provider.load_from_string(css)
        button.get_style_context().add_provider(
            css_provider,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION + 3
        )

    def _on_gradient_button_clicked(self, button: Gtk.Button, start: HexColor, end: HexColor, angle: int) -> None:
        self.popover.popdown()

        if self.callback:
            self.callback(start, end, angle)

    def set_callback(self, callback: Callable[[HexColor, HexColor, int], None]) -> None:
        self.callback = callback

    def set_gradient_presets(self, gradients: list[tuple[HexColor, HexColor, int]]) -> None:
        child = self.flowbox.get_first_child()
        while child:
            next_child = child.get_next_sibling()
            self.flowbox.remove(child)
            child = next_child

        for i, (start, end, angle) in enumerate(gradients[:6]):
            gradient_name = f"gradient-preset-{i}"

            button = Gtk.Button(
                name=gradient_name,
                focusable=True,
                can_focus=True,
                width_request=60,
                height_request=40
            )
            button.add_css_class("gradient-preset")

            self._apply_gradient_to_button(button, start, end, angle)
            button.connect("clicked", self._on_gradient_button_clicked, start, end, angle)

            self.flowbox.append(button)
