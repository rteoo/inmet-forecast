# Project artwork

`inmet-forecast-icon.svg` is the icon's source: a cloud with rain and an orange
sun on a rounded navy tile. `inmet-forecast-icon.png` is its 1024-pixel render,
used by the repository README and the PyPI page. It is an independent project
mark and does not reproduce INMET's official identity.

The icon follows the personal-project icon family shared with
[homeassistantpy](https://github.com/rteoo/homeassistantpy) and
[bcbpy](https://github.com/rteoo/bcbpy): a navy tile graded through the Teô
Personal Design System's navy-500, navy-600 and navy-900, a pictogram in its
paper-100 to navy-300 gradient, and a single orange-500 accent, here the sun.
The SVG was drawn by hand on 2026-10-16, replacing the earlier generated raster.

To regenerate the PNG, render the SVG at 1024 by 1024 with a transparent
background, for example with headless Microsoft Edge:

```text
msedge --headless=new --disable-gpu --hide-scrollbars --default-background-color=00000000 --window-size=1024,1024 --screenshot=inmet-forecast-icon.png inmet-forecast-icon.svg
```
