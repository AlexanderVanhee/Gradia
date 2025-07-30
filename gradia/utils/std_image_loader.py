import sys
import os
import shutil
from pathlib import Path

from PIL import Image
from io import BytesIO

from typing import Optional
from gradia.backend.logger import Logger
from gradia.utils.timestamp_filename import TimestampedFilenameGenerator
logging = Logger()

class StdinImageLoader:
    def __init__(self):
        self.temp_path: Optional[str] = None

    def get_flatpak_safe_temp_dir(self) -> str:
        xdg_cache_home = os.environ.get("XDG_CACHE_HOME") or os.path.expanduser("~/.cache")
        temp_dir = os.path.join(xdg_cache_home, "gradia", "stdin")
        os.makedirs(temp_dir, exist_ok=True)
        return temp_dir

    def read_from_stdin(self) -> Optional[str]:
        if sys.stdin.isatty():
            return None

        try:
            logging.debug("Reading image from stdin...")
            image_data = sys.stdin.buffer.read()
            if not image_data:
                raise ValueError("No image data received from stdin.")

            image = Image.open(BytesIO(image_data))
            image.load()

            temp_dir = self.get_flatpak_safe_temp_dir()
            filename = TimestampedFilenameGenerator().generate(_("Edited Image From %Y-%m-%d %H-%M-%S")) + ".png"
            temp_path = os.path.join(temp_dir, filename)
            Path(temp_dir).mkdir(parents=True, exist_ok=True)

            image.save(temp_path)
            self.temp_path = temp_path

            logging.info(f"Temporary image file written to: {self.temp_path}")

            return self.temp_path

        except Exception as e:
            logging.critical("Failed to read image from stdin.", exception=e, show_exception=True)
            return None
