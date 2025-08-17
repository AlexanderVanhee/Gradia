# Gradia Website

The website is live at [gradia.alexandervanhee.be](https://gradia.alexandervanhee.be/)

### How to update base stylesheet
To get changes imported from `base.css` to the base stylesheet in real time during development, open a new terminal tab/window, make sure you are in `web/` directory and type:

```sh
npx @tailwindcss/cli -i assets/styles/base.css -o assets/styles/base-tailwind.css --watch
```

You can also import changes without having to run a watcher constantly in the background, just run the above command without the `--watch` option.
