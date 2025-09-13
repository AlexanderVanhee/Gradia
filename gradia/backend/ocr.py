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

import pytesseract
from PIL import Image
import os

class OCR:
    def __init__(self):
        self.tesseract_cmd = "/app/extensions/ocr/bin/tesseract"
        self.tessdata_dir = "/app/extensions/ocr/share/tessdata"
        pytesseract.pytesseract.tesseract_cmd = self.tesseract_cmd

    @staticmethod
    def is_available():
        return os.path.exists("/app/extensions/ocr/bin/tesseract")

    def extract_text(self, image, primary_lang="eng", secondary_lang=None):
        try:
            config = f'--tessdata-dir "{self.tessdata_dir}"'
            lang = f"{primary_lang}+{secondary_lang}" if secondary_lang else primary_lang
            extracted_text = pytesseract.image_to_string(
                image,
                lang=lang,
                config=config
            )
            return extracted_text.strip()
        except FileNotFoundError:
            raise
        except Exception as e:
            raise Exception(f"OCR processing failed: {str(e)}")

