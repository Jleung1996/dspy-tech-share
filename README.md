# DSPy — Tech Share Deck

An interactive, self-contained slide deck for a DSPy tech-share session.

**Live site:** https://jleung1996.github.io/dspy-tech-share/

## About

Everything lives in a single `index.html` — no build step, no dependencies, no external
assets. The CSS and JavaScript (slide navigation, live DSPy weight/widget demos) are all
inlined, so the deck works offline: just open `index.html` in a browser.

## Local use

```bash
# clone, then open the file directly — that's it
start index.html
```

Navigate with the arrow keys; the on-slide widgets are interactive.

## Deployment

Served by GitHub Pages straight from the `main` branch root. Any push to `main`
republishes the site (usually within a minute).
