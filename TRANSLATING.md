# Translating Gradia

Thank you for your interest in translating Gradia! This guide will help you contribute translations to make Gradia accessible to more users around the world.

## Getting Started

1. **Fork the Gradia repository** and clone it to your local machine.

2. Locate the translation template file, found at `po/gradia.pot`.

3. Open the `gradia.pot` file in [Poedit](https://poedit.net/).

4. In Poedit, create a new translation by selecting your target language. Poedit will generate a new `.po` file for that language.

5. Save the new `.po` file in the `po/` directory, following the naming convention for your language code, e.g., `fr.po`, `de.po`, or `nl.po`.

6. Add your language code to the `po/LINGUAS` file to register your translation.

## Translating

* Use Poedit's interface to translate each message carefully, some entries will have notes/comments attached to them.
* Poedit may sometimes generate a `.mo` file, but this file is not needed because it is already generated when building the app.

## Testing

If your system is not set to the target language or you want to preview the English version for reference, 
you can force the app to run in English using the following environment variable:

```json
"--env=LANGUAGE=en"
```

To apply this in a more permanent fashion, add it under the `finish-args` section of `build-aux/be.alexandervanhee.gradia.Devel.json` before building the app.

## Submitting Your Translation

1. Commit your `.po` file and the updated `po/LINGUAS` file.
2. Push the changes to your fork.
3. Open a Pull Request against the main Gradia repository with a title beginning with `i18n:`.


---

Thank you for helping make Gradia multilingual!
