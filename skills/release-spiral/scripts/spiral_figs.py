"""Рисунки спирали выпуска: две спирали, цепочка CI, развёртка, часы по виткам, запуски, календарь."""
import calendar
import datetime as dt
import math
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
from matplotlib.patches import FancyBboxPatch, Rectangle  # noqa: E402

plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 9, "axes.facecolor": "#FAFAF7",
                     "axes.edgecolor": "#BBBBBB", "axes.grid": True, "grid.color": "#E3E3E3",
                     "axes.spines.top": False, "axes.spines.right": False, "legend.frameon": False})
SEC_COL = ["#7DA7D9", "#E8A33C", "#5BAE6A", "#9B6BD1"]
GREY = "#777777"
LANE_COL = ["#7DA7D9", "#A9C4E6", "#E8A33C", "#2A6FDB", "#E8692E", "#3A9E6A", "#1F7A4D", "#B8860B", "#B9B9B9",
            "#8E8E8E", "#9B6BD1", "#6A3FA0"]
CAL_COL = ["#ebedf0", "#b6d8fa", "#77b8f3", "#348ce0", "#0969da"]
MONTHS = ["янв", "фев", "мар", "апр", "май", "июн", "июл", "авг", "сен", "окт", "ноя", "дек"]


def _comma(ax, x=True):
    import matplotlib.ticker as mt
    f = mt.FuncFormatter(lambda v, p: f"{v:g}".replace(".", ","))
    (ax.xaxis if x else ax.yaxis).set_major_formatter(f)


def save(fig, out, name):
    path = os.path.join(out, name + ".png")
    fig.savefig(path, dpi=170, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    return path


def sector_of(model, lane):
    return model["rules"]["lanes"].get(lane, 2)


def lanes(model):
    seen = list(model["rules"]["lanes"])
    for t in model["turns"]:
        for x in t["tasks"]:
            if x["lane"] not in seen:
                seen.append(x["lane"])
    used = {x["lane"] for t in model["turns"] for x in t["tasks"]}
    return [l for l in seen if l in used]


def spiral(model, turns, title, start, end, out, name, size=(7.4, 6.6)):
    fig, ax = plt.subplots(figsize=size)
    r0, dr = 0.55, min(0.75, 6.2 / max(len(turns), 1)) if len(turns) > 1 else 1.4
    for i, t in enumerate(turns):
        mins, fails = [0.0] * 4, 0
        for x in t["tasks"]:
            mins[sector_of(model, x["lane"])] += x["min"]
            fails += x.get("fails", 0)
        for s in range(4):
            th = np.linspace(2 * math.pi * i + s * math.pi / 2, 2 * math.pi * i + (s + 1) * math.pi / 2, 60)
            r = r0 + dr * th / (2 * math.pi)
            x, y = r * np.cos(math.pi / 2 + th), r * np.sin(math.pi / 2 + th)
            if mins[s] > 0:
                ax.plot(x, y, color=SEC_COL[s], lw=1.6 + 5.0 * min(mins[s], 180) / 180, solid_capstyle="butt")
            else:
                ax.plot(x, y, color="#CCCCCC", lw=1.0, ls=(0, (2, 2)))
        for j in range(min(fails, 8)):
            tt = 2 * math.pi * i + math.pi + (j + 0.5) * (math.pi / 2) / min(fails, 8)
            rr = r0 + dr * tt / (2 * math.pi)
            ax.plot(rr * math.cos(math.pi / 2 + tt), rr * math.sin(math.pi / 2 + tt), "x", color="#C0392B", ms=5, mew=1.6)
        rr = r0 + dr * i
        ax.text(0, rr, str(t["n"]), ha="center", va="center", fontsize=7.4, color="white", weight="bold",
                bbox=dict(boxstyle="circle,pad=0.22", fc="#333333", ec="none"))
    rend = r0 + dr * len(turns)
    ax.plot([0], [rend], marker="*", ms=16, color="#C0392B")
    ax.text(0.25, rend + 0.15, end, fontsize=8.6, weight="bold", color="#C0392B", va="bottom")
    ax.plot([0], [0], marker="o", ms=8, color="#333333")
    ax.text(0, -0.45, start, fontsize=8.2, ha="center", va="top", weight="bold")
    R = rend + 0.9
    for s, ang, ha in ((0, 135, "right"), (1, 225, "right"), (2, 315, "left"), (3, 45, "left")):
        a = math.radians(ang)
        ax.text(R * math.cos(a), R * math.sin(a), model["rules"]["sectors"][s], color=SEC_COL[s], fontsize=8.4,
                weight="bold", ha=ha, va="center")
    ax.set_aspect("equal")
    ax.axis("off")
    ax.set_xlim(-R - 1.8, R + 1.8)
    ax.set_ylim(-R - 0.6, R + 1.0)
    ax.set_title(title, fontsize=9.5)
    return save(fig, out, name)


def ci_chain(model, out):
    chain = model["ci_chain"]
    fig, ax = plt.subplots(figsize=(7.4, 2.4))
    ax.set_xlim(-1.5, 101.5)
    ax.set_ylim(-2, 22)
    ax.axis("off")
    n, w = len(chain), 14.0
    gap = (100 - w * n) / (n - 1)
    for i, (name, cnt, note) in enumerate(chain):
        x = i * (w + gap)
        col = SEC_COL[3] if i < n - 1 else "#C0392B"
        ax.add_patch(FancyBboxPatch((x, 8), w, 12, boxstyle="round,pad=0.3,rounding_size=1.2", fc="white", ec=col, lw=1.4))
        ax.text(x + w / 2, 16.6, name, ha="center", va="center", fontsize=7.6, weight="bold", linespacing=1.1)
        word = "конвейер" if cnt % 10 == 1 and cnt % 100 != 11 else (
            "конвейера" if 2 <= cnt % 10 <= 4 and not 12 <= cnt % 100 <= 14 else "конвейеров")
        ax.text(x + w / 2, 11.6, str(cnt), ha="center", va="center", fontsize=11, color=col, weight="bold")
        ax.text(x + w / 2, 9.2, word, ha="center", va="center", fontsize=6.6, color=col)
        ax.text(x + w / 2, 6.3, note, ha="center", va="top", fontsize=6.8, color=GREY, linespacing=1.15)
        if i < n - 1:
            ax.annotate("", (x + w + gap - 0.4, 14), (x + w + 0.4, 14), arrowprops=dict(arrowstyle="-|>", color=GREY, lw=1.2))
    return save(fig, out, "ci_chain")


def gantt(model, out):
    ls = list(reversed(lanes(model)))
    fig, ax = plt.subplots(figsize=(7.4, 0.9 + 0.3 * len(ls)))
    t, bounds = 0.0, []
    for turn in model["turns"]:
        t0 = t
        for x in turn["tasks"]:
            ax.barh(ls.index(x["lane"]), x["min"] / 60, left=t / 60, height=0.66,
                    color=LANE_COL[ls[::-1].index(x["lane"]) % len(LANE_COL)], lw=0)
            t += x["min"]
        bounds.append((turn["n"], t0, t))
    for k, a, b in bounds:
        ax.axvline(a / 60, color="#DDDDDD", lw=0.7, zorder=0)
        ax.text((a + b) / 120, len(ls) - 0.35, str(k), ha="center", fontsize=7, color="#333333")
    rel = [b for k, a, b in bounds if k == model["release_turn"]]
    if rel:
        ax.axvline(rel[0] / 60, color="#C0392B", lw=1.3, ls="--")
        ax.text(rel[0] / 60 + 0.2, 0.2, "выпуск %s готов" % model["versions"][1], color="#C0392B", fontsize=7.5)
    ax.set_yticks(range(len(ls)))
    ax.set_yticklabels(ls, fontsize=7.3)
    ax.set_ylim(-0.6, len(ls) + 0.2)
    ax.set_xlabel("Часы работы подряд (сумма по задачам, без перерывов и ожидания)")
    ax.set_xlim(0, t / 60 + 0.3)
    _comma(ax)
    return save(fig, out, "gantt")


def turn_hours(model, out):
    ks = [t["n"] for t in model["turns"]]
    fig, ax = plt.subplots(figsize=(7.4, 3.0))
    bottom = np.zeros(len(ks))
    for s, name in enumerate(model["rules"]["sectors"]):
        v = np.array([sum(x["min"] for x in t["tasks"] if sector_of(model, x["lane"]) == s) / 60 for t in model["turns"]])
        ax.bar(range(len(ks)), v, bottom=bottom, color=SEC_COL[s], width=0.62, label=name)
        bottom += v
    for i, b in enumerate(bottom):
        ax.text(i, b + 0.06, f"{b:.1f}".replace(".", ","), ha="center", fontsize=7)
    ax.axvline(model["release_turn"] - 0.5, color="#C0392B", ls="--", lw=1)
    ax.set_xticks(range(len(ks)))
    ax.set_xticklabels([str(k) for k in ks])
    ax.set_xlabel("Виток")
    ax.set_ylabel("Часы")
    ax.set_ylim(0, max(bottom) * 1.4 + 0.5)
    ax.set_axisbelow(True)
    ax.legend(ncol=4, fontsize=7, loc="upper left")
    return save(fig, out, "turn_hours")


def attempts(model, out):
    ks = [t["n"] for t in model["turns"]]
    n = np.array([sum(x.get("n", 0) for x in t["tasks"]) for t in model["turns"]])
    f = np.array([sum(x.get("fails", 0) for x in t["tasks"]) for t in model["turns"]])
    fig, ax = plt.subplots(figsize=(7.4, 2.4))
    ax.bar(range(len(ks)), n - f, color="#5BAE6A", width=0.62, label="запуск прошёл")
    ax.bar(range(len(ks)), f, bottom=n - f, color="#C0392B", width=0.62, label="сбой → правка → повтор")
    for i, (a, b) in enumerate(zip(n, f)):
        if a:
            ax.text(i, a + 0.3, f"{a}" + (f" ({b})" if b else ""), ha="center", fontsize=7)
    ax.axvline(model["release_turn"] - 0.5, color="#C0392B", ls="--", lw=1)
    ax.set_xticks(range(len(ks)))
    ax.set_xticklabels([str(k) for k in ks])
    ax.set_xlabel("Виток")
    ax.set_ylabel("Запусков")
    ax.set_ylim(0, max(max(n), 1) * 1.35 + 2)
    ax.set_axisbelow(True)
    ax.legend(fontsize=7, loc="upper left")
    return save(fig, out, "attempts")


def _union(iv, gap):
    out = []
    for a, b in sorted(iv):
        if out and a <= out[-1][1] + gap:
            out[-1][1] = max(out[-1][1], b)
        else:
            out.append([a, b])
    return out


def daily_hours(events, tz, gap_min):
    days, hours = {}, [0.0] * 24
    for a, b in _union([(e["_t0"].astimezone(tz), max(e["_t1"], e["_t0"]).astimezone(tz)) for e in events],
                       dt.timedelta(minutes=gap_min)):
        t = a
        while t < b:
            nxt = min(b, (t + dt.timedelta(hours=1)).replace(minute=0, second=0, microsecond=0))
            h = (nxt - t).total_seconds() / 3600
            days[t.date()] = days.get(t.date(), 0) + h
            hours[t.hour] += h
            t = nxt
    return days, hours


def activity_calendar(events, period, tz, gap_min, title, out, tz_label):
    days, hours = daily_hours(events, tz, gap_min)
    p0, p1 = period
    first = dt.date(p0.year, p0.month, 1)
    last = dt.date(p1.year, p1.month, calendar.monthrange(p1.year, p1.month)[1])
    start = first - dt.timedelta(days=first.weekday())
    nweeks = (last - start).days // 7 + 1
    lvl = lambda h: 0 if h <= 0 else 1 if h <= 2 else 2 if h <= 4 else 3 if h <= 8 else 4
    fig = plt.figure(figsize=(7.4, 2.9))
    ax = fig.add_axes([0.05, 0.27, 0.63, 0.56])
    d, seen = first, set()
    while d <= last:
        w, r = (d - start).days // 7, d.weekday()
        inside = p0 <= d <= p1
        ax.add_patch(Rectangle((w + 0.08, -r - 0.92), 0.84, 0.84, fc=CAL_COL[lvl(days.get(d, 0))] if inside else "#f6f8fa",
                               ec="none" if inside else "#d0d7de", lw=0.5))
        if (d.year, d.month) not in seen:
            seen.add((d.year, d.month))
            ax.text(w + 0.1, 0.35, MONTHS[d.month - 1], fontsize=7.5, color="#24292f", va="bottom")
        d += dt.timedelta(days=1)
    for r, name in ((0, "Пн"), (2, "Ср"), (4, "Пт"), (6, "Вс")):
        ax.text(-0.25, -r - 0.5, name, fontsize=7, ha="right", va="center", color="#57606a")
    ax.set_xlim(-0.1, nweeks + 0.1)
    ax.set_ylim(-7.2, 1.3)
    ax.set_aspect("equal")
    ax.axis("off")
    inside = {k: v for k, v in days.items() if p0 <= k <= p1}
    active, total = sum(1 for v in inside.values() if v > 0), sum(inside.values())
    peak = max(((v, k) for k, v in inside.items()), default=(0, p0))
    word = "день" if active % 10 == 1 and active % 100 != 11 else (
        "дня" if 2 <= active % 10 <= 4 and not 12 <= active % 100 <= 14 else "дней")
    fig.text(0.06, 0.93, title, fontsize=9.5, color="#24292f", weight="bold")
    fig.text(0.06, 0.865, f"{active} {word} с работой, {total:.0f} ч активности по журналам; больше всего — "
                          + f"{peak[0]:.1f}".replace(".", ",") + f" ч ({peak[1]:%d.%m})", fontsize=7.6, color="#57606a")
    fig.text(0.06, 0.17, "Меньше", fontsize=7, color="#57606a", va="center")
    for i, c in enumerate(CAL_COL):
        fig.patches.append(Rectangle((0.12 + i * 0.022, 0.155), 0.016, 0.032, transform=fig.transFigure, fc=c, ec="none"))
    fig.text(0.235, 0.17, "Больше", fontsize=7, color="#57606a", va="center")
    fig.text(0.06, 0.08, "уровни: 0 ч · до 2 ч · 2–4 ч · 4–8 ч · больше 8 ч; светлые клетки с рамкой — вне периода "
                         "выпуска", fontsize=6.8, color="#57606a")
    ax2 = fig.add_axes([0.74, 0.34, 0.24, 0.42])
    ax2.bar(range(24), hours, color=CAL_COL[3], width=0.8)
    ax2.set_xticks([0, 6, 12, 18, 23])
    ax2.tick_params(labelsize=6.5)
    ax2.set_title("Часы активности по времени суток", fontsize=7.4)
    ax2.set_xlabel("час (%s)" % tz_label, fontsize=6.8)
    ax2.set_ylabel("часы", fontsize=6.8)
    path = save(fig, out, "activity")
    busiest = sorted(((v, k) for k, v in inside.items()), reverse=True)[:3]
    return path, dict(active=active, total=total, busiest=busiest, night=sum(hours[h] for h in list(range(7)) + [23]))
