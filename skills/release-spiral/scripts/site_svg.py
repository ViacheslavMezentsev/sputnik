#!/usr/bin/env python3
"""SVG для страницы сайта: календарь занятости и спираль, цвета — переменные темы сайта (тёмная и светлая).

    python3 site_svg.py assets/demo/turns.json assets/demo/events.jsonl --tz +05:00 --out-dir build/site-svg
Пишет calendar.svg и spiral.svg (встраиваются в HTML как есть).
"""
import argparse
import calendar
import datetime as dt
import json
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from collect_events import tz_arg  # noqa: E402
from spiral_common import parse_time, read_events  # noqa: E402

SEC = ["var(--accent)", "var(--attention)", "var(--success)", "var(--done)"]
MON = ["янв", "фев", "мар", "апр", "май", "июн", "июл", "авг", "сен", "окт", "ноя", "дек"]


def daily(events, tz, gap_min):
    iv = sorted((e["_t0"].astimezone(tz), max(e["_t1"], e["_t0"]).astimezone(tz)) for e in events)
    merged = []
    for a, b in iv:
        if merged and a <= merged[-1][1] + dt.timedelta(minutes=gap_min):
            merged[-1][1] = max(merged[-1][1], b)
        else:
            merged.append([a, b])
    days = {}
    for a, b in merged:
        t = a
        while t < b:
            nxt = min(b, (t + dt.timedelta(hours=1)).replace(minute=0, second=0, microsecond=0))
            days[t.date()] = days.get(t.date(), 0) + (nxt - t).total_seconds() / 3600
            t = nxt
    return days


def calendar_svg(model, events, tz):
    p0, p1 = (dt.date.fromisoformat(x) for x in model["period"])
    first = dt.date(p0.year, p0.month, 1)
    last = dt.date(p1.year, p1.month, calendar.monthrange(p1.year, p1.month)[1])
    start = first - dt.timedelta(days=first.weekday())
    days = daily(events, tz, model["rules"]["time"]["session_gap_min"])
    c, g = 13, 3
    weeks = (last - start).days // 7 + 1
    W, H = 30 + weeks * (c + g), 20 + 7 * (c + g) + 26
    op = lambda h: 0 if h <= 0 else 0.3 if h <= 2 else 0.55 if h <= 4 else 0.8 if h <= 8 else 1.0
    s = ['<svg class="activity" viewBox="0 0 %d %d" width="%d" height="%d" style="max-width:100%%;height:auto" role="img" '
         'aria-label="Календарь занятости проектом">' % (W, H, W * 1.5, H * 1.5)]
    d, seen = first, set()
    while d <= last:
        w, r = (d - start).days // 7, d.weekday()
        x, y = 30 + w * (c + g), 18 + r * (c + g)
        inside = p0 <= d <= p1
        h = days.get(d, 0) if inside else 0
        title = "%s: %s ч" % (d.strftime("%d.%m"), ("%.1f" % h).replace(".", ","))
        if not inside:
            s.append('<rect x="%d" y="%d" width="%d" height="%d" rx="2" fill="none" stroke="var(--border-muted)"/>' % (x, y, c, c))
        elif h <= 0:
            s.append('<rect x="%d" y="%d" width="%d" height="%d" rx="2" fill="var(--bg-inset)" stroke="var(--border-muted)"><title>%s</title></rect>' % (x, y, c, c, title))
        else:
            s.append('<rect x="%d" y="%d" width="%d" height="%d" rx="2" fill="var(--accent)" fill-opacity="%.2f"><title>%s</title></rect>' % (x, y, c, c, op(h), title))
        if (d.year, d.month) not in seen:
            seen.add((d.year, d.month))
            s.append('<text x="%d" y="12" font-size="10" fill="var(--fg-muted)">%s</text>' % (x, MON[d.month - 1]))
        d += dt.timedelta(days=1)
    for r, name in ((0, "Пн"), (2, "Ср"), (4, "Пт"), (6, "Вс")):
        s.append('<text x="0" y="%d" font-size="9" fill="var(--fg-muted)">%s</text>' % (28 + r * (c + g), name))
    ly = H - 8
    s.append('<text x="30" y="%d" font-size="9" fill="var(--fg-muted)">меньше</text>' % ly)
    for i, o in enumerate((0, 0.3, 0.55, 0.8, 1.0)):
        fill = 'fill="var(--bg-inset)" stroke="var(--border-muted)"' if o == 0 else 'fill="var(--accent)" fill-opacity="%.2f"' % o
        s.append('<rect x="%d" y="%d" width="10" height="10" rx="2" %s/>' % (72 + i * 13, ly - 9, fill))
    s.append('<text x="%d" y="%d" font-size="9" fill="var(--fg-muted)">больше</text>' % (72 + 5 * 13 + 4, ly))
    s.append("</svg>")
    total = sum(v for k, v in days.items() if p0 <= k <= p1)
    active = sum(1 for k, v in days.items() if p0 <= k <= p1 and v > 0)
    return "\n".join(s), total, active


def spiral_svg(model, turns, start, end, size=420):
    lanes = model["rules"]["lanes"]
    cx = cy = size / 2
    r0, dr = 18, (size / 2 - 60) / max(len(turns), 1)
    s = ['<svg class="spiral" viewBox="-90 0 %d %d" style="width:100%%;height:auto" role="img" aria-label="Спираль выпуска">'
         % (size + 180, size)]
    for i, t in enumerate(turns):
        mins, fails = [0.0] * 4, 0
        for x in t["tasks"]:
            mins[lanes.get(x["lane"], 2)] += x["min"]
            fails += x.get("fails", 0)
        for sec in range(4):
            pts = []
            for k in range(25):
                th = 2 * math.pi * i + (sec + k / 24) * math.pi / 2
                r = r0 + dr * th / (2 * math.pi)
                pts.append("%.1f,%.1f" % (cx + r * math.cos(math.pi / 2 + th), cy - r * math.sin(math.pi / 2 + th)))
            if mins[sec] > 0:
                w = 1.5 + 6 * min(mins[sec], 240) / 240
                s.append('<polyline points="%s" fill="none" stroke="%s" stroke-width="%.1f"><title>виток %d: %d мин</title></polyline>'
                         % (" ".join(pts), SEC[sec], w, t["n"], mins[sec]))
            else:
                s.append('<polyline points="%s" fill="none" stroke="var(--border)" stroke-width="1" stroke-dasharray="3 3"/>'
                         % " ".join(pts))
        for j in range(min(fails, 8)):
            th = 2 * math.pi * i + math.pi + (j + 0.5) * (math.pi / 2) / min(fails, 8)
            r = r0 + dr * th / (2 * math.pi)
            x, y = cx + r * math.cos(math.pi / 2 + th), cy - r * math.sin(math.pi / 2 + th)
            s.append('<path d="M%.1f %.1fl5 5M%.1f %.1fl-5 5" stroke="var(--danger, #f85149)" stroke-width="1.6"/>'
                     % (x - 2.5, y - 2.5, x + 2.5, y - 2.5))
        r = r0 + dr * i
        s.append('<circle cx="%.1f" cy="%.1f" r="7" fill="var(--fg)"/><text x="%.1f" y="%.1f" font-size="8" text-anchor="middle" '
                 'fill="var(--bg)" font-weight="bold">%d</text>' % (cx, cy - r, cx, cy - r + 3, t["n"]))
    rend = r0 + dr * len(turns)
    s.append('<text x="%.1f" y="%.1f" font-size="12" font-weight="bold" fill="var(--danger, #f85149)">★ %s</text>'
             % (cx - 6, cy - rend - 4, end))
    s.append('<circle cx="%.1f" cy="%.1f" r="4" fill="var(--fg)"/><text x="%.1f" y="%.1f" font-size="10" text-anchor="middle" '
             'fill="var(--fg)">%s</text>' % (cx, cy, cx, cy + 16, start))
    R = rend + 18
    for sec, ang, anchor in ((0, 135, "end"), (1, 225, "end"), (2, 315, "start"), (3, 45, "start")):
        a = math.radians(ang)
        s.append('<text x="%.1f" y="%.1f" font-size="11" font-weight="bold" text-anchor="%s" fill="%s">%s</text>'
                 % (cx + R * math.cos(a), cy - R * math.sin(a), anchor, SEC[sec], model["rules"]["sectors"][sec]))
    s.append("</svg>")
    return "\n".join(s)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("turns")
    ap.add_argument("events")
    ap.add_argument("--tz", type=tz_arg, default=dt.timezone.utc)
    ap.add_argument("--out-dir", required=True)
    a = ap.parse_args(argv)
    model = json.load(open(a.turns, encoding="utf-8"))
    ev = read_events(a.events)
    os.makedirs(a.out_dir, exist_ok=True)
    cal, total, active = calendar_svg(model, ev, a.tz)
    rt = model["release_turn"]
    sp = spiral_svg(model, [t for t in model["turns"] if t["n"] <= rt], model["versions"][0], model["versions"][1])
    open(os.path.join(a.out_dir, "calendar.svg"), "w", encoding="utf-8").write(cal)
    open(os.path.join(a.out_dir, "spiral.svg"), "w", encoding="utf-8").write(sp)
    print("calendar.svg: %d дней, %.0f ч; spiral.svg: %d витков" % (active, total, rt))


if __name__ == "__main__":
    sys.exit(main())
