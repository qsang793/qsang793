# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

## Users
Fellow developers and friends who open Sang's profile page to get a feel for who he is: what he works on and what he is like off the clock. They skim it in seconds, on desktop or on a phone. Recruiters are not the primary reader (docs/adr/0001).

## Product Purpose
A profile README that shows a person, not a CV. Success is a visitor who remembers the theme and leaves knowing roughly what Sang builds (agents, developer tools, humanoid robot simulation) and what he likes.

## Positioning
The whole profile is told through one theme, 死に戻り (Return by Death): die, come back, try again. The Clock, the City and the rewinding intro are drawn from his own contribution data, so nobody else's profile can carry them unchanged.

## Operating Context
- Two profiles share the same drawing code: this personal one on GitHub (qsang793/qsang793) and the work one on the company GitLab (git.soc.one/sangnq/sangnq). A drawing change is copied by hand to both.
- The README is sanitized markdown: no CSS or JS. Every section is an SVG image drawn by `scripts/build_profile.py` and published daily by CI to the `output` branch.
- SVGs render through `<img>`: internal CSS and animation work, nothing is clickable or loads externally, fonts are not guaranteed (kanji are outlines in `scripts/glyphs.json`).
- GitHub picks the light or dark file through `<picture>`; the GitLab copy puts both themes in one SVG because GitLab strips `<picture>`.
- Images are drawn on an 846-unit column and shrink to about 0.4 on a phone; below 600px rendered width they switch to larger text.

## Capabilities and Constraints
- Sections: Clock, intro (one-liners typed and rewound), Stack, City (Activity), Off the clock (anime). Terms as defined in GLOSSARY.md.
- Contributions come from the GitHub GraphQL API (the GitLab copy uses GitLab's calendar.json). Only the past year is available.
- Anime portraits are official art kept downscaled in `assets/anime/`, an accepted takedown risk (docs/adr/0002).
- Subaru's City frames are renders of a fan VRM model kept in `assets/subaru/`; the model itself is never committed (docs/adr/0003).
- CI runs stdlib Python only; anything needing a library is precomputed into the repo.

## Brand Commitments
- Display name: Sang Nguyen.
- The 死に戻り theme and its vocabulary (Loop, Clock, City, Off the clock).
- Personality leads; there is no "Selected work" section in the README (docs/adr/0001).

## Evidence on Hand
- Contribution calendar for the past year (live, from the API).
- Stack list and Simple Icons paths in `scripts/icons.json`.
- Four anime portraits in `assets/anime/`.
- No testimonials, metrics or project write-ups exist in the README; do not invent them.

## Product Principles
1. One theme, carried everywhere: every section is a variation on the loop.
2. Drawn from real data where data exists; never fake numbers.
3. Personality first, work signal second, and never a CV.
4. Readable everywhere the README is read: phone, desktop, either theme, no installed fonts.

## Accessibility & Inclusion
- Every image carries descriptive alt text that includes its words (jokes, quotes, stack names).
- Animation honors `prefers-reduced-motion`.
- Small text meets WCAG AA on its panel in both themes; text stays readable at 375px.
