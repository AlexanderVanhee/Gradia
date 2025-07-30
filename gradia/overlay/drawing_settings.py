from typing import Tuple, Optional
from dataclasses import dataclass

DEFAULT_ARROW_HEAD_SIZE = 25.0
DEFAULT_FONT_SIZE = 22.0
DEFAULT_HIGHLIGHTER_SIZE = 12.0
DEFAULT_PIXELATION_LEVEL = 8

@dataclass
class DrawingSettings:
    pen_color: Tuple[float, float, float, float] = (0.0, 0.0, 0.0, 1.0)
    pen_size: float = 3.0
    fill_color: Optional[Tuple[float, float, float, float]] = None
    outline_color: Optional[Tuple[float, float, float, float]] = None
    highlighter_color: Tuple[float, float, float, float] = (1.0, 1.0, 0.0, 0.5)
    highlighter_size: float = DEFAULT_HIGHLIGHTER_SIZE
    arrow_head_size: float = DEFAULT_ARROW_HEAD_SIZE
    font_size: float = DEFAULT_FONT_SIZE
    font_family: str = "Sans"
    number_radius: float = 20.0
    pixelation_level: int = DEFAULT_PIXELATION_LEVEL
    image_bounds: Tuple[int, int] = (1920, 1080)

    def set_pen_color(self, r: float, g: float, b: float, a: float=1.0) -> None:
        self.pen_color = (r, g, b, a)

    def set_fill_color(self, r: float, g: float, b: float, a: float=1) -> None:
        self.fill_color = (r, g, b, a)

    def set_outline_color(self, r: float, g: float, b: float, a: float=1) -> None:
        self.outline_color = (r, g, b, a)

    def set_highlighter_color(self, r: float, g: float, b: float, a: float=1) -> None:
        self.highlighter_color = (r, g, b, a)

    def set_pen_size(self, size: float) -> None:
        self.pen_size = max(1.0, size)

    def set_highlighter_size(self, size: float) -> None:
        self.highlighter_size = max(1.0, size)

    def set_arrow_head_size(self, size: float) -> None:
        self.arrow_head_size = max(5.0, size)

    def set_font_size(self, size: float) -> None:
        self.font_size = max(8.0, size)

    def set_font_family(self, family: str) -> None:
        self.font_family = family if family else "Sans"

    def set_highlighter_size(self, size: float) -> None:
        self.highlighter_size = max(1.0, size)

    def set_pixelation_level(self, level: int) -> None:
        self.pixelation_level = max(2, int(level))

    def set_number_radius(self, radius: float) -> None:
        self.number_radius = radius


    def copy(self) -> 'DrawingSettings':
        return DrawingSettings(
            pen_color=self.pen_color,
            pen_size=self.pen_size,
            fill_color=self.fill_color,
            outline_color=self.outline_color,
            highlighter_color=self.highlighter_color,
            highlighter_size=self.highlighter_size,
            arrow_head_size=self.arrow_head_size,
            font_size=self.font_size,
            font_family=self.font_family,
            number_radius=self.number_radius,
            pixelation_level=self.pixelation_level,
            image_bounds=self.image_bounds
        )
