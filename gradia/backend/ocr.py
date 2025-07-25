import pytesseract
from PIL import Image
import os
from gradia.app_constants import TESSDATA_DIR

class OCR:
    def __init__(self):
        self.tessdata_dir = TESSDATA_DIR

    def extract_text(self, file_path, primary_lang='eng', secondary_lang=None):
        try:
            if not os.path.exists(file_path):
                raise FileNotFoundError(f"File not found: {file_path}")

            image = Image.open(file_path)
            config = f'--tessdata-dir "{self.tessdata_dir}"'

            if secondary_lang:
                lang = f"{primary_lang}+{secondary_lang}"
            else:
                lang = primary_lang

            extracted_text = pytesseract.image_to_string(image, lang=lang, config=config)
            return extracted_text.strip()

        except FileNotFoundError:
            raise
        except Exception as e:
            raise Exception(f"OCR processing failed: {str(e)}")
