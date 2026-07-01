# Translating Gradia

Thank you for your interest in translating Gradia! This guide will help you contribute translations to make Gradia accessible to more users around the world.

## Getting Started

1. **Fork the Gradia repository** and clone it on your local computer.

2. Locate the `po/` directory and search for existing translations for the target language (e.g., `po/fr.po` for French, `po/nl.po` for Dutch).

3. Add new or update existing translations by following these steps:

#### a) Add new language translations

1. Locate the translation template file, located in `po/gradia.pot`.

2. Open the `gradia.pot` file in [Poedit](https://poedit.net/).

3. In Poedit, create a new translation by selecting the target language. Poedit will generate a new `.po` file for that language.

4. Save the new `.po` file in the `po/` directory, using the two-letter [ISO 639-1 language code](https://en.wikipedia.org/wiki/List_of_ISO_639_language_codes), e.g., `fr.po`, `de.po`, or `nl.po`.

   To specify a specific dialect, use an underscore to combine the language code with the region code (the [two-letter ISO 3166-1 code](https://en.wikipedia.org/wiki/ISO_3166-1_alpha-2), capitalized), e.g., `fr_FR.po` for French spoken in France or `fr_CA.po` for French spoken in Canada.

6. Add the same code to the `po/LINGUAS` file to register your translation.

#### b) Update existing language translations

1. Locate the translation file for the target language, located in `po/${target_language}.po`.

2. Open this `.po` file in [Poedit](https://poedit.net/).

4. In Poedit, you can view and edit existing translations.

5. Simply save the updated `.po` file, replacing the old one in the `po/` directory.

## Translating

* Use Poedit's interface to translate each message carefully, some entries will have notes/comments attached to them.
* **Note the `_` characters** in the messages – they are used by the application to define mnemonics (keyboard shortcuts);
  
  e.g., the message `"_Padding"` will be displayed as `<u>P</u>adding`, and the user will be able to activate the associated button/option/field by pressing `Alt`+`P`.
* Poedit may sometimes generate a `.mo` file, but this file is not needed because it is already generated when building the app.

## Testing

If your system is not set to the target language, the Builder launch command ignores this setting and launches in English, or you simply want to preview the English version for reference, 
you can force the app to run in the specified language using the following environment variable:

```json
"--env=LANGUAGE=en"
```

To apply this in a more permanent fashion, add it under the `finish-args` section of `build-aux/flatpak/be.alexandervanhee.gradia.Devel.json` before building the app.

## Submitting Your Translation

1. Commit your `.po` file (and the updated `po/LINGUAS` file if a new language was added).
2. Push the changes to your fork.
3. Open a Pull Request against the main Gradia repository with a title beginning with `i18n:`.


---

Thank you for helping make Gradia multilingual!
