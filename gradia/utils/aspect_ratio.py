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

def parse_aspect_ratio(text: str) -> float | None:
    text = text.strip()
    if not text:
        return None
    if ":" in text:
        num, denom = map(float, text.split(":"))
        if denom == 0:
            raise ValueError("Denominator cannot be zero")
        return num / denom
    return float(text)

def check_aspect_ratio_bounds(ratio: float, min_ratio=0.2, max_ratio=5) -> bool:
    return min_ratio <= ratio <= max_ratio
