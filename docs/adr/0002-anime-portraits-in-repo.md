# Official anime portraits are kept in the repo

Off the clock uses official character art (Zero Two, Rem, Megumi, Kaneki) from AniList. We keep it, accepting that the art belongs to its rights holders and could draw a takedown. The images are stored downscaled in `assets/anime/` instead of fetched at build time, so an AniList outage can no longer stop the Clock and City from updating.

## Considered Options

- Fetch from AniList each build (old way): one CDN failure broke every image.
- Skip the panel when the fetch fails: still depends on the CDN.
- Hotlink `<img>` tags in the README: no art in the repo, but loses the styled panel.
- Remove the art: rejected; the anime is part of who the profile is for (ADR 0001).
