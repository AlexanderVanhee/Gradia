import pytesseract
from PIL import Image
import os

class OCR:

    def __init__(self):
        self.tessdata_dir = "/app/share/tessdata"

    def extract_text(self, file_path):
        try:
            if not os.path.exists(file_path):
                raise FileNotFoundError(f"File not found: {file_path}")

            image = Image.open(file_path)

            config = f'--tessdata-dir "{self.tessdata_dir}"'

            extracted_text = pytesseract.image_to_string(image, config=config)

            return extracted_text.strip()

        except FileNotFoundError:
            raise
        except Exception as e:
            raise Exception(f"OCR processing failed: {str(e)}")

