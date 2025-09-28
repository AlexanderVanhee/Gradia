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
from dataclasses import dataclass
from typing import List, ClassVar
gi.require_version("Soup", "3.0")
from gi.repository import Soup, GLib, Gio
from pathlib import Path
from gradia.backend.logger import Logger
from gradia.backend.settings import Settings
from gradia.constants import app_id
from gradia.constants import ocr_tesseract_cmd, ocr_original_tessdata


logger = Logger()

@dataclass(frozen=True)
class OCRModel:
    code: str
    name: str
    size: int

class OCR:
    DOWNLOADABLE_MODELS: ClassVar[List[OCRModel]] = [
        OCRModel("eng", _("English"), 15400601),
        OCRModel("chi_sim", _("Chinese Simplified"), 13077423),
        OCRModel("chi_tra", _("Chinese Traditional"), 12985735),
        OCRModel("spa", _("Spanish"), 13570187),
        OCRModel("fra", _("French"), 3972885),
        OCRModel("fas", _("Persian"), 3325955),
        OCRModel("deu", _("German"), 8628461),
        OCRModel("jpn", _("Japanese"), 14330109),
        OCRModel("ara", _("Arabic"), 12603724),
        OCRModel("rus", _("Russian"), 15301764),
        OCRModel("por", _("Portuguese"), 8159939),
        OCRModel("ita", _("Italian"), 8863635),
        OCRModel("kor", _("Korean"), 12528128),
        OCRModel("hin", _("Hindi"), 11895564),
        OCRModel("nld", _("Dutch"), 8903736),
        OCRModel("tur", _("Turkish"), 7456265),
        OCRModel("kaz", _("Kazakh"), 7528853),
        OCRModel("oci", _("Occitan"), 12917692),
        OCRModel("pol", _("Polish"), 11978867),
        OCRModel("ukr", _("Ukrainian"), 10859081),
        OCRModel("tel", _("Telugu"), 9098795)
    ]

    def __init__(self, window=None):
        self.tesseract_cmd = ocr_tesseract_cmd
        self.original_tessdata_dir = ocr_original_tessdata
        self.user_tessdata_dir = os.path.expanduser(f"~/.var/app/{app_id}/data/tessdata")
        self.window = window

        pytesseract.pytesseract.tesseract_cmd = self.tesseract_cmd
        self._session = None
        self.settings = Settings()

        self._update_ocr_action_state()

    def _update_ocr_action_state(self):
        if self.window:
            available = Path(ocr_tesseract_cmd).exists() and len(self.get_installed_models()) > 0
            ocr_action = self.window.lookup_action("ocr")
            if ocr_action and hasattr(ocr_action, 'set_state'):
                ocr_action.set_state(GLib.Variant.new_boolean(available))

    def get_current_model(self):
        return self.settings.trained_data

    def set_current_model(self, model_code: str):
        if self.is_model_installed(model_code):
            self.settings.trained_data = model_code
            logger.info(f"Setting current OCR model to: {model_code}")
        else:
            logger.warning(f"Cannot set model {model_code}: not installed")
            raise ValueError(f"Model {model_code} is not installed")

    def extract_text(self, image, primary_lang):
        if not self.get_installed_models():
            raise RuntimeError("No OCR language models are available")

        if not self.is_model_installed(primary_lang):
            raise RuntimeError(f"OCR language model '{primary_lang}' is not installed")

        self.set_current_model(primary_lang)

        try:
            tessdata_dir = self._get_tessdata_dir_for_lang(primary_lang)
            config = f'--tessdata-dir "{tessdata_dir}"'
            lang = primary_lang
            if self.is_model_installed("eng") and primary_lang != "eng":
                lang = f"{primary_lang}+eng"

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

        for path in [self.original_tessdata_dir, self.user_tessdata_dir]:
            p = Path(path)
            if p.exists():
                for file in p.glob("*.traineddata"):
                    if file.stem != "osd":
                        installed.add(file.stem)

        return sorted(list(installed))

    def get_downloadable_models(self) -> List[OCRModel]:
        return list(self.DOWNLOADABLE_MODELS)

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
                    logger.info(f"saving to  {output_path} ")

                logger.info(f"Downloaded OCR model: {model_code}")
                self.set_current_model(model_code)
                self._update_ocr_action_state()

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
        user_model_path = Path(self.user_tessdata_dir) / f"{model_code}.traineddata"

        if user_model_path.exists():
            user_model_path.unlink()
            logger.info(f"Deleted OCR model: {model_code}")

            if self.get_current_model() == model_code:
                available_models = self.get_installed_models()
                if available_models:
                    self.set_current_model(available_models[0])

            self._update_ocr_action_state()
            return True
        else:
            logger.warning(f"OCR model not found: {model_code}")
            return False
