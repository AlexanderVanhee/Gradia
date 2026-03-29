#!/usr/bin/env python3
import json
import sys
import urllib.request
from pathlib import Path

try:
    from babel import Locale
    from babel.core import UnknownLocaleError
except ImportError:
    print("Error: babel library not found. Install it with: pip install babel")
    sys.exit(1)

verbose = False

def log(msg):
    if verbose:
        print(msg)

def read_linguas(linguas_path):
    languages = []
    with open(linguas_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#"):
                languages.append(line)
    return languages

def fetch_tessdata_files():
    url = "https://api.github.com/repos/tesseract-ocr/tessdata_best/git/trees/main?recursive=1"
    req = urllib.request.Request(url, headers={"Accept": "application/vnd.github+json", "User-Agent": "tessdata-script"})
    with urllib.request.urlopen(req) as r:
        data = json.loads(r.read().decode())
    files = {}
    for item in data.get("tree", []):
        if item["type"] != "blob":
            continue
        path = item["path"]
        if not path.endswith(".traineddata"):
            continue
        if "/" in path:
            continue
        code = path.replace(".traineddata", "")
        if "_vert" in code:
            continue
        files[code] = item["size"]
    return files

SKIP = {
    "osd", "equ",
    "enm", "frm", "grc", "ita_old", "spa_old", "kat_old", "deu_latf",
    "epo", "san", "lat", "chr", "dzo", "iku", "ton", "que", "mri",
    "srp_latn", "aze_cyrl", "uzb_cyrl",
}

LOCALE_OVERRIDES = {
    "chi_sim": "zh_Hans",
    "chi_tra": "zh_Hant",
    "srp_latn": "sr_Latn",
    "uzb_cyrl": "uz_Cyrl",
    "aze_cyrl": "az_Cyrl",
}

ISO3_TO_ISO1 = {
    "afr": "af", "amh": "am", "ara": "ar", "asm": "as", "aze": "az",
    "bel": "be", "ben": "bn", "bod": "bo", "bos": "bs", "bre": "br",
    "bul": "bg", "cat": "ca", "ceb": "ceb","ces": "cs", "chr": "chr",
    "cos": "co", "cym": "cy", "dan": "da", "deu": "de", "div": "dv",
    "dzo": "dz", "ell": "el", "eng": "en", "enm": "en", "epo": "eo",
    "est": "et", "eus": "eu", "fao": "fo", "fas": "fa", "fil": "fil",
    "fin": "fi", "fra": "fr", "frm": "fr", "fry": "fy", "gla": "gd",
    "gle": "ga", "glg": "gl", "grc": "el", "guj": "gu", "hat": "ht",
    "heb": "he", "hin": "hi", "hrv": "hr", "hun": "hu", "hye": "hy",
    "iku": "iu", "ind": "id", "isl": "is", "ita": "it", "jav": "jv",
    "jpn": "ja", "kan": "kn", "kat": "ka", "kaz": "kk", "khm": "km",
    "kir": "ky", "kmr": "ku", "kor": "ko", "lao": "lo", "lat": "la",
    "lav": "lv", "lit": "lt", "ltz": "lb", "mal": "ml", "mar": "mr",
    "mkd": "mk", "mlt": "mt", "mon": "mn", "mri": "mi", "msa": "ms",
    "mya": "my", "nep": "ne", "nld": "nl", "nor": "no", "oci": "oc",
    "ori": "or", "pan": "pa", "pol": "pl", "por": "pt", "pus": "ps",
    "que": "qu", "ron": "ro", "rus": "ru", "san": "sa", "sin": "si",
    "slk": "sk", "slv": "sl", "snd": "sd", "spa": "es", "sqi": "sq",
    "srp": "sr", "sun": "su", "swa": "sw", "swe": "sv", "syr": "syr",
    "tam": "ta", "tat": "tt", "tel": "te", "tgk": "tg", "tha": "th",
    "tir": "ti", "ton": "to", "tur": "tr", "uig": "ug", "ukr": "uk",
    "urd": "ur", "uzb": "uz", "vie": "vi", "yid": "yi", "yor": "yo",
}

def make_locale(code):
    parts = code.split("_")
    try:
        if len(parts) == 3:
            return Locale(parts[0], script=parts[1], territory=parts[2])
        elif len(parts) == 2:
            try:
                return Locale(parts[0], script=parts[1])
            except Exception:
                return Locale(parts[0], territory=parts[1])
        else:
            return Locale(parts[0])
    except UnknownLocaleError:
        return None

def normalize_ui_lang(lang_code):
    manual = {"zh_CN": "zh_Hans_CN", "zh_TW": "zh_Hant_TW"}
    return make_locale(manual.get(lang_code, lang_code))

def resolve_tess_locale(tess_code):
    if tess_code in LOCALE_OVERRIDES:
        return make_locale(LOCALE_OVERRIDES[tess_code])
    base = tess_code.split("_")[0]
    iso1 = ISO3_TO_ISO1.get(base)
    if not iso1:
        return None
    return make_locale(iso1)

def get_english_name(tess_code):
    tess_locale = resolve_tess_locale(tess_code)
    if tess_locale is None:
        return tess_code
    en = Locale("en")
    name = en.languages.get(tess_locale.language, tess_code)
    if tess_code == "chi_sim":
        name += f" ({en.scripts.get('Hans', 'Simplified')})"
    elif tess_code == "chi_tra":
        name += f" ({en.scripts.get('Hant', 'Traditional')})"
    return name

def get_language_name(tess_code, ui_locale):
    tess_locale = resolve_tess_locale(tess_code)
    if tess_locale is None:
        return get_english_name(tess_code)
    try:
        name = ui_locale.languages.get(tess_locale.language)
        if not name:
            return get_english_name(tess_code)
        if tess_code == "chi_sim":
            name += f" ({ui_locale.scripts.get('Hans', 'Simplified')})"
        elif tess_code == "chi_tra":
            name += f" ({ui_locale.scripts.get('Hant', 'Traditional')})"
        return name
    except Exception as e:
        log(f"Warning: {tess_code} in {ui_locale}: {e}")
        return get_english_name(tess_code)

def main():
    global verbose

    linguas_path = "../po/LINGUAS"
    output_path = "../data/models.json"

    if "--verbose" in sys.argv:
        verbose = True
        sys.argv.remove("--verbose")
    if len(sys.argv) > 1:
        linguas_path = sys.argv[1]
    if len(sys.argv) > 2:
        output_path = sys.argv[2]

    if not Path(linguas_path).exists():
        print(f"Error: LINGUAS file not found at {linguas_path}")
        sys.exit(1)

    languages = read_linguas(linguas_path)
    log(f"Found {len(languages)} UI languages: {', '.join(languages)}")

    log("Fetching tessdata_best file list from GitHub...")
    tessdata_files = fetch_tessdata_files()
    log(f"Found {len(tessdata_files)} traineddata files")

    ui_locales = {lang: normalize_ui_lang(lang) for lang in languages}

    result = {}
    for tess_code, size_bytes in sorted(tessdata_files.items()):
        if tess_code in SKIP:
            log(f"Skipping: {tess_code}")
            continue
        log(f"Processing: {tess_code} ({size_bytes} bytes)")
        translations = {}
        for lang, ui_locale in ui_locales.items():
            if ui_locale is None:
                translations[lang] = get_english_name(tess_code)
            else:
                translations[lang] = get_language_name(tess_code, ui_locale)
        result[tess_code] = {
            "english_name": get_english_name(tess_code),
            "size_bytes": size_bytes,
            "translations": translations,
        }

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, separators=(",", ":"))

    print(f"Saved {len(result)} entries to {output_path}")

if __name__ == "__main__":
    main()
