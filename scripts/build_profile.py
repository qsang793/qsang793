#!/usr/bin/env python3
"""Draws the profile images: a year of contributions as a Return by Death clock.

Usage: GITHUB_TOKEN=... python3 scripts/build_profile.py dist
Images are drawn 1:1 for GitHub's 846px README column, in GitHub's own system font and Primer colors.
"""
import base64, json, math, os, pathlib, sys, urllib.request
from xml.sax.saxutils import escape, quoteattr

USER = "qsang793"
HERE = pathlib.Path(__file__).parent
ICONS = json.loads((HERE / "icons.json").read_text())
WIDTH = 846
# Primer tokens: fg.default, fg.muted, border.default, canvas.subtle, then the purple and severe scales.
THEMES = {
    "dark": dict(ink="#f0f6fc", soft="#9198a1", line="#3d444d", tile="#151b23", faint="#262c36", witch="#ab7df8", south="#8957e5", east="#6e40c9", now="#db6d28"),
    "light": dict(ink="#1f2328", soft="#59636e", line="#d1d9e0", tile="#f6f8fa", faint="#e6eaef", witch="#8250df", south="#6639ba", east="#512a97", now="#bc4c00"),
}
FONT = "-apple-system,BlinkMacSystemFont,'Segoe UI','Noto Sans',Helvetica,Arial,sans-serif"
CHARACTER_CDN = "https://s4.anilist.co/file/anilistcdn/character/large/"
# (quote, character, show, portrait); the first one gets the big panel.
ANIME = [
    ("Be my darling.", "Zero Two", "DARLING in the FRANXX", "b124381-2gAVq76HPfL2.png"),
    ("Let's start from zero.", "Rem", "Re:Zero", "b88575-Ayu8UPDA8NS6.png"),
    ("I save people unequally.", "Megumi", "Jujutsu Kaisen", "b126635-L0y3I92JSUkN.png"),
    ("What's 1000 minus 7?", "Kaneki", "Tokyo Ghoul", "b87275-mb13EWZBdbh3.png"),
]
# (label, Simple Icons slug); MuJoCo has no logo there, so it gets a monogram.
STACK = [
    ("Python", "python"), ("TypeScript", "typescript"), ("Go", "go"), ("Isaac Sim", "nvidia"),
    ("MuJoCo", None), ("ROS 2", "ros"), ("QEMU", "qemu"), ("Docker", "docker"),
    ("FastAPI", "fastapi"), ("Next.js", "nextdotjs"), ("Postgres", "postgresql"), ("Claude", "claude"),
]


def fetch_days():
    query = '{user(login:"%s"){contributionsCollection{contributionCalendar{totalContributions weeks{contributionDays{contributionCount}}}}}}' % USER
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
    days = [d["contributionCount"] for w in cal["weeks"] for d in w["contributionDays"]]
    # A short calendar means a bad response: fail so the last good image stays published.
    assert len(days) > 300, len(days)
    return cal["totalContributions"], days


def fetch_portraits():
    # Embedded as data URIs: an SVG inside <img> will not load anything external.
    out = []
    for *_, file in ANIME:
        req = urllib.request.Request(CHARACTER_CDN + file, headers={"User-Agent": USER})
        with urllib.request.urlopen(req, timeout=30) as res:
            out.append("data:image/png;base64," + base64.b64encode(res.read()).decode())
    return out


def svg(w, h, alt, body):
    return f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w:.0f} {h:.0f}" role="img" aria-label={quoteattr(alt)} font-family="{FONT}">
{body}
</svg>
'''


def text(s, x, y, size, fill, weight=400, anchor="start"):
    return f'<text x="{x:.1f}" y="{y:.1f}" font-size="{size}" font-weight="{weight}" fill="{fill}" text-anchor="{anchor}">{escape(s)}</text>'


def stack(c):
    gap, h = 8, 72
    w = (WIDTH - gap * (len(STACK) - 1)) / len(STACK)
    out = []
    for i, (label, slug) in enumerate(STACK):
        x = i * (w + gap)
        cx = x + w / 2
        out.append(f'<rect x="{x + .5:.1f}" y=".5" width="{w - 1:.1f}" height="{h - 1}" rx="6" fill="none" stroke="{c["line"]}"/>')
        if slug:
            out.append(f'<path transform="translate({cx - 12:.1f} 14)" fill="{c["ink"]}" d="{ICONS[slug]}"/>')
        else:
            out.append(text("MJ", cx, 33, 18, c["ink"], 600, "middle"))
        out.append(text(label, cx, 58, 11, c["soft"], anchor="middle"))
    alt = "Stack: " + ", ".join(label for label, _ in STACK) + "."
    return svg(WIDTH, h, alt, "".join(out))


def clock(days, c):
    cx = cy = 240
    r0 = 168
    top = max(days) or 1
    out = []
    for i, n in enumerate(days):
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
{"".join(out)}
<circle class="rewind" cx="{cx}" cy="{cy - r0 + 16}" r="6" fill="{c["now"]}"/>
{kanji}''')


def city(total, days, c):
    # One block per day: weeks run to the right, weekdays toward the viewer, height grows with contributions.
    top = max(days) or 1
    wx, wy, dx, dy = 15, 2.2, -6, 6
    head = 32
    blocks, ys = [], []
    for i, n in enumerate(days):
        w, d = divmod(i, 7)
        h = 2 + (44 * math.sqrt(n / top) if n else 0)
        x0, y0 = w * wx + d * dx, w * wy + d * dy
        mx, my = x0 + (wx + dx) / 2, y0 + (wy + dy) / 2
        # Shrink each footprint so the blocks read as separate buildings with streets between.
        base = [(mx + (x - mx) * 0.86, my + (y - my) * 0.86) for x, y in
                [(x0, y0), (x0 + wx, y0 + wy), (x0 + wx + dx, y0 + wy + dy), (x0 + dx, y0 + dy)]]
        blocks.append((d, w, base, h, n, i == len(days) - 1))
        ys += [y0 - h, y0 + wy + dy]
    xs = [7 * -dx + 2, len(days) // 7 * wx + wx + 2]
    pts = lambda p: " ".join(f"{x + xs[0]:.1f},{y - min(ys) + head:.1f}" for x, y in p)
    out = [text(f"{total} contributions in the last year", 0, 14, 14, c["soft"])]
    for d, w, (a, b, cc, e), h, n, today in sorted(blocks):
        up = lambda p: (p[0], p[1] - h)
        if n or today:
            out.append(f'<polygon points="{pts([e, cc, up(cc), up(e)])}" fill="{c["south"]}"/>')
            out.append(f'<polygon points="{pts([b, cc, up(cc), up(b)])}" fill="{c["east"]}"/>')
        fill = c["now"] if today else c["witch"] if n else c["faint"]
        out.append(f'<polygon points="{pts([up(a), up(b), up(cc), up(e)])}" fill="{fill}"/>')
    width, height = xs[0] + xs[1], max(ys) - min(ys) + head + 4
    alt = f"{total} contributions in the last year, drawn as an isometric city, one block per day. Taller blocks mean more contributions."
    return svg(width, height, alt, "".join(out))


def anime(portraits, c):
    h, gap, fw = 288, 8, 240
    rx, rw, rh = fw + gap, WIDTH - fw - gap, (h - 2 * gap) / 3
    pw = 72
    (quote, who, show, _), rest = ANIME[0], ANIME[1:]
    out = [
        '<defs><linearGradient id="scrim" x1="0" y1="0" x2="0" y2="1">'
        '<stop offset=".5" stop-color="#010409" stop-opacity="0"/><stop offset="1" stop-color="#010409" stop-opacity=".9"/></linearGradient>'
        f'<clipPath id="feature"><rect width="{fw}" height="{h}" rx="6"/></clipPath>',
    ]
    for i in range(len(rest)):
        y = i * (rh + gap)
        # Round only the left corners: the portrait sits at the start of its row.
        out.append(f'<clipPath id="p{i}"><path d="M{rx + 6} {y:.1f}H{rx + pw}V{y + rh:.1f}H{rx + 6}A6 6 0 0 1 {rx} {y + rh - 6:.1f}V{y + 6:.1f}A6 6 0 0 1 {rx + 6} {y:.1f}Z"/></clipPath>')
    out.append("</defs>")
    out.append(f'<g clip-path="url(#feature)"><image href="{portraits[0]}" width="{fw}" height="{h}" preserveAspectRatio="xMidYMin slice"/><rect width="{fw}" height="{h}" fill="url(#scrim)"/></g>')
    out.append(text(quote, 16, h - 38, 20, "#ffffff", 600))
    out.append(f'<text x="16" y="{h - 16}" font-size="12"><tspan fill="#ffffff">{escape(who)}</tspan><tspan fill="#ffffffaa" dx="6">{escape(show)}</tspan></text>')
    for i, ((quote, who, show, _), src) in enumerate(zip(rest, portraits[1:])):
        y = i * (rh + gap)
        tx = rx + pw + 16
        out.append(f'<rect x="{rx + .5}" y="{y + .5:.1f}" width="{rw - 1}" height="{rh - 1:.1f}" rx="6" fill="none" stroke="{c["line"]}"/>')
        out.append(f'<image href="{src}" x="{rx}" y="{y:.1f}" width="{pw}" height="{rh:.1f}" preserveAspectRatio="xMidYMin slice" clip-path="url(#p{i})"/>')
        out.append(text(quote, tx, y + rh / 2 - 2, 16, c["ink"]))
        out.append(f'<text x="{tx}" y="{y + rh / 2 + 18:.1f}" font-size="12"><tspan fill="{c["witch"]}">{escape(who)}</tspan><tspan fill="{c["soft"]}" dx="6">{escape(show)}</tspan></text>')
    alt = "Favorite anime, one line each: " + " ".join(f'"{q}" {who}, {show}.' for q, who, show, _ in ANIME)
    return svg(WIDTH, h, alt, "".join(out))


def main(out):
    out = pathlib.Path(out)
    out.mkdir(parents=True, exist_ok=True)
    total, days = fetch_days()
    portraits = fetch_portraits()
    for theme, c in THEMES.items():
        (out / f"clock-{theme}.svg").write_text(clock(days, c), encoding="utf-8")
        (out / f"city-{theme}.svg").write_text(city(total, days, c), encoding="utf-8")
        (out / f"stack-{theme}.svg").write_text(stack(c), encoding="utf-8")
        (out / f"anime-{theme}.svg").write_text(anime(portraits, c), encoding="utf-8")


if __name__ == "__main__":
    main(sys.argv[1])
