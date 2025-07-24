import pytesseract
from PIL import Image
import os

class OCR:

    def __init__(self):
        pass

    def extract_text(self, file_path):

        try:
            if not os.path.exists(file_path):
                raise FileNotFoundError(f"File not found: {file_path}")

            image = Image.open(file_path)

            extracted_text = pytesseract.image_to_string(image)

            return extracted_text.strip()

        except FileNotFoundError:
            raise
        except Exception as e:
            raise Exception(f"OCR processing failed: {str(e)}")

