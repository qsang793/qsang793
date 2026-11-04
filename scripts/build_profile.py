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
# The kanji as outlines from Noto Serif JP (SIL OFL), so they look the same without a Japanese font installed.
GLYPHS = json.loads((HERE / "glyphs.json").read_text())
WIDTH, PAD = 846, 16
# Below this rendered width (a phone), images swap to larger text; the 846 viewBox shrinks to ~0.4 there.
NARROW = "@media (max-width:600px)"
# Tokyo Night for dark, Tokyo Night Day for light (folke/tokyonight.nvim palettes),
# with soft and the light witch darkened so small text passes WCAG AA on the panel.
THEMES = {
    "dark": dict(ink="#c0caf5", soft="#8089b3", line="#3b4261", canvas="#16161e", tile="#1a1b26", faint="#292e42", witch="#bb9af7", neon="#7aa2f7", south="#9d7cd8", east="#7058b8", now="#ff9e64"),
    "light": dict(ink="#3760bf", soft="#585f88", line="#a8aecb", canvas="#e9e9ed", tile="#e1e2e7", faint="#c4c8da", witch="#7c3bd5", neon="#2e7de9", south="#7847bd", east="#5f37a0", now="#b15c00"),
}
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
# Subaru's frames, rendered by scripts/render_subaru.py; frames.json says where his feet are and how big he is.
SUBARU = HERE.parent / "assets" / "subaru"
# One line per loop: typed, held, then rewound before the next loop tries again.
# The robot line goes first: it is the one that is about the actual work, and reduced motion shows only it.
LINES = [
    "My robot fell 3,000 times today. It's learning.",
    "My agents work while I sleep. That's the whole business plan.",
    "Hey Claude, build me an app. No mistakes.",
    "Vibe coding by day, vibe debugging by night.",
    "90% sleeping, 10% telling the AI it's wrong.",
    "Job title: engineer. Actual job: pressing Enter.",
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
    # One symbol per photo, drawn with <use>, so an image holding both themes carries each photo once.
    return "<defs>" + "".join(
        f'<symbol id="pt{i}"><image href="data:image/jpeg;base64,{base64.b64encode((PORTRAITS / file).read_bytes()).decode()}" width="100%" height="100%" preserveAspectRatio="xMidYMin slice"/></symbol>'
        for i, (*_, file) in enumerate(ANIME)) + "</defs>"


def load_subaru():
    # Like the portraits: each frame once, drawn with <use> by both themes and by the afterimages.
    # A <g>, not a <symbol>, so the frame can hang left of and above its feet, which sit at 0,0.
    f = json.loads((SUBARU / "frames.json").read_text())
    k = 40 / (1.8 * f["px_per_m"])  # Subaru is 1.8 m and drawn 40 units tall
    (w, h), (gx, gy) = f["size"], f["ground"]
    return "<defs>" + "".join(
        f'<g id="sb-{n}"><image href="data:image/webp;base64,{base64.b64encode((SUBARU / f"{n}.webp").read_bytes()).decode()}" x="{-gx * k:.1f}" y="{-gy * k:.1f}" width="{w * k:.1f}" height="{h * k:.1f}"/></g>'
        for n in ("run0", "run1", "run2", "jump", "fall", "stand")) + "</defs>"


def svg(w, h, alt, body):
    return f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w:.0f} {h:.0f}" role="img" aria-label={quoteattr(alt)} font-family="{FONT}">
{body}
</svg>
'''


def text(s, x, y, size, fill, weight=400, anchor="start"):
    return f'<text x="{x:.1f}" y="{y:.1f}" font-size="{size}" font-weight="{weight}" fill="{fill}" text-anchor="{anchor}">{escape(s)}</text>'


def kanji(s, x, y, size, fill, anchor="start"):
    # Like text(), with (x, y) on the baseline, but drawn from GLYPHS.
    k = size / GLYPHS["upm"]
    x -= {"start": 0, "middle": .5, "end": 1}[anchor] * k * sum(GLYPHS[ch]["w"] for ch in s)
    out = []
    for ch in s:
        out.append(f'<path transform="translate({x:.1f} {y:.1f}) scale({k:.3f} {-k:.3f})" fill="{fill}" d="{GLYPHS[ch]["d"]}"/>')
        x += k * GLYPHS[ch]["w"]
    return "".join(out)


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
    # 装備, the loadout, runs down the right edge the way 死に戻り runs down the Clock.
    # The logos sit straight on the panel: twelve bordered tiles read as a template, not a kit.
    h, ks = 128, 44
    w = (WIDTH - 2 * PAD - ks - 24) / len(STACK)
    # On a phone the labels would be ~4px, so they give way to larger logos; the alt text keeps the names.
    out = [f"<style>{NARROW}{{.label{{display:none}}.icon{{transform:translateY(12px) scale(1.6)}}}}</style>", panel(h, c, 0, 0)]
    for i, ch in enumerate("装備"):
        out.append(kanji(ch, WIDTH - PAD - ks / 2, (h - 2 * ks - 4) / 2 + .88 * ks + i * (ks + 4), ks, c["line"], "middle"))
    for i, (label, slug) in enumerate(STACK):
        cx = PAD + (i + .5) * w
        # The icon is centered on its group's origin, so it grows in place.
        mark = (f'<path transform="scale({28 / 24:.3f}) translate(-12 -12)" fill="{c["ink"]}" d="{ICONS[slug]}"/>' if slug
                else text("MJ", 0, 7, 20, c["ink"], 600, "middle"))
        out.append(f'<g transform="translate({cx:.1f} 52)"><g class="icon">{mark}</g></g>')
        # 11px keeps the longest label, TypeScript, inside its column.
        out.append(f'<g class="label">{text(label, cx, 94, 11, c["soft"], anchor="middle")}</g>')
    alt = "Loadout, 装備: " + ", ".join(label for label, _ in STACK) + "."
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
    words = "".join(kanji(ch, cx, cy - 66 + i * 60, 52, c["ink"], "middle") for i, ch in enumerate("死に戻り"))
    alt = "A clock with one tick per day of the past year, around the Japanese words shi ni modori, Return by Death."
    return svg(480, 480, alt, f'''<style>.rewind{{transform-origin:{cx}px {cy}px;animation:rewind 60s linear infinite}}
@keyframes rewind{{to{{transform:rotate(-360deg)}}}}
@media (prefers-reduced-motion:reduce){{.rewind{{animation:none}}}}</style>
<defs><radialGradient id="halo"><stop offset=".55" stop-color="{c["witch"]}" stop-opacity=".22"/><stop offset="1" stop-color="{c["witch"]}" stop-opacity="0"/></radialGradient></defs>
<circle cx="{cx}" cy="{cy}" r="240" fill="url(#halo)"/>
{"".join(out)}
<circle class="rewind" cx="{cx}" cy="{cy - r0 + 16}" r="6" fill="{c["now"]}"/>
{words}''')


def iso(days, top, width, hmax, c, now=False, rise=False):
    """One block per day: weeks run to the right, weekdays toward the viewer, height grows with contributions.

    Returns the polygons, scaled to `width`, their height, and each week's roof for Subaru: (x, y, built),
    the middle of its tallest block's roof, or of today's in the last week.
    """
    weeks = days[-1][0] + 1
    k = width / (7 * 6 + weeks * 15)
    wx, wy, dx, dy = 15 * k, 2.2 * k, -6 * k, 6 * k
    blocks, ys, tops, built = [], [], {}, {}
    for i, (w, d, n) in enumerate(days):
        h = 2 * k + (hmax * math.sqrt(n / top) if n else 0)
        x0, y0 = w * wx + d * dx, w * wy + d * dy
        mx, my = x0 + (wx + dx) / 2, y0 + (wy + dy) / 2
        # Shrink each footprint so the blocks read as separate buildings with streets between.
        base = [(mx + (x - mx) * 0.86, my + (y - my) * 0.86) for x, y in
                [(x0, y0), (x0 + wx, y0 + wy), (x0 + wx + dx, y0 + wy + dy), (x0 + dx, y0 + dy)]]
        blocks.append((d, w, base, h, n, now and i == len(days) - 1))
        ys += [y0 - h, y0 + wy + dy]
        last = i == len(days) - 1
        if w not in tops or h > tops[w][0] or last:
            tops[w] = (h, mx, my - h)
        built[w] = built.get(w, False) or bool(n) or last
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
    roofs = [(tops[w][1] - 7 * dx, tops[w][2] - min(ys), built[w]) for w in sorted(tops)]
    return "".join(out), max(ys) - min(ys), roofs


def subaru(roofs, c, start):
    """One Attempt as CSS keyframes: Subaru hops a roof a week, dies once in the longest stretch of empty weeks,
    returns to the Save point before it, clears it, and rests on today's roof until the next Attempt.

    `roofs` comes from iso(); `start` waits out the City's rise. Returns the style, the drawing and an alt sentence.
    """
    hop, rest = .22, 8
    # Stretches of empty weeks with a built week on each side, as (first empty week, first built week after).
    gaps, first = [], None
    for i, (*_, built) in enumerate(roofs):
        if not built and first is None and i and roofs[i - 1][2]:
            first = i
        elif built and first is not None:
            gaps.append((first, i))
            first = None
    # The longest one; between equals, the one nearest today.
    gap = max(gaps, key=lambda g: (g[1] - g[0], g[0]), default=None)
    xy = lambda i: roofs[i][:2]
    t, pos, frame, alpha = 0, [], [], []  # (time, x, y), (time, frame), (time, opacity)

    def arc(a, b, dur, lift):
        nonlocal t
        (x0, y0), (x1, y1), t0 = a, b, t
        for f in (.25, .5, .75, 1):
            t = t0 + dur * f
            pos.append((t, x0 + (x1 - x0) * f, y0 + (y1 - y0) * f - 4 * (lift + abs(y1 - y0) / 2) * f * (1 - f)))

    def hops(a, b):
        for i in range(a, b):
            arc(xy(i), xy(i + 1), hop, 4)

    pos.append((0, *xy(0)))
    frame.append((0, "run"))
    alpha += [(0, 0), (.2, 1)]
    t = .2
    pos.append((t, *xy(0)))
    rewind = None
    if gap:
        save, land = gap[0] - 1, gap[1]
        hops(0, save)
        # The leap falls short: over the middle of the gap he drops below the street.
        x, y = xy(gap[0] + (gap[1] - gap[0] - 1) // 2)
        leap0 = len(pos) - 1
        frame.append((t, "jump"))
        frame.append((t + .4, "fall"))
        arc(xy(save), (x, y + 14), .8, 14)
        leap = pos[leap0:]
        alpha += [(t - .25, 1), (t, 0)]
        died = t
        # The Witch's shadow takes him, then time runs back along the leap to the Save point.
        t += .7
        rewind = t
        alpha += [(t, 0), (t + .05, .6)]
        frame.append((t, "fall"))
        for j, (_, px, py) in enumerate(reversed(leap)):
            pos.append((t + .15 * j, px, py))
        frame.append((t + .3, "jump"))
        t += .15 * (len(leap) - 1)
        back = t
        alpha += [(t, .6), (t + .1, 1)]
        frame.append((t, "stand"))
        t += .5
        pos.append((t, *xy(save)))
        frame.append((t, "jump"))
        arc(xy(save), xy(land), .5 + .05 * (land - save), 14 + 2 * (land - save))
        frame.append((t, "run"))
        hops(land, len(roofs) - 1)
        said = ("Subaru runs the rooftops a week per hop, dies once in the longest stretch of empty weeks, "
                "returns by death to the roof before it, and makes it across to today.")
    else:
        hops(0, len(roofs) - 1)
        said = "Subaru runs the rooftops a week per hop, all the way to today."
    frame.append((t, "stand"))
    total = t + rest
    pos.append((total, *xy(-1)))
    alpha += [(total - .2, 1), (total, 0)]
    pct = lambda t: f"{100 * t / total:.2f}%"
    keys = lambda name, rows: f"@keyframes {name}{{" + "".join(f"{pct(t)}{{{r}}}" for t, r in rows) + "}"
    css = [keys("sbp", [(t, f"transform:translate({x:.1f}px,{y:.1f}px)") for t, x, y in pos]),
           keys("sbo", [(t, f"opacity:{a}") for t, a in alpha])]
    loop = lambda name, ease: f"animation:{name} {total:.2f}s {ease} {start:.2f}s infinite both"
    css.append(f".sbp{{{loop('sbp', 'linear')}}}.sbo{{{loop('sbo', 'linear')}}}")
    for m in ("run", "jump", "fall", "stand"):
        css.append(keys(f"sb{m}", [(t, f"opacity:{int(f == m)}") for t, f in frame + [(total, frame[-1][1])]]))
        css.append(f".sb{m}{{{loop(f'sb{m}', 'step-end')}}}")
    # Three run frames take turns, whatever else is moving.
    css.append("@keyframes sbc{0%{opacity:1}33.3%,100%{opacity:0}}.sbc{animation:sbc .27s step-end infinite both}")
    out = []
    if gap:
        css.append(keys("sbg", [(0, "opacity:0"), (rewind, "opacity:.4"), (back + .1, "opacity:0")]))
        css.append(f".sbg{{{loop('sbg', 'step-end')}}}")
        css.append(keys("sbw", [(0, "transform:scale(0);opacity:0"), (died - .1, "transform:scale(0);opacity:.8"),
                                (died + .3, "transform:scale(1);opacity:.8"), (back, "transform:scale(1.2);opacity:0")]))
        css.append(f".sbw{{transform-box:fill-box;transform-origin:center;{loop('sbw', 'ease-out')}}}")
        out.append(f'<ellipse class="sbw" cx="{x:.1f}" cy="{y:.1f}" rx="30" ry="10" fill="{c["witch"]}"/>')

    def body(delay=None):
        s = f' style="animation-delay:{delay:.2f}s"' if delay is not None else ""
        run = "".join(f'<use class="sbc" href="#sb-run{i}" style="animation-delay:-{.09 * (3 - i) % .27:.2f}s"/>' for i in range(3))
        return (f'<g class="sbp"{s}><g class="sz"><g class="sbrun"{s}>{run}</g>'
                + "".join(f'<g class="sb{m}"{s}><use href="#sb-{m}"/></g>' for m in ("jump", "fall", "stand")) + "</g></g>")

    out.append('<defs><filter id="sbl" x="-20%" y="-20%" width="140%" height="140%">'
               f'<feMorphology in="SourceAlpha" operator="dilate" radius=".8" result="d"/><feFlood flood-color="{c["ink"]}"/>'
               '<feComposite in2="d" operator="in"/><feMerge><feMergeNode/><feMergeNode in="SourceGraphic"/></feMerge></filter>'
               f'<filter id="sbt"><feFlood flood-color="{c["witch"]}"/><feComposite in2="SourceAlpha" operator="in"/></filter></defs>')
    if gap:
        # Afterimages trail him back, each a little later along the same path, only while time runs back.
        for k in (3, 2, 1):
            out.append(f'<g class="sbg" style="animation-delay:{start + .06 * k:.2f}s" filter="url(#sbt)">{body(start + .06 * k)}</g>')
    out.append(f'<g class="sbo" filter="url(#sbl)">{body()}</g>')
    out = f'<g class="sb">{"".join(out)}</g>'
    # Reduced motion: he just stands on today's roof.
    x, y = xy(-1)
    out += f'<g class="sbx" transform="translate({x:.1f} {y:.1f})" filter="url(#sbl)"><g class="sz"><use href="#sb-stand"/></g></g>'
    css.append(f".sbx{{display:none}}@media (prefers-reduced-motion:reduce){{.sb{{display:none}}.sbx{{display:inline}}}}"
               f"{NARROW}{{.sz{{transform:scale(1.6)}}}}")
    return "".join(css), out, said


def city(total, days, c, frames=""):
    # `frames` is load_subaru(): pass it here, or to adaptive() when one image holds both themes.
    body, bh, roofs = iso(days, max(n for *_, n in days) or 1, WIDTH - 2 * PAD, 44, c, now=True, rise=True)
    # Subaru starts once the last week has risen.
    run_css, run, said = subaru(roofs, c, len(roofs) * 0.03 + .8)
    head = 32
    h = PAD + head + bh + PAD
    out = [
        '<style>.rise{transform-box:fill-box;transform-origin:50% 100%;animation:rise .8s cubic-bezier(.16,1,.3,1) both}'
        '@keyframes rise{from{transform:scaleY(0)}}@media (prefers-reduced-motion:reduce){.rise{animation:none}}'
        f'{NARROW}{{.count text{{font-size:30px;transform:translateY(10px)}}}}{run_css}</style>',
        frames,
        panel(h, c, 0, 1),
        # 不夜城, the city that never sleeps, sits in the empty corner above the later weeks.
        kanji("不夜城", WIDTH - PAD, PAD + 46, 48, c["line"], "end"),
        f'<g class="count">{text(f"{total} contributions in the last year", PAD, PAD + 14, 14, c["soft"])}</g>',
        f'<g transform="translate({PAD} {PAD + head})">{body}{run}</g>',
    ]
    alt = f"{total} contributions in the last year, drawn as an isometric city, one block per day. Taller blocks mean more contributions. {said}"
    return svg(WIDTH, h, alt, "".join(out))


def anime(c, portraits=""):
    # `portraits` is load_portraits(): pass it here, or to adaptive() when one image holds both themes.
    ih, gap, fw = 288, 8, 240
    h = ih + 2 * PAD
    rx = PAD + fw + gap
    rh = (ih - 2 * gap) / 3
    pw = 72
    (quote, who, show, _), rest = ANIME[0], ANIME[1:]
    out = [
        # On a phone the text grows to stay readable; the big panel drops its show name to make room.
        f"<style>{NARROW}{{.fq text{{font-size:25px;transform:translateY(-6px)}}.fm{{font-size:24px}}.fm .show{{display:none}}"
        ".rq text{font-size:26px;transform:translateY(-6px)}.rm{font-size:24px;transform:translateY(10px)}}</style>",
        portraits,
        panel(h, c, 1, 1),
        # 推し, your favorite character, sits under the quotes the way 不夜城 sits over the City.
        kanji("推し", WIDTH - PAD - 8, PAD + ih - 12, 96, c["line"], "end"),
        '<defs><linearGradient id="scrim" x1="0" y1="0" x2="0" y2="1">'
        '<stop offset=".5" stop-color="#010409" stop-opacity="0"/><stop offset="1" stop-color="#010409" stop-opacity=".9"/></linearGradient>'
        f'<clipPath id="feature"><rect x="{PAD}" y="{PAD}" width="{fw}" height="{ih}" rx="6"/></clipPath>',
    ]
    for i in range(len(rest)):
        out.append(f'<clipPath id="p{i}"><rect x="{rx}" y="{PAD + i * (rh + gap):.1f}" width="{pw}" height="{rh:.1f}" rx="6"/></clipPath>')
    out.append("</defs>")
    out.append(f'<g clip-path="url(#feature)"><use href="#pt0" x="{PAD}" y="{PAD}" width="{fw}" height="{ih}"/><rect x="{PAD}" y="{PAD}" width="{fw}" height="{ih}" fill="url(#scrim)"/></g>')
    out.append(f'<g class="fq">{text(f"“{quote}”", PAD + 16, PAD + ih - 38, 20, "#ffffff", 600)}</g>')
    out.append(f'<text class="fm" x="{PAD + 16}" y="{PAD + ih - 16}" font-size="12"><tspan fill="#ffffff">{escape(who)}</tspan><tspan class="show" fill="#ffffffaa" dx="6">{escape(show)}</tspan></text>')
    # No cards around the other three: the quotes are the content, so they stand on the panel at display size.
    for i, (quote, who, show, _) in enumerate(rest):
        y = PAD + i * (rh + gap)
        tx = rx + pw + 20
        out.append(f'<g clip-path="url(#p{i})"><use href="#pt{i + 1}" x="{rx}" y="{y:.1f}" width="{pw}" height="{rh:.1f}"/></g>')
        out.append(f'<g class="rq">{text(f"“{quote}”", tx, y + rh / 2, 20, c["ink"])}</g>')
        out.append(f'<text class="rm" x="{tx}" y="{y + rh / 2 + 20:.1f}" font-size="12"><tspan fill="{c["witch"]}">{escape(who)}</tspan><tspan fill="{c["soft"]}" dx="6">{escape(show)}</tspan></text>')
    alt = "Favorite anime, one line each: " + " ".join(f'"{q}" {who}, {show}.' for q, who, show, _ in ANIME)
    return svg(WIDTH, h, alt, "".join(out))


def main(out):
    out = pathlib.Path(out)
    out.mkdir(parents=True, exist_ok=True)
    total, days = fetch_calendar()
    portraits, frames = load_portraits(), load_subaru()
    for theme, c in THEMES.items():
        (out / f"clock-{theme}.svg").write_text(clock(days, c), encoding="utf-8")
        (out / f"intro-{theme}.svg").write_text(intro(c), encoding="utf-8")
        (out / f"city-{theme}.svg").write_text(city(total, days, c, frames), encoding="utf-8")
        (out / f"stack-{theme}.svg").write_text(stack(c), encoding="utf-8")
        (out / f"anime-{theme}.svg").write_text(anime(c, portraits), encoding="utf-8")


if __name__ == "__main__":
    main(sys.argv[1])
