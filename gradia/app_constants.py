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
from gradia.graphics.gradient import Gradient

GradientPreset = tuple[str, str, int]

PREDEFINED_GRADIENTS: list[Gradient] = [
    Gradient(
        mode="linear",
        steps=[(0.0, "#f66151"), (1.0, "#ed333b")],
        angle=45
    ),
    Gradient(
        mode="linear",
        steps=[(0.0, "#ff5f6d"), (1.0, "#ffc371")],
        angle=45
    ),
    Gradient(
        mode="linear",
        steps=[(0.0, "#ffd200"), (1.0, "#f7971e")],
        angle=135
    ),
    Gradient(
        mode="linear",
        steps=[(0.0, "#DFFFCD"), (0.48, "#90F9C4"), (1.0, "#39F3BB")],
        angle=135
    ),
    Gradient(
        mode="linear",
        steps=[(0.0, "#57e389"), (1.0, "#3584e4")],
        angle=135
    ),
    Gradient(
        mode="linear",
        steps=[(0.0, "#23d4fd"), (0.5, "#3a98f0"), (1.0, "#b721ff")],
        angle=45
    ),
]

SUPPORTED_EXPORT_FORMATS = {
    'png': {
        'name': _('PNG Image (*.png)'),
        'shortname' : 'PNG',
        'mime_type': 'image/png',
        'extensions': ['.png'],
        'save_options': {'keys': [], 'values': []}
    },
    'jpeg': {
        'name': _('JPEG Image (*.jpg)'),
        'shortname' : 'JPEG',
        'mime_type': 'image/jpeg',
        'extensions': ['.jpg', '.jpeg'],
        'save_options': {'keys': ['quality'], 'values': ['90']}
    },
    'webp': {
        'name': _('WebP Image (*.webp)'),
        'shortname' : 'WebP',
        'mime_type': 'image/webp',
        'extensions': ['.webp'],
        'save_options': {'keys': ['quality'], 'values': ['90']}
    }
}

DEFAULT_EXPORT_FORMAT = 'jpeg'
