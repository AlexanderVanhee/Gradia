<p align="center">
  <img src="data/icons/hicolor/scalable/apps/be.alexandervanhee.gradia.svg" alt="Gradia Logo" height="128">
</p>

<h1 align="center">Gradia</h1>
<p align="center"><em>Make your screenshots ready for the world.</em></p>

<p align="center">
  On social media, it's often hard to control how your images appear to others.
  Transparent or oddly sized images—like screenshots—often don't display well.
  Fixing these issues can feel like more trouble than it's worth.
</p>

<p align="center">
  Gradia aims to alleviate that problem by allowing you to quickly edit images to address these issues,
  while also offering options to enhance their overall appearance.
</p>

<p align="center">
  <a href="https://flathub.org/apps/be.alexandervanhee.gradia">
    <img width="190" alt="Download on Flathub" src="https://flathub.org/api/badge?locale=en" />
  </a>
</p>


---

Gradia allows you to quickly modify screenshots of application windows to put them better in context.

> [!IMPORTANT]
> The [GNOME Code of Conduct](https://conduct.gnome.org) applies to this project, including this repository.
## Automatically Open the App After Taking a Screenshot

If you'd like Gradia to **open automatically** after taking a screenshot, you can set up a custom keyboard shortcut:

1. Go to **Settings** → **Keyboard** → **View and Customize Shortcuts** → **Custom Shortcuts**.
2. Click the **+** button to create a new shortcut.
3. Set the **Name** to something like *Open Gradia with Screenshot*.
4. For the **Command**, enter:

   ```
   flatpak run be.alexandervanhee.gradia --screenshot
   ```
5. Assign a keyboard shortcut of your choice (`Ctrl + Print` should be free by default).

## Screenshots

<p align="center">
  <img src="screenshots/showcase.webp" alt="Showcase screenshot" style="width:45%; margin-right: 5%;">
  <img src="screenshots/home.webp" alt="Home screenshot" style="width:45%;">
</p>
