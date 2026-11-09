#!/usr/bin/env python3
"""Документ «Спираль выпуска» (PDF) по turns.json и events.jsonl.

    python3 render_spiral.py build/spiral/turns.json --events build/spiral/events.jsonl \\
        --out build/spiral/Спираль_выпуска_1.3.0.pdf --project "Плата ввода-вывода" --tz +05:00

Нужны matplotlib, numpy, reportlab, Pillow. Разделы: занятость, как читать, две спирали и CI, сводка,
витки по порядку, развёртка, итоги, что не учтено. Тексты витков — поля name, result, notes в turns.json;
в модели можно задать "stands" (таблица стендов), "conclusions", "not_included", "intro".
"""
import argparse
import datetime as dt
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import spiral_figs as F  # noqa: E402
from collect_events import tz_arg  # noqa: E402
from report_style import P, build, bullets, figure, num, table  # noqa: E402
from reportlab.platypus import PageBreak  # noqa: E402
from spiral_common import parse_time, read_events  # noqa: E402


def h(m):
    return num(m / 60, 1)


def fails_word(f):
    return "сбой" if f == 1 else "сбоя" if 1 < f < 5 else "сбоев"


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("turns")
    ap.add_argument("--events", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--figdir")
    ap.add_argument("--project", default="", help="название изделия для подзаголовка и колонтитула")
    ap.add_argument("--tz", type=tz_arg, default=dt.timezone.utc)
    a = ap.parse_args(argv)
    model = json.load(open(a.turns, encoding="utf-8"))
    ev = read_events(a.events)
    out = a.figdir or os.path.join(os.path.dirname(os.path.abspath(a.out)), "fig")
    os.makedirs(out, exist_ok=True)
    v0, v1, v2 = model["versions"]
    rt, T = model["release_turn"], model["rules"]["time"]
    turns = model["turns"]
    tot = {t["n"]: sum(x["min"] for x in t["tasks"]) for t in turns}
    pre = sum(v for k, v in tot.items() if k <= rt)
    post = sum(v for k, v in tot.items() if k > rt)
    n_all = sum(x.get("n", 0) for t in turns for x in t["tasks"])
    f_all = sum(x.get("fails", 0) for t in turns for x in t["tasks"])
    n_pre = sum(x.get("n", 0) for t in turns if t["n"] <= rt for x in t["tasks"])
    f_pre = sum(x.get("fails", 0) for t in turns if t["n"] <= rt for x in t["tasks"])
    lane = {}
    for t in turns:
        for x in t["tasks"]:
            lane[x["lane"]] = lane.get(x["lane"], 0) + x["min"]
    tzl = a.tz.tzname(None).replace("UTC", "GMT") if a.tz.tzname(None) != "UTC" else "UTC"
    period = (parse_time(turns[0]["t0"]).astimezone(a.tz).date(), parse_time(turns[-1]["t1"]).astimezone(a.tz).date())
    if model.get("period"):
        period = tuple(dt.date.fromisoformat(x) for x in model["period"])
    cal, act = F.activity_calendar(ev, period, a.tz, T["session_gap_min"],
                                   "Занятость проектом: выпуск %s (%s–%s)" % (v1, period[0].strftime("%d.%m"),
                                                                              period[1].strftime("%d.%m.%Y")), out, tzl)
    fig = {"cal": cal,
           "s1": F.spiral(model, [t for t in turns if t["n"] <= rt],
                          "Спираль 1. От выпуска %s к выпуску %s: витки 1–%d" % (v0, v1, rt), v0, v1, out, "spiral1"),
           "chain": F.ci_chain(model, out), "gantt": F.gantt(model, out), "hours": F.turn_hours(model, out),
           "att": F.attempts(model, out)}
    conf = [t for t in turns if t["n"] > rt]
    if conf:
        rng = "виток %d" % conf[0]["n"] if len(conf) == 1 else "витки %d–%d" % (conf[0]["n"], conf[-1]["n"])
        fig["s2"] = F.spiral(model, conf, "Спираль 2. Подтверждение %s: %s" % (v1, rng), v1, "план " + v2, out,
                             "spiral2", (6.0, 4.8))
    foot = "%sспираль выпуска %s (от %s к %s)" % ((a.project + ": ") if a.project else "", v1, v0, v1)

    st = [P("Спираль выпуска %s:<br/>от %s к отлаженному выпуску" % (v1, v0), "title"),
          P((a.project + ". " if a.project else "") + (model.get("intro") or
            "Какие витки работы привели к выпуску, где шла проверка и сколько времени уходит на каждую задачу."), "sub"),
          P("Период: %s — %s" % (period[0].strftime("%d.%m.%Y"), period[1].strftime("%d.%m.%Y")), "date")]
    kinds = {}
    for e in ev:
        kinds[e["kind"]] = kinds.get(e["kind"], 0) + 1
    names = {"commit": "коммиты", "merge": "слияния", "tag": "теги", "run": "прогоны сценариев",
             "job": "задания стенда", "local_ci": "локальный CI", "recording": "записи испытаний", "manual": "ручные"}
    top = ", ".join(k.strftime("%d.%m") + " — " + num(v, 1) + " ч" for v, k in act["busiest"])
    st += [P("1. Занятость проектом", "h1"),
           P("Календарь показывает, сколько часов в день шла работа по выпуску: квадрат — день, столбец — неделя, "
             "месяцы целиком. Цвет — часы активности по журналам; пересекающиеся интервалы считаются один раз, "
             "промежутки короче %d мин — работой. Это занятость в течение дня, а не сумма задач." % T["session_gap_min"]),
           figure(fig["cal"], "Календарь занятости. Справа — в какие часы суток шла работа (сумма за период)."),
           P("Событий в журналах: " + ", ".join("%s — %d" % (names.get(k, k), v) for k, v in sorted(kinds.items()))
             + ". Самые загруженные дни: %s." % top)]
    st += [P("2. Как читать документ", "h1"),
           P("Работа от выпуска до выпуска показана спиралью: каждый виток проходит четыре сектора — %s — и "
             "заканчивается новым отлаженным состоянием. Спираль 1 приводит от %s к %s, спираль 2 — проверки после "
             "выпуска, которые дают план %s." % (", ".join(model["rules"]["sectors"]), v0, v1, v2)),
           table([["Что", "Как оценено"],
                  ["Прогоны на стендах, задания, локальный CI", "машинное время из журналов плюс %d мин на запуск "
                   "человеком и %d мин на разбор каждого сбоя" % (T["launch_min"], T["fail_analysis_min"])],
                  ["Смена платы", "%d мин" % T["board_swap_min"]],
                  ["CI сервера", "оценка: конвейер ветки, MR или слияния — %d мин, тега — %d мин, образа — %d мин"
                   % (T["pipeline_branch_min"], T["pipeline_tag_min"], T["pipeline_image_min"])],
                  ["Испытания", "длительность записей и ручных событий"],
                  ["Изменения, ТЗ, документы", "оценка по занятости между коммитами или вручную"]], [0.36, 0.64])]
    if model.get("stands"):
        st += [P("Стенды", "h2"), table([["Стенд", "Что есть", "Для чего"]] + model["stands"], [0.18, 0.46, 0.36])]
    st += [PageBreak(), P("3. Две спирали", "h1"),
           figure(fig["s1"], "Рис. 1. Спираль 1. Цвет — сектор витка, толщина — время в секторе, пунктир — сектор "
                             "без задач, красный крест — сбой прогона с правкой и повтором.", 0.86),
           P("Спираль 1 — %s ч, %d запусков, из них %d закончились сбоем и повтором." % (h(pre), n_pre, f_pre))]
    if conf:
        st += [figure(fig["s2"], "Рис. 2. Спираль 2: проверки выпуска; замечания уходят в план %s." % v2, 0.66),
               P("Спираль 2 — %s ч." % h(post))]
    st += [P("CI проходится многократно", "h2"),
           P("Каждое изменение проходит CI на каждой ступени пути к выпуску: ветка, MR, слияние в линию, MR в "
             "основную ветку, тег. За выпуск — %d конвейеров." % sum(c[1] for c in model["ci_chain"])),
           figure(fig["chain"], "Рис. 3. Ступени CI сервера и число конвейеров на каждой.")]
    rows = [["№", "Виток", "Даты", "Результат", "Запусков (сбоев)", "Часы"]]
    for t in turns:
        n = sum(x.get("n", 0) for x in t["tasks"])
        f = sum(x.get("fails", 0) for x in t["tasks"])
        rows.append([str(t["n"]), t["name"], t["dates"], t["result"], (f"{n}" + (f" ({f})" if f else "")) if n else "—",
                     h(tot[t["n"]])])
    rows += [["", "До выпуска", "", "", f"{n_pre} ({f_pre})", h(pre)],
             ["", "Подтверждение", "", "", f"{n_all - n_pre} ({f_all - f_pre})", h(post)],
             ["", "Всего", "", "", f"{n_all} ({f_all})", h(pre + post)]]
    st += [P("4. Сводка витков", "h1"), table(rows, [0.05, 0.25, 0.1, 0.38, 0.12, 0.1]), P("5. Витки по порядку", "h1")]
    for t in turns:
        r = [["Задача", "Где", "Мин", "Оценка"]]
        for x in t["tasks"]:
            src = "журнал + запуск" if x["src"] == "fact" else "оценка"
            if x.get("n"):
                f = x.get("fails", 0)
                src += "; %d зап." % x["n"] + (", %d %s" % (f, fails_word(f)) if f else "")
            r.append([x["name"], x["lane"], num(x["min"], 0), src])
        r.append(["Итого", "", num(tot[t["n"]], 0), h(tot[t["n"]]) + " ч"])
        st += [P("Виток %d. %s (%s)" % (t["n"], t["name"], t["dates"]), "h2"), P(t.get("notes") or t["result"]),
               table(r, [0.46, 0.24, 0.08, 0.22])]
    st += [PageBreak(), P("6. Развёртка по времени", "h1"),
           figure(fig["gantt"], "Рис. 4. Задачи витков подряд по месту выполнения; номера сверху — витки, красная "
                                "линия — выпуск готов."),
           figure(fig["hours"], "Рис. 5. Часы по виткам и секторам."),
           figure(fig["att"], "Рис. 6. Запуски по виткам: зелёные прошли, красные — сбой и повтор."),
           table([["Вид работ", "Часы", "Доля"]] + [[ln, h(lane[ln]), num(100 * lane[ln] / (pre + post), 0) + " %"]
                                                   for ln in F.lanes(model)] + [["Всего", h(pre + post), "100 %"]],
                 [0.5, 0.25, 0.25])]
    st += [P("7. Итоги", "h1"),
           P("До выпуска — %s ч, подтверждение — %s ч; запусков %d, сбоев с повтором %d." % (h(pre), h(post), n_all, f_all))]
    st += bullets(model.get("conclusions") or [])
    st += [P("8. Что не учтено", "h1")] + bullets(model.get("not_included") or [
        "сборка и наладка стендов и окружения;", "перерывы, ожидание ответов и работа по другим проектам;",
        "фактическая длительность конвейеров CI сервера, если её нет в журналах."])
    st += [P("Данные: " + (model.get("sources") or "журнал событий %s, модель витков %s." %
                           (os.path.basename(a.events), os.path.basename(a.turns))), "data")]
    build(a.out, st, foot, "Спираль выпуска %s" % v1)
    print(a.out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
