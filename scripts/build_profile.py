#!/usr/bin/env python3
"""Draws the profile images: a year of contributions as a Return by Death clock.

Usage: GITHUB_TOKEN=... python3 scripts/build_profile.py dist
Text is outlined from glyphs.json because an SVG inside <img> cannot load web fonts.
"""
import base64, json, math, os, pathlib, sys, urllib.request
from xml.sax.saxutils import quoteattr

USER = "qsang793"
HERE = pathlib.Path(__file__).parent
FONT = json.loads((HERE / "glyphs.json").read_text())
ICONS = json.loads((HERE / "icons.json").read_text())
THEMES = {
    "dark": dict(ink="#f1edf7", soft="#a9a1b8", witch="#b48cf0", faint="#332a44", tile="#1b1527", now="#ff7a45", south="#8a62cc", east="#6b45a8"),
    "light": dict(ink="#1b1524", soft="#5e5570", witch="#6d28d9", faint="#e4ddf0", tile="#f3eefa", now="#d9480f", south="#5b21b6", east="#4c1d95"),
}
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
    ("FastAPI", "fastapi"), ("Next.js", "nextdotjs"), ("PostgreSQL", "postgresql"), ("Claude", "claude"),
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


def text(s, x, y, size, fill, track=0.0):
    k = size / FONT["upm"]
    d, pen = [], x
    for ch in s:
        g = FONT["glyphs"][ch]
        for op, *a in g["d"]:
            pts = [f"{pen + a[i] * k:.1f} {y - a[i + 1] * k:.1f}" for i in range(0, len(a), 2)]
            d.append(op + " ".join(pts))
        pen += g["adv"] * k + track * size
    return f'<path fill="{fill}" d="{"".join(d)}"/>'


def measure(s, size, track=0.0):
    return sum(FONT["glyphs"][ch]["adv"] for ch in s) * size / FONT["upm"] + track * size * len(s)


def stack(c):
    cols, gap, w, h = 6, 16, (1200 - 5 * 16) / 6, 150
    out = []
    for i, (label, slug) in enumerate(STACK):
        x, y = (i % cols) * (w + gap), (i // cols) * (h + gap)
        cx = x + w / 2
        out.append(f'<rect x="{x:.1f}" y="{y}" width="{w:.1f}" height="{h}" rx="16" fill="{c["tile"]}"/>')
        if slug:
            out.append(f'<path transform="translate({cx - 28:.1f} {y + 26}) scale({56 / 24:.4f})" fill="{c["ink"]}" d="{ICONS[slug]}"/>')
        else:
            out.append(text("MJ", cx - measure("MJ", 48) / 2, y + 74, 48, c["ink"]))
        out.append(text(label, cx - measure(label, 28) / 2, y + 126, 28, c["soft"]))
    rows = -(-len(STACK) // cols)
    alt = "Stack: " + ", ".join(label for label, _ in STACK) + "."
    return f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1200 {rows * h + (rows - 1) * gap}" role="img" aria-label={quoteattr(alt)}>
{"".join(out)}
</svg>
'''


def ticks(days, cx, cy, r0, c):
    top = max(days) or 1
    out = []
    for i, n in enumerate(days):
        a = 2 * math.pi * (i + 1) / len(days)
        r1 = r0 + 10 + (58 * math.sqrt(n / top) if n else 0)
        s, co = math.sin(a), math.cos(a)
        today = i == len(days) - 1
        color = c["now"] if today else c["witch"] if n else c["faint"]
        width = 4 if today else 1.8
        out.append(f'<line x1="{cx + r0 * s:.1f}" y1="{cy - r0 * co:.1f}" x2="{cx + r1 * s:.1f}" y2="{cy - r1 * co:.1f}" stroke="{color}" stroke-width="{width}" stroke-linecap="round"/>')
    return "".join(out)


def hero(total, days, c):
    cx, cy, r0 = 958, 260, 168
    label = f"{total} contributions this loop."
    alt = f"Harry Sang. Software engineer. I build agents and developer tools. By day, I simulate humanoid robots. {label} A clock made of one tick per day of the past year, with the Japanese words shi ni modori, Return by Death, at its center."
    kanji = "".join(
        f'<text x="{cx}" y="{cy - 66 + i * 60}" text-anchor="middle" fill="{c["ink"]}">{ch}</text>'
        for i, ch in enumerate("死に戻り")
    )
    return f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1200 520" role="img" aria-label={quoteattr(alt)}>
<style>text{{font-family:"Hiragino Mincho ProN","Yu Mincho","Noto Serif CJK JP",serif;font-size:52px}}
.rewind{{transform-origin:{cx}px {cy}px;animation:rewind 60s linear infinite}}
@keyframes rewind{{to{{transform:rotate(-360deg)}}}}
@media (prefers-reduced-motion:reduce){{.rewind{{animation:none}}}}</style>
{ticks(days, cx, cy, r0, c)}
<circle class="rewind" cx="{cx}" cy="{cy - r0 + 16}" r="6" fill="{c["now"]}"/>
{kanji}
{text("Harry Sang", 0, 190, 132, c["ink"], -0.03)}
{text("Software engineer.", 2, 268, 38, c["soft"])}
{text("I build agents and developer tools.", 2, 320, 38, c["soft"])}
{text("By day, I simulate humanoid robots.", 2, 372, 38, c["soft"])}
{text(label, 2, 450, 38, c["witch"])}
</svg>
'''


def city(days, c):
    # One block per day: weeks run to the right, weekdays toward the viewer, height grows with contributions.
    top = max(days) or 1
    wx, wy, dx, dy = 13, 3.2, -5, 7
    blocks, ys = [], []
    for i, n in enumerate(days):
        w, d = divmod(i, 7)
        h = 2 + (64 * math.sqrt(n / top) if n else 0)
        x0, y0 = w * wx + d * dx, w * wy + d * dy
        mx, my = x0 + (wx + dx) / 2, y0 + (wy + dy) / 2
        # Shrink each footprint so the blocks read as separate buildings with streets between.
        base = [(mx + (x - mx) * 0.86, my + (y - my) * 0.86) for x, y in
                [(x0, y0), (x0 + wx, y0 + wy), (x0 + wx + dx, y0 + wy + dy), (x0 + dx, y0 + dy)]]
        blocks.append((d, w, base, h, n, i == len(days) - 1))
        ys += [y0 - h, y0 + wy + dy]
    xs = [-7 * 5 - 2, len(days) // 7 * wx + 15]
    pts = lambda p: " ".join(f"{x - xs[0]:.1f},{y - min(ys) + 4:.1f}" for x, y in p)
    out = []
    for d, w, (a, b, cc, e), h, n, today in sorted(blocks):
        up = lambda p: (p[0], p[1] - h)
        if n or today:
            out.append(f'<polygon points="{pts([e, cc, up(cc), up(e)])}" fill="{c["south"]}"/>')
            out.append(f'<polygon points="{pts([b, cc, up(cc), up(b)])}" fill="{c["east"]}"/>')
        fill = c["now"] if today else c["witch"] if n else c["faint"]
        out.append(f'<polygon points="{pts([up(a), up(b), up(cc), up(e)])}" fill="{fill}"/>')
    width, height = xs[1] - xs[0], max(ys) - min(ys) + 8
    alt = "The past year of contributions drawn as an isometric city, one block per day. Taller blocks mean more contributions."
    return f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width:.0f} {height:.0f}" role="img" aria-label={quoteattr(alt)}>
{"".join(out)}
</svg>
'''


def fetch_portraits():
    # Embedded as data URIs: an SVG inside <img> will not load anything external.
    out = []
    for *_, file in ANIME:
        req = urllib.request.Request(CHARACTER_CDN + file, headers={"User-Agent": USER})
        with urllib.request.urlopen(req, timeout=30) as res:
            out.append("data:image/png;base64," + base64.b64encode(res.read()).decode())
    return out


def anime(portraits, c):
    w, h, gap = 1200, 600, 16
    fw = 520
    rx, ry, rw, rh = fw + gap, 0, w - fw - gap, (h - 2 * gap) / 3
    pw = 150
    (quote, who, show, _), rest = ANIME[0], ANIME[1:]
    out = [
        '<defs><linearGradient id="scrim" x1="0" y1="0" x2="0" y2="1">'
        '<stop offset=".45" stop-color="#0d0a12" stop-opacity="0"/><stop offset="1" stop-color="#0d0a12" stop-opacity=".92"/></linearGradient>'
        f'<clipPath id="feature"><rect width="{fw}" height="{h}" rx="16"/></clipPath>',
    ]
    for i in range(len(rest)):
        y = ry + i * (rh + gap)
        # Round only the left corners: the portrait sits at the start of its row.
        out.append(f'<clipPath id="p{i}"><path d="M{rx + 16} {y:.1f}H{rx + pw}V{y + rh:.1f}H{rx + 16}A16 16 0 0 1 {rx} {y + rh - 16:.1f}V{y + 16:.1f}A16 16 0 0 1 {rx + 16} {y:.1f}Z"/></clipPath>')
    out.append("</defs>")
    out.append(f'<g clip-path="url(#feature)"><image href="{portraits[0]}" width="{fw}" height="{h}" preserveAspectRatio="xMidYMin slice"/><rect width="{fw}" height="{h}" fill="url(#scrim)"/></g>')
    out.append(text(quote, 40, h - 92, 58, "#ffffff", -0.01))
    out.append(text(who, 42, h - 44, 28, "#ffffff"))
    out.append(text(show, 42 + measure(who + "  ", 28), h - 44, 28, "#ffffff99"))
    for i, ((quote, who, show, _), src) in enumerate(zip(rest, portraits[1:])):
        y = ry + i * (rh + gap)
        tx = rx + pw + 36
        out.append(f'<rect x="{rx}" y="{y:.1f}" width="{rw}" height="{rh:.1f}" rx="16" fill="{c["tile"]}"/>')
        out.append(f'<image href="{src}" x="{rx}" y="{y:.1f}" width="{pw}" height="{rh:.1f}" preserveAspectRatio="xMidYMin slice" clip-path="url(#p{i})"/>')
        out.append(text(quote, tx, y + rh / 2 + 4, 34, c["ink"], -0.01))
        out.append(text(who, tx + 2, y + rh / 2 + 50, 26, c["witch"]))
        out.append(text(show, tx + 2 + measure(who + "  ", 26), y + rh / 2 + 50, 26, c["soft"]))
    alt = "Favorite anime, one line each: " + " ".join(f'"{q}" {who}, {show}.' for q, who, show, _ in ANIME)
    return f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" role="img" aria-label={quoteattr(alt)}>
{"".join(out)}
</svg>
'''


def main(out):
    out = pathlib.Path(out)
    out.mkdir(parents=True, exist_ok=True)
    total, days = fetch_days()
    portraits = fetch_portraits()
    for theme, c in THEMES.items():
        (out / f"hero-{theme}.svg").write_text(hero(total, days, c), encoding="utf-8")
        (out / f"city-{theme}.svg").write_text(city(days, c), encoding="utf-8")
        (out / f"stack-{theme}.svg").write_text(stack(c), encoding="utf-8")
        (out / f"anime-{theme}.svg").write_text(anime(portraits, c), encoding="utf-8")


if __name__ == "__main__":
    main(sys.argv[1])
