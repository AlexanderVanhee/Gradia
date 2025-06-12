from gi.repository import Gio, Gdk

class Settings:
    def __init__(self):
        self._settings = Gio.Settings.new("be.alexandervanhee.gradia")

    def _parse_rgba(self, color_str: str, fallback: tuple[float, float, float, float]) -> Gdk.RGBA:
        rgba = Gdk.RGBA()
        try:
            parts = list(map(float, color_str.split(',')))
            if len(parts) == 4:
                rgba.red, rgba.green, rgba.blue, rgba.alpha = parts
            else:
                rgba.red, rgba.green, rgba.blue, rgba.alpha = fallback
        except (ValueError, IndexError):
            rgba.red, rgba.green, rgba.blue, rgba.alpha = fallback
        return rgba

    def _rgba_to_string(self, rgba: Gdk.RGBA) -> str:
        return f"{rgba.red:.3f},{rgba.green:.3f},{rgba.blue:.3f},{rgba.alpha:.3f}"

    @property
    def draw_mode(self) -> str:
        return self._settings.get_string("draw-mode")

    @draw_mode.setter
    def draw_mode(self, value: str):
        print(value)
        self._settings.set_string("draw-mode", value)

    @property
    def pen_color(self) -> Gdk.RGBA:
        return self._parse_rgba(
            self._settings.get_string("pen-color"),
            fallback=(1.0, 1.0, 1.0, 1.0)
        )

    @pen_color.setter
    def pen_color(self, value: Gdk.RGBA):
        self._settings.set_string("pen-color", self._rgba_to_string(value))

    @property
    def highlighter_color(self) -> Gdk.RGBA:
        return self._parse_rgba(
            self._settings.get_string("highlighter-color"),
            fallback=(1.0, 1.0, 0.0, 0.5)
        )

    @highlighter_color.setter
    def highlighter_color(self, value: Gdk.RGBA):
        self._settings.set_string("highlighter-color", self._rgba_to_string(value))

    @property
    def fill_color(self) -> Gdk.RGBA:
        return self._parse_rgba(
            self._settings.get_string("fill-color"),
            fallback=(0.0, 0.0, 0.0, 0.0)
        )

    @fill_color.setter
    def fill_color(self, value: Gdk.RGBA):
        self._settings.set_string("fill-color", self._rgba_to_string(value))

    @property
    def pen_size(self) -> float:
        return self._settings.get_double("pen-size")

    @pen_size.setter
    def pen_size(self, value: float):
        self._settings.set_double("pen-size", value)

    @property
    def number_radius(self) -> float:
        return self._settings.get_double("number-radius")

    @number_radius.setter
    def number_radius(self, value: float):
        self._settings.set_double("number-radius", value)

    @property
    def font(self) -> str:
        return self._settings.get_string("font")

    @font.setter
    def font(self, value: str):
        self._settings.set_string("font", value)



    @property
    def screenshot_subfolder(self) -> str:
        return self._settings.get_string("screenshot-subfolder")

    @screenshot_subfolder.setter
    def screenshot_subfolder(self, value: str):
        self._settings.set_string("screenshot-subfolder", value)



