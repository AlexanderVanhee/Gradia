# Copyright (C) 2026 Wilder Chavez
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

def segment_intersects_rect(x1: float, y1: float, x2: float, y2: float,
                            rect: tuple[float, float, float, float]) -> bool:
    min_x, min_y, max_x, max_y = rect
    dx, dy = x2 - x1, y2 - y1
    t0, t1 = 0.0, 1.0
    for p, q in ((-dx, x1 - min_x), (dx, max_x - x1), (-dy, y1 - min_y), (dy, max_y - y1)):
        if p == 0:
            if q < 0:
                return False
            continue
        t = q / p
        if p < 0:
            t0 = max(t0, t)
        else:
            t1 = min(t1, t)
        if t0 > t1:
            return False
    return True


def polyline_intersects_rect(points: list[tuple[float, float]], rect: tuple[float, float, float, float],
                             padding: float) -> bool:
    if not points:
        return False
    min_x, min_y, max_x, max_y = rect
    padded = (min_x - padding, min_y - padding, max_x + padding, max_y + padding)
    if len(points) == 1:
        return segment_intersects_rect(*points[0], *points[0], padded)
    return any(segment_intersects_rect(x1, y1, x2, y2, padded)
               for (x1, y1), (x2, y2) in zip(points, points[1:]))
