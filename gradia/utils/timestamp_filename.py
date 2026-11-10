import os
import re
from datetime import datetime
from string import Formatter

class TimestampedFilenameGenerator:
    def __init__(self):
        return

    def generate(self, pattern) -> str:
        return datetime.now().strftime(pattern)


def _expand(pattern: str, now: datetime, counter: int | None) -> tuple[str, bool]:
    """Expand placeholders; with counter=None build a regex that captures {n} instead."""
    as_regex = counter is None
    parts = []
    has_counter = False
    for literal, field, spec, conversion in Formatter().parse(pattern):
        parts.append(re.escape(literal) if as_regex else literal)
        if field is None:
            continue
        if conversion:
            raise ValueError(f"Conversion not supported: {conversion}")
        if field == "n":
            has_counter = True
            parts.append(r"(\d+)" if as_regex else format(counter, spec))
        elif field in ("date", "time"):
            value = format(now.strftime("%Y-%m-%d" if field == "date" else "%H-%M-%S"), spec)
            parts.append(re.escape(value) if as_regex else value)
        else:
            raise KeyError(field)
    return "".join(parts), has_counter


def _next_counter(regex: str, folder: str) -> int:
    try:
        names = os.listdir(folder)
    except OSError:
        return 1
    numbers = [
        int(match.group(1))
        for name in names
        if (match := re.fullmatch(regex, os.path.splitext(name)[0]))
    ]
    return max(numbers, default=0) + 1


def format_filename_pattern(pattern: str, folder: str | None = None, now: datetime | None = None) -> str | None:
    """Expand {date}, {time}, {n} (with format spec, e.g. {n:03}) and strftime codes.

    {n} is one more than the highest number among files in folder that match the
    rest of the pattern, or 1 if there are none. Returns None if the pattern is
    invalid or expands to an empty name.
    """
    now = now or datetime.now()
    try:
        # A slash would turn the name into a path.
        pattern = now.strftime(pattern).replace("/", "-").strip()
        regex, has_counter = _expand(pattern, now, None)
        counter = _next_counter(regex, folder) if has_counter and folder else 1
        name = _expand(pattern, now, counter)[0].strip()
    except (ValueError, KeyError, IndexError):
        return None
    return name or None


if __name__ == "__main__":
    import tempfile

    t = datetime(2026, 11, 9, 14, 5, 7)
    assert format_filename_pattern("Shot {date} {time} {n}", None, t) == "Shot 2026-11-09 14-05-07 1"
    assert format_filename_pattern("{n:03}_%d.%m.%Y", None, t) == "001_09.11.2026"
    assert format_filename_pattern("a/b {n}", None, t) == "a-b 1"
    assert format_filename_pattern("{oops", None, t) is None
    assert format_filename_pattern("{unknown}", None, t) is None
    assert format_filename_pattern("{n!r}", None, t) is None
    assert format_filename_pattern("  ", None, t) is None

    with tempfile.TemporaryDirectory() as folder:
        for name in ["2026-11-09_001.png", "2026-11-09_007.jpg", "2026-11-08_012.png", "2026-11-09_x.png", "notes.txt"]:
            open(os.path.join(folder, name), "w").close()
        assert format_filename_pattern("{date}_{n:03}", folder, t) == "2026-11-09_008"
        assert format_filename_pattern("{date}_{n:03}", folder, datetime(2026, 11, 10)) == "2026-11-10_001"
        # Regex metacharacters in the pattern are literal.
        open(os.path.join(folder, "a.b (1).png"), "w").close()
        assert format_filename_pattern("a.b ({n})", folder, t) == "a.b (2)"
        assert format_filename_pattern("{n}", os.path.join(folder, "missing"), t) == "1"
    print("ok")
