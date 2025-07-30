from datetime import datetime

class TimestampedFilenameGenerator:
    def __init__(self):
        return

    def generate(self, pattern) -> str:
        return datetime.now().strftime(pattern)

