# Copyright (C) 2025 Alexander Vanhee, tfuxu
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
from typing import Literal, Optional, Sequence
from dataclasses import dataclass, field
from ctypes import CDLL, POINTER, Structure, c_double, c_int, c_uint8
import json

from PIL import Image

from gradia.graphics.background import Background
from gradia.utils.colors import parse_rgb_string


Step = tuple[float, str]  # (position, "rgb(r,g,b)")


class ColorStop(Structure):
    _fields_ = [
        ("position", c_double),
        ("r", c_uint8),
        ("g", c_uint8),
        ("b", c_uint8),
    ]


@dataclass
class Gradient:
    mode: Literal["linear", "conic", "radial"] = "linear"
    steps: Sequence[Step] = field(default_factory=lambda: [
        (0.0, "rgb(87,227,137)"),
        (1.0, "rgb(53,132,228)"),
    ])
    angle: float = 135.0

    def to_json(self) -> str:
        return json.dumps({
            "mode": self.mode,
            "steps": self.steps,
            "angle": self.angle,
        })

    @classmethod
    def from_json(cls, json_str: str) -> 'Gradient':
        try:
            data = json.loads(json_str)
            return cls(
                mode=data.get("mode", "linear"),
                steps=data.get("steps", [
                    (0.0, "rgb(87,227,137)"),
                    (1.0, "rgb(53,132,228)"),
                ]),
                angle=data.get("angle", 135.0),
            )
        except Exception:
            return cls()

    def to_css(self) -> str:
        steps_str = ", ".join(
            f"{color} {step * 100:.2f}%" for step, color in self.steps
        )

        if self.mode == "linear":
            return f"linear-gradient({self.angle:.2f}deg, {steps_str})"
        elif self.mode == "conic":
            return f"conic-gradient(from {self.angle:.2f}deg, {steps_str})"
        elif self.mode == "radial":
            return f"radial-gradient(circle, {steps_str})"
        else:
            return ""


@dataclass
class GradientBackground(Background):
    gradient: Gradient = field(default_factory=Gradient)
    _c_lib: Optional[CDLL] = None

    def __init__(self, gradient: Optional[Gradient] = None):
        self.gradient = gradient or Gradient()
        self._load_c_lib()

    @classmethod
    def _load_c_lib(cls) -> None:
        if cls._c_lib is not None:
            return

        from importlib.resources import files
        gradia_path = files("gradia").joinpath("libgradient_gen.so")
        cls._c_lib = CDLL(str(gradia_path))
        cls._c_lib.generate_gradient.argtypes = [
            POINTER(c_uint8), c_int, c_int,
            POINTER(ColorStop), c_int,
            c_double, c_int
        ]
        cls._c_lib.generate_gradient.restype = None

    @classmethod
    def from_json(cls, json_str: str) -> 'GradientBackground':
        return cls(gradient=Gradient.from_json(json_str))

    def to_json(self) -> str:
        return self.gradient.to_json()

    def get_name(self) -> str:
        return "Gradient"

    def prepare_image(self, width: int, height: int) -> Image.Image:
        if self._c_lib is None:
            raise RuntimeError("C gradient library not loaded")
        return self._generate_gradient_c(width, height)

    def _generate_gradient_c(self, width: int, height: int) -> Image.Image:
        pixel_count = width * height * 4
        pixel_buffer = (c_uint8 * pixel_count)()

        steps = self.gradient.steps
        if self.gradient.mode == "conic":
            offset = (self.gradient.angle % 360.0) / 360.0
            steps = [(((pos * 0.9) + 0.05 + offset) % 1.0, color) for pos, color in steps]
            steps.sort(key=lambda s: s[0])
            steps.append((1.0, steps[0][1]))

        parsed_stops = []
        for pos, color_str in steps:
            r, g, b = parse_rgb_string(color_str)
            parsed_stops.append(ColorStop(pos, r, g, b))

        stop_array = (ColorStop * len(parsed_stops))(*parsed_stops)

        mode_map = {
            "linear": 0,
            "conic": 1,
            "radial": 2,
        }

        mode = mode_map.get(self.gradient.mode, 0)

        self._c_lib.generate_gradient(
            pixel_buffer, width, height,
            stop_array, len(parsed_stops),
            float(self.gradient.angle),
            mode
        )

        return Image.frombytes("RGBA", (width, height), bytes(pixel_buffer))

