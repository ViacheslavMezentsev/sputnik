#!/usr/bin/env python3
"""Демо-данные спирали (вымышленное изделие): assets/demo/events.jsonl и turns.json.

Данные детерминированные: одна и та же генерация даёт одни и те же файлы. По ним строится пример на сайте
(site_svg.py) и пробный PDF (render_spiral.py), не раскрывая журналов настоящих проектов.
"""
import datetime as dt
import json
import os
import pathlib
import random
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from spiral_common import iso, load_rules  # noqa: E402

OUT = pathlib.Path(__file__).resolve().parents[1] / "assets" / "demo"
UTC = dt.timezone.utc
TURNS = [  # название, дата начала, дни, (план, изменение) мин, запусков, сбоев, CI сервера мин
    ("План выпуска", "2026-09-01", 1, (90, 0), 0, 0, 0),
    ("Окружение CI", "2026-09-03", 2, (30, 120), 4, 1, 40),
    ("Драйвер датчика", "2026-09-08", 3, (60, 300), 14, 4, 30),
    ("Протокол обмена", "2026-09-15", 4, (45, 360), 18, 6, 30),
    ("Режим энергосбережения", "2026-09-22", 2, (40, 180), 9, 2, 30),
    ("Мелкие исправления", "2026-09-28", 1, (0, 90), 6, 1, 20),
    ("Полная проверка на двух платах", "2026-10-01", 2, (20, 60), 6, 2, 20),
    ("Выпуск", "2026-10-05", 1, (60, 15), 3, 1, 75),
    ("Комплект выпуска", "2026-10-06", 1, (45, 0), 8, 0, 0),
    ("Испытания на стенде заказчика", "2026-10-12", 1, (90, 0), 0, 0, 0),
    ("Удалённый стенд", "2026-10-14", 1, (45, 0), 12, 1, 0),
]
RELEASE = 9


def main():
    rnd = random.Random(20261005)
    rules = load_rules()
    T = rules["time"]
    OUT.mkdir(parents=True, exist_ok=True)
    events, turns = [], []
    for n, (name, day, days, (plan, change), runs, fails, ci) in enumerate(TURNS, 1):
        d0 = dt.datetime.fromisoformat(day + "T04:00:00+00:00")
        tasks = []
        if plan:
            tasks.append({"name": "ТЗ и документы", "lane": "План и ТЗ", "min": plan, "src": "est", "n": 0, "fails": 0})
        if change:
            tasks.append({"name": "Изменения и сценарии", "lane": "Изменение", "min": change, "src": "est", "n": 0,
                          "fails": 0})
        if runs:
            sec = 0
            for k in range(runs):
                t0 = d0 + dt.timedelta(days=rnd.randrange(days), hours=rnd.uniform(0.5, 9))
                s = rnd.randint(30, 900)
                sec += s
                events.append({"t0": iso(t0), "t1": iso(t0 + dt.timedelta(seconds=s)), "kind": "run",
                               "source": "hil", "status": "FAIL" if k < fails else "PASS", "seconds": s,
                               "subject": "SCENARIO_%02d" % rnd.randint(1, 40)})
            lane = "Удалённый стенд" if n == 11 else "Локальный стенд"
            tasks.append({"name": "Прогоны сценариев", "lane": lane, "src": "fact", "n": runs, "fails": fails,
                          "min": round(sec / 60 + runs * T["launch_min"] + fails * T["fail_analysis_min"], 1)})
        if n in (3, 4, 7):
            tasks.append({"name": "Смена платы", "lane": "Смена платы", "min": T["board_swap_min"], "src": "est", "n": 0,
                          "fails": 0})
        if ci:
            tasks.append({"name": "CI сервера: ветка, MR, слияния", "lane": "CI сервера", "min": ci, "src": "est", "n": 0,
                          "fails": 0})
        if n == 10:
            t0 = d0 + dt.timedelta(hours=1)
            events.append({"t0": iso(t0), "t1": iso(t0 + dt.timedelta(hours=4)), "kind": "recording",
                           "source": "manual", "subject": "запись испытания"})
            tasks.append({"name": "Испытание с записью телеметрии", "lane": "Лаборатория", "min": 240, "src": "fact",
                          "n": 0, "fails": 0})
        work = plan + change
        k = 0
        while work > 0:
            t1 = d0 + dt.timedelta(days=k % days, hours=rnd.uniform(1, 10))
            events.append({"t0": iso(t1 - dt.timedelta(minutes=T["commit_window_min"])), "t1": iso(t1), "kind": "commit",
                           "source": "git", "subject": "feat: шаг %d.%d" % (n, k)})
            work -= rnd.randint(25, 70)
            k += 1
        turns.append({"n": n, "spiral": 1 if n <= RELEASE else 2, "branch": "", "name": name,
                      "dates": "%s–%s" % (d0.strftime("%d.%m"), (d0 + dt.timedelta(days=days - 1)).strftime("%d.%m")),
                      "result": "", "notes": "", "t0": iso(d0), "t1": iso(d0 + dt.timedelta(days=days, hours=-12)),
                      "commits": [], "tasks": tasks})
    model = {"schema": 1, "versions": ["2.0.0", "2.1.0", "2.2.0"], "release_turn": RELEASE, "line": "release/2.x",
             "rules": rules, "period": ["2026-09-01", "2026-10-15"],
             "ci_chain": [["push\nветки", 7, "рабочие ветки"], ["MR\nв линию", 6, ""], ["слияние\nв линию", 6, ""],
                          ["MR\nв main", 1, ""], ["слияние\nв main", 1, ""], ["тег", 1, "выпуск"]],
             "turns": turns}
    with open(OUT / "events.jsonl", "w", encoding="utf-8") as f:
        for e in sorted(events, key=lambda e: e["t0"]):
            f.write(json.dumps(e, ensure_ascii=False) + "\n")
    (OUT / "turns.json").write_text(json.dumps(model, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(OUT / "turns.json", len(events), "событий")


if __name__ == "__main__":
    main()
