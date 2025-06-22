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

from abc import ABC, abstractmethod

from PIL import Image

class Background(ABC):
    """
    Abstract base class for different backgrounds.

    All background implementations should inherit from this class
    and implement the required methods.
    """

    @abstractmethod
    def prepare_cairo_surface(self, width: int, height: int) -> Image.Image:
        """
        Prepare and return a Cairo surface with the background.

        Args:
            width (int): The target width
            height (int): The target height

        Returns:
            Image.Image: The background image
        """
        pass

    @abstractmethod
    def get_name(self) -> str:
        """
        Get a unique identifier for this background.

        Returns:
            str: A unique name for this background configuration
        """
        pass
