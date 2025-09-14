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
import os
import gi
gi.require_version("Soup", "3.0")
from gi.repository import Soup, GLib, Gio
from pathlib import Path
from gradia.backend.logger import Logger
from gradia.backend.settings import Settings
from gradia.constants import app_id

logger = Logger()

class OCR:
    def __init__(self):
        self.tesseract_cmd = "/app/extensions/ocr/bin/tesseract"
        self.original_tessdata_dir = "/app/extensions/ocr/share/tessdata"
        self.user_tessdata_dir = os.path.expanduser(f"~/.var/app/{app_id}/data/tessdata")
        pytesseract.pytesseract.tesseract_cmd = self.tesseract_cmd
        self._session = None
        self.settings = Settings()

    @staticmethod
    def is_available():
        return os.path.exists("/app/extensions/ocr/bin/tesseract")

    def get_current_model(self):
        return self.settings.trained_data

    def set_current_model(self, model_code: str):
        if self.is_model_installed(model_code):
            self.settings.trained_data = model_code
            logger.info(f"Set current OCR model to: {model_code}")
        else:
            logger.warning(f"Cannot set model {model_code}: not installed")
            raise ValueError(f"Model {model_code} is not installed")

    def extract_text(self, image, primary_lang="eng", secondary_lang="eng"):
        self.set_current_model(primary_lang)
        try:
            tessdata_dir = self._get_tessdata_dir_for_lang(primary_lang)
            config = f'--tessdata-dir "{tessdata_dir}"'
            lang = f"{primary_lang}+{secondary_lang}"
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

    def _get_tessdata_dir_for_lang(self, lang_code):
        user_model_path = Path(self.user_tessdata_dir) / f"{lang_code}.traineddata"
        if user_model_path.exists():
            return self.user_tessdata_dir
        return self.original_tessdata_dir

    def get_installed_models(self):
        installed = set()

        original_path = Path(self.original_tessdata_dir)
        if original_path.exists():
            for file in original_path.glob("*.traineddata"):
                model_code = file.stem
                if model_code != "osd":
                    installed.add(model_code)

        user_path = Path(self.user_tessdata_dir)
        if user_path.exists():
            for file in user_path.glob("*.traineddata"):
                model_code = file.stem
                if model_code != "osd":
                    installed.add(model_code)

        return sorted(list(installed))

    def get_downloadable_models(self):
        return [
            {"code": "eng", "name": _("English")},
            {"code": "chi_sim", "name": _("Chinese Simplified")},
            {"code": "chi_tra", "name": _("Chinese Traditional")},
            {"code": "spa", "name": _("Spanish")},
            {"code": "fra", "name": _("French")},
            {"code": "deu", "name": _("German")},
            {"code": "jpn", "name": _("Japanese")},
            {"code": "ara", "name": _("Arabic")},
            {"code": "rus", "name": _("Russian")},
            {"code": "por", "name": _("Portuguese")},
            {"code": "ita", "name": _("Italian")},
            {"code": "kor", "name": _("Korean")},
            {"code": "hin", "name": _("Hindi")},
            {"code": "nld", "name": _("Dutch")},
            {"code": "tur", "name": _("Turkish")},
            {"code": "kaz", "name": _("Kazakh")},
            {"code": "oci", "name": _("Occitan")},
            {"code": "pol", "name": _("Polish")},
            {"code": "ukr", "name": _("Ukrainian")},
        ]

    def is_model_installed(self, model_code: str):
        return model_code in self.get_installed_models()

    def download_model(self, model_code: str, progress_callback=None):
        if not self._session:
            self._session = Soup.Session()

        url = f"https://github.com/tesseract-ocr/tessdata_best/raw/4.1.0/{model_code}.traineddata"
        output_path = Path(self.user_tessdata_dir) / f"{model_code}.traineddata"

        output_path.parent.mkdir(parents=True, exist_ok=True)

        message = Soup.Message.new("GET", url)

        def on_download_complete(session, result, user_data):
            try:
                glib_bytes = session.send_and_read_finish(result)
                if message.get_status() != Soup.Status.OK:
                    raise RuntimeError(f"HTTP error {message.get_status()}")

                raw_bytes = glib_bytes.get_data()

                with open(output_path, 'wb') as f:
                    f.write(raw_bytes)

                logger.info(f"Downloaded OCR model: {model_code}")
                self.set_current_model(model_code)

                if progress_callback:
                    GLib.idle_add(progress_callback, True, f"Downloaded {model_code}")

            except Exception as e:
                logger.error(f"Failed to download OCR model {model_code}: {e}")
                if progress_callback:
                    GLib.idle_add(progress_callback, False, str(e))

        self._session.send_and_read_async(
            message,
            GLib.PRIORITY_DEFAULT,
            None,
            on_download_complete,
            None
        )

    def delete_model(self, model_code: str):
        if model_code == "eng":
            raise ValueError("Cannot delete English model")

        user_model_path = Path(self.user_tessdata_dir) / f"{model_code}.traineddata"

        if user_model_path.exists():
            user_model_path.unlink()
            logger.info(f"Deleted OCR model: {model_code}")

            if self.get_current_model() == model_code:
                self.set_current_model("eng")

            return True
        else:
            logger.warning(f"OCR model not found: {model_code}")
            return False
