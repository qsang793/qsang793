#!/usr/bin/env python3
"""Draws the profile images: a year of contributions as a Return by Death clock.

Usage: GITHUB_TOKEN=... python3 scripts/build_profile.py dist
Images are drawn 1:1 for GitHub's 846px README column, in GitHub's own system font and Tokyo Night colors.
"""
import base64, json, math, os, pathlib, sys, urllib.request
from xml.sax.saxutils import escape, quoteattr

USER = "qsang793"
HERE = pathlib.Path(__file__).parent
ICONS = json.loads((HERE / "icons.json").read_text())
WIDTH, PAD = 846, 16
# Tokyo Night for dark, Tokyo Night Day for light (folke/tokyonight.nvim palettes).
THEMES = {
    "dark": dict(ink="#c0caf5", soft="#737aa2", line="#3b4261", canvas="#16161e", tile="#1a1b26", faint="#292e42", witch="#bb9af7", neon="#7aa2f7", south="#9d7cd8", east="#7058b8", now="#ff9e64"),
    "light": dict(ink="#3760bf", soft="#68709a", line="#a8aecb", canvas="#e9e9ed", tile="#e1e2e7", faint="#c4c8da", witch="#9854f1", neon="#2e7de9", south="#7847bd", east="#5f37a0", now="#b15c00"),
}
MINCHO = "'Hiragino Mincho ProN','Yu Mincho','Noto Serif CJK JP',serif"
FONT = "-apple-system,BlinkMacSystemFont,'Segoe UI','Noto Sans',Helvetica,Arial,sans-serif"
PORTRAITS = HERE.parent / "assets" / "anime"
# (quote, character, show, portrait); the first one gets the big panel.
# Portraits are kept in the repo, not fetched, so a CDN outage cannot stop the build (docs/adr/0002).
ANIME = [
    ("Be my darling.", "Zero Two", "DARLING in the FRANXX", "zero-two.jpg"),
    ("Let's start from zero.", "Rem", "Re:Zero", "rem.jpg"),
    ("I save people unequally.", "Megumi", "Jujutsu Kaisen", "megumi.jpg"),
    ("What's 1000 minus 7?", "Kaneki", "Tokyo Ghoul", "kaneki.jpg"),
]
# One line per loop: typed, held, then rewound before the next loop tries again.
LINES = [
    "My agents work while I sleep. That's the whole business plan.",
    "Hey Claude, build me an app. No mistakes.",
    "Vibe coding by day, vibe debugging by night.",
    "90% sleeping, 10% telling the AI it's wrong.",
    "Job title: engineer. Actual job: pressing Enter.",
    "My robot fell 3,000 times today. It's learning.",
]
MONO = "ui-monospace,SFMono-Regular,'SF Mono',Menlo,Consolas,'Liberation Mono',monospace"
# (label, Simple Icons slug); MuJoCo has no logo there, so it gets a monogram.
STACK = [
    ("Python", "python"), ("TypeScript", "typescript"), ("Go", "go"), ("Isaac Sim", "nvidia"),
    ("MuJoCo", None), ("ROS 2", "ros"), ("QEMU", "qemu"), ("Docker", "docker"),
    ("FastAPI", "fastapi"), ("Next.js", "nextdotjs"), ("Postgres", "postgresql"), ("Claude", "claude"),
]


def fetch_calendar():
    # GitHub's rolling last twelve months.
    query = '{user(login:"%s"){contributionsCollection{contributionCalendar{totalContributions weeks{contributionDays{weekday contributionCount}}}}}}' % USER
    req = urllib.request.Request(
        "https://api.github.com/graphql",
        json.dumps({"query": query}).encode(),
        {"Authorization": "bearer " + os.environ["GITHUB_TOKEN"], "Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=30) as res:
        body = json.load(res)
    if "errors" in body:
        raise RuntimeError(body["errors"])
    cal = body["data"]["user"]["contributionsCollection"]["contributionCalendar"]
    # (week, weekday, count): the window starts mid-week, so the weekday places each day.
    days = [(w, d["weekday"], d["contributionCount"]) for w, week in enumerate(cal["weeks"]) for d in week["contributionDays"]]
    # A short calendar means a bad response: fail so the last good image stays published.
    assert len(days) > 300, len(days)
    return cal["totalContributions"], days


def load_portraits():
    # Embedded as data URIs: an SVG inside <img> will not load anything external.
    return ["data:image/jpeg;base64," + base64.b64encode((PORTRAITS / file).read_bytes()).decode() for *_, file in ANIME]


def svg(w, h, alt, body):
    return f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w:.0f} {h:.0f}" role="img" aria-label={quoteattr(alt)} font-family="{FONT}">
{body}
</svg>
'''


def text(s, x, y, size, fill, weight=400, anchor="start"):
    return f'<text x="{x:.1f}" y="{y:.1f}" font-size="{size}" font-weight="{weight}" fill="{fill}" text-anchor="{anchor}">{escape(s)}</text>'


def panel(h, c, gx, gy):
    # The shared surface: a Tokyo Night canvas, a dot grid, magenta neon from one corner and blue from the opposite one.
    return (f'<defs><pattern id="dots" width="12" height="12" patternUnits="userSpaceOnUse"><circle cx="2" cy="2" r="1" fill="{c["line"]}"/></pattern>'
            f'<radialGradient id="glow" cx="{gx}" cy="{gy}" r=".7"><stop offset="0" stop-color="{c["witch"]}" stop-opacity=".22"/><stop offset="1" stop-color="{c["witch"]}" stop-opacity="0"/></radialGradient>'
            f'<radialGradient id="neon" cx="{1 - gx}" cy="{1 - gy}" r=".6"><stop offset="0" stop-color="{c["neon"]}" stop-opacity=".14"/><stop offset="1" stop-color="{c["neon"]}" stop-opacity="0"/></radialGradient></defs>'
            f'<rect width="{WIDTH}" height="{h:.0f}" rx="6" fill="{c["tile"]}"/>'
            f'<rect width="{WIDTH}" height="{h:.0f}" rx="6" fill="url(#dots)" opacity=".7"/>'
            f'<rect width="{WIDTH}" height="{h:.0f}" rx="6" fill="url(#glow)"/>'
            f'<rect width="{WIDTH}" height="{h:.0f}" rx="6" fill="url(#neon)"/>')


def stack(c):
    gap, th = 8, 72
    h = th + 2 * PAD
    w = (WIDTH - 2 * PAD - gap * (len(STACK) - 1)) / len(STACK)
    out = [panel(h, c, 0, 0)]
    for i, (label, slug) in enumerate(STACK):
        x = PAD + i * (w + gap)
        cx = x + w / 2
        out.append(f'<rect x="{x + .5:.1f}" y="{PAD + .5}" width="{w - 1:.1f}" height="{th - 1}" rx="6" fill="{c["canvas"]}" stroke="{c["line"]}"/>')
        if slug:
            out.append(f'<path transform="translate({cx - 12:.1f} {PAD + 14})" fill="{c["ink"]}" d="{ICONS[slug]}"/>')
        else:
            out.append(text("MJ", cx, PAD + 33, 18, c["ink"], 600, "middle"))
        # 10px keeps the longest label, TypeScript, inside its tile.
        out.append(text(label, cx, PAD + 58, 10, c["soft"], anchor="middle"))
    alt = "Stack: " + ", ".join(label for label, _ in STACK) + "."
    return svg(WIDTH, h, alt, "".join(out))


def intro(c):
    # Each loop types its line, holds it, then rewinds to the prompt: Return by Death as a terminal.
    # 20px keeps the longest line inside the 846px column.
    size, cw, h, y = 20, 12, 40, 28
    rows = [(f"#{i + 1} › ", s) for i, s in enumerate(LINES)]
    spans = [(0.05 * len(s), 2.4, 0.015 * len(s), 0.4) for _, s in rows]
    total = sum(map(sum, spans))
    css, out, t = [], [], 0.0
    for i, ((p, s), span) in enumerate(zip(rows, spans)):
        full, pre = (len(p) + len(s)) * cw, len(p) * cw
        marks = [t]
        for d in span:
            marks.append(marks[-1] + d)
        a, b, cc, d, e = (100 * m / total for m in marks)
        # Hidden goes two characters past the left edge so the cursor leaves the canvas too.
        hidden, prompt = f"translateX({-full - 2 * cw:.1f}px)", f"translateX({pre - full:.1f}px)"
        # One step per character, typing and rewinding alike.
        step = f"steps({len(s)},end)"
        css.append(f"@keyframes l{i}{{0%{{transform:{hidden};animation-timing-function:step-end}}"
                   f"{a:.3f}%{{transform:{prompt};animation-timing-function:{step}}}"
                   f"{b:.3f}%{{transform:none}}"
                   f"{cc:.3f}%{{transform:none;animation-timing-function:{step}}}"
                   f"{d:.3f}%{{transform:{prompt};animation-timing-function:step-end}}"
                   f"{e:.3f}%,100%{{transform:{hidden}}}}}")
        # Without animation (reduced motion), only the first loop shows, fully typed.
        anim = f'class="loop" style="animation-name:l{i}{";transform:" + hidden if i else ""}"'
        out.append(f'<clipPath id="c{i}"><rect {anim} width="{full:.1f}" height="{h}"/></clipPath>'
                   f'<text x="0" y="{y}" textLength="{full:.1f}" lengthAdjust="spacing" clip-path="url(#c{i})">'
                   f'<tspan fill="{c["witch"]}">{escape(p)}</tspan><tspan fill="{c["ink"]}">{escape(s)}</tspan></text>'
                   f'<g {anim}><rect class="cursor" x="{full + 2:.1f}" y="{y - size + 3}" width="{cw * .6:.1f}" height="{size + 2}" fill="{c["now"]}"/></g>')
        t = marks[-1]
    alt = "One-liners typed and rewound in a loop: " + " ".join(LINES)
    style = (f"<style>text{{font-family:{MONO};font-size:{size}px;white-space:pre}}"
             f".loop{{animation:{total:.2f}s infinite}}.cursor{{animation:blink 1s step-end infinite}}"
             "@keyframes blink{50%{opacity:0}}" + "".join(css) +
             "@media (prefers-reduced-motion:reduce){.loop,.cursor{animation:none}}</style>")
    return svg(WIDTH, h, alt, style + "".join(out))


def clock(days, c):
    cx = cy = 240
    r0 = 168
    top = max(n for *_, n in days) or 1
    out = []
    for i, (*_, n) in enumerate(days):
        a = 2 * math.pi * (i + 1) / len(days)
        r1 = r0 + 10 + (58 * math.sqrt(n / top) if n else 0)
        s, co = math.sin(a), math.cos(a)
        today = i == len(days) - 1
        color = c["now"] if today else c["witch"] if n else c["line"]
        out.append(f'<line x1="{cx + r0 * s:.1f}" y1="{cy - r0 * co:.1f}" x2="{cx + r1 * s:.1f}" y2="{cy - r1 * co:.1f}" stroke="{color}" stroke-width="{4 if today else 1.8}" stroke-linecap="round"/>')
    kanji = "".join(
        f'<text x="{cx}" y="{cy - 66 + i * 60}" text-anchor="middle" fill="{c["ink"]}">{ch}</text>'
        for i, ch in enumerate("死に戻り")
    )
    alt = "A clock with one tick per day of the past year, around the Japanese words shi ni modori, Return by Death."
    return svg(480, 480, alt, f'''<style>text{{font-family:"Hiragino Mincho ProN","Yu Mincho","Noto Serif CJK JP",serif;font-size:52px}}
.rewind{{transform-origin:{cx}px {cy}px;animation:rewind 60s linear infinite}}
@keyframes rewind{{to{{transform:rotate(-360deg)}}}}
@media (prefers-reduced-motion:reduce){{.rewind{{animation:none}}}}</style>
<defs><radialGradient id="halo"><stop offset=".55" stop-color="{c["witch"]}" stop-opacity=".22"/><stop offset="1" stop-color="{c["witch"]}" stop-opacity="0"/></radialGradient></defs>
<circle cx="{cx}" cy="{cy}" r="240" fill="url(#halo)"/>
{"".join(out)}
<circle class="rewind" cx="{cx}" cy="{cy - r0 + 16}" r="6" fill="{c["now"]}"/>
{kanji}''')


def iso(days, top, width, hmax, c, now=False, rise=False):
    """One block per day: weeks run to the right, weekdays toward the viewer, height grows with contributions.

    Returns the polygons, scaled to `width`, and their height.
    """
    weeks = days[-1][0] + 1
    k = width / (7 * 6 + weeks * 15)
    wx, wy, dx, dy = 15 * k, 2.2 * k, -6 * k, 6 * k
    blocks, ys = [], []
    for i, (w, d, n) in enumerate(days):
        h = 2 * k + (hmax * math.sqrt(n / top) if n else 0)
        x0, y0 = w * wx + d * dx, w * wy + d * dy
        mx, my = x0 + (wx + dx) / 2, y0 + (wy + dy) / 2
        # Shrink each footprint so the blocks read as separate buildings with streets between.
        base = [(mx + (x - mx) * 0.86, my + (y - my) * 0.86) for x, y in
                [(x0, y0), (x0 + wx, y0 + wy), (x0 + wx + dx, y0 + wy + dy), (x0 + dx, y0 + dy)]]
        blocks.append((d, w, base, h, n, now and i == len(days) - 1))
        ys += [y0 - h, y0 + wy + dy]
    pts = lambda p: " ".join(f"{x - 7 * dx:.1f},{y - min(ys):.1f}" for x, y in p)
    out = []
    for d, w, (a, b, cc, e), h, n, today in sorted(blocks):
        up = lambda p: (p[0], p[1] - h)
        if not n and not today:
            out.append(f'<polygon points="{pts([up(a), up(b), up(cc), up(e)])}" fill="{c["faint"]}"/>')
            continue
        # Built buildings rise week by week when the image loads.
        out.append(f'<g class="rise" style="animation-delay:{w * 0.03:.2f}s">' if rise else "<g>")
        out.append(f'<polygon points="{pts([e, cc, up(cc), up(e)])}" fill="{c["south"]}"/>')
        out.append(f'<polygon points="{pts([b, cc, up(cc), up(b)])}" fill="{c["east"]}"/>')
        out.append(f'<polygon points="{pts([up(a), up(b), up(cc), up(e)])}" fill="{c["now"] if today else c["witch"]}"/></g>')
    return "".join(out), max(ys) - min(ys)


def city(total, days, c):
    body, bh = iso(days, max(n for *_, n in days) or 1, WIDTH - 2 * PAD, 44, c, now=True, rise=True)
    head = 32
    h = PAD + head + bh + PAD
    out = [
        '<style>.rise{transform-box:fill-box;transform-origin:50% 100%;animation:rise .8s cubic-bezier(.16,1,.3,1) both}'
        '@keyframes rise{from{transform:scaleY(0)}}@media (prefers-reduced-motion:reduce){.rise{animation:none}}</style>',
        panel(h, c, 0, 1),
        # 不夜城, the city that never sleeps, sits in the empty corner above the later weeks.
        f'<text x="{WIDTH - PAD}" y="{PAD + 46}" font-family="{MINCHO}" font-size="48" fill="{c["line"]}" text-anchor="end">不夜城</text>',
        text(f"{total} contributions in the last year", PAD, PAD + 14, 14, c["soft"]),
        f'<g transform="translate({PAD} {PAD + head})">{body}</g>',
    ]
    alt = f"{total} contributions in the last year, drawn as an isometric city, one block per day. Taller blocks mean more contributions."
    return svg(WIDTH, h, alt, "".join(out))


def anime(portraits, c):
    ih, gap, fw = 288, 8, 240
    h = ih + 2 * PAD
    rx = PAD + fw + gap
    rw, rh = WIDTH - PAD - rx, (ih - 2 * gap) / 3
    pw = 72
    (quote, who, show, _), rest = ANIME[0], ANIME[1:]
    out = [
        panel(h, c, 1, 1),
        '<defs><linearGradient id="scrim" x1="0" y1="0" x2="0" y2="1">'
        '<stop offset=".5" stop-color="#010409" stop-opacity="0"/><stop offset="1" stop-color="#010409" stop-opacity=".9"/></linearGradient>'
        f'<clipPath id="feature"><rect x="{PAD}" y="{PAD}" width="{fw}" height="{ih}" rx="6"/></clipPath>',
    ]
    for i in range(len(rest)):
        y = PAD + i * (rh + gap)
        # Round only the left corners: the portrait sits at the start of its row.
        out.append(f'<clipPath id="p{i}"><path d="M{rx + 6} {y:.1f}H{rx + pw}V{y + rh:.1f}H{rx + 6}A6 6 0 0 1 {rx} {y + rh - 6:.1f}V{y + 6:.1f}A6 6 0 0 1 {rx + 6} {y:.1f}Z"/></clipPath>')
    out.append("</defs>")
    out.append(f'<g clip-path="url(#feature)"><image href="{portraits[0]}" x="{PAD}" y="{PAD}" width="{fw}" height="{ih}" preserveAspectRatio="xMidYMin slice"/><rect x="{PAD}" y="{PAD}" width="{fw}" height="{ih}" fill="url(#scrim)"/></g>')
    out.append(text(quote, PAD + 16, PAD + ih - 38, 20, "#ffffff", 600))
    out.append(f'<text x="{PAD + 16}" y="{PAD + ih - 16}" font-size="12"><tspan fill="#ffffff">{escape(who)}</tspan><tspan fill="#ffffffaa" dx="6">{escape(show)}</tspan></text>')
    for i, ((quote, who, show, _), src) in enumerate(zip(rest, portraits[1:])):
        y = PAD + i * (rh + gap)
        tx = rx + pw + 16
        out.append(f'<rect x="{rx + .5}" y="{y + .5:.1f}" width="{rw - 1}" height="{rh - 1:.1f}" rx="6" fill="{c["canvas"]}" stroke="{c["line"]}"/>')
        out.append(f'<image href="{src}" x="{rx}" y="{y:.1f}" width="{pw}" height="{rh:.1f}" preserveAspectRatio="xMidYMin slice" clip-path="url(#p{i})"/>')
        out.append(text(quote, tx, y + rh / 2 - 2, 16, c["ink"]))
        out.append(f'<text x="{tx}" y="{y + rh / 2 + 18:.1f}" font-size="12"><tspan fill="{c["witch"]}">{escape(who)}</tspan><tspan fill="{c["soft"]}" dx="6">{escape(show)}</tspan></text>')
    alt = "Favorite anime, one line each: " + " ".join(f'"{q}" {who}, {show}.' for q, who, show, _ in ANIME)
    return svg(WIDTH, h, alt, "".join(out))


def main(out):
    out = pathlib.Path(out)
    out.mkdir(parents=True, exist_ok=True)
    total, days = fetch_calendar()
    portraits = load_portraits()
    for theme, c in THEMES.items():
        (out / f"clock-{theme}.svg").write_text(clock(days, c), encoding="utf-8")
        (out / f"intro-{theme}.svg").write_text(intro(c), encoding="utf-8")
        (out / f"city-{theme}.svg").write_text(city(total, days, c), encoding="utf-8")
        (out / f"stack-{theme}.svg").write_text(stack(c), encoding="utf-8")
        (out / f"anime-{theme}.svg").write_text(anime(portraits, c), encoding="utf-8")


if __name__ == "__main__":
    main(sys.argv[1])
