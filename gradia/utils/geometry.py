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

import math


def distance_to_polyline_sq(px: float, py: float, points: list[tuple[float, float]]) -> float:
    if not points:
        return math.inf
    if len(points) == 1:
        return (px - points[0][0]) ** 2 + (py - points[0][1]) ** 2

    best = math.inf
    for (x1, y1), (x2, y2) in zip(points, points[1:]):
        seg_len_sq = (x2 - x1) ** 2 + (y2 - y1) ** 2
        if seg_len_sq == 0:
            t = 0.0
        else:
            t = max(0.0, min(1.0, ((px - x1) * (x2 - x1) + (py - y1) * (y2 - y1)) / seg_len_sq))
        cx = x1 + t * (x2 - x1)
        cy = y1 + t * (y2 - y1)
        best = min(best, (px - cx) ** 2 + (py - cy) ** 2)
    return best
