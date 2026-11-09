#!/usr/bin/env python3
"""Черновик витков спирали из журнала событий: events.jsonl -> turns.json.

Правила по умолчанию (rules.json, переопределяются --rules):
  - виток — ветка, слитая в линию; внутри ветки виток заканчивается коммитом проверки (`test…`),
    за которым идёт не проверка (--no-split-on-check отключает);
  - прямые коммиты в линию — виток на группу с перерывом больше direct_commit_gap_h;
  - прогоны, CI и записи относятся к витку, который закончился первым после события;
  - события после последнего коммита — спираль 2 (подтверждение), витки по перерыву confirm_gap_h;
  - время: прогон — машинное + launch_min (+ fail_analysis_min при не PASS); конвейеры по числу слияний
    и тегов; изменения и документы — по занятости между коммитами (оценка).
Черновик редактирует агент: названия, описания, оценки, ручные задачи (`"src": "est"`).

    python3 build_turns.py build/spiral/events.jsonl --line release/1.x --versions 1.2.0,1.3.0,1.4.0 \\
        --out build/spiral/turns.json
"""
import argparse
import datetime as dt
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from spiral_common import commit_sector, iso, load_rules, read_events, union_minutes  # noqa: E402


def segments(commits, split_on_check, rules):
    """Разбить коммиты одной ветки на витки."""
    if not split_on_check:
        return [commits]
    out, cur = [], []
    for i, c in enumerate(commits):
        cur.append(c)
        here = commit_sector(c["subject"], rules) == "check"
        nxt = commit_sector(commits[i + 1]["subject"], rules) if i + 1 < len(commits) else None
        if here and nxt not in (None, "check"):
            out.append(cur)
            cur = []
    if cur:
        out.append(cur)
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("events")
    ap.add_argument("--line", required=True, help="интеграционная ветка (куда сливаются рабочие ветки)")
    ap.add_argument("--main", default="main")
    ap.add_argument("--versions", required=True, help="предыдущая,текущая,следующая")
    ap.add_argument("--rules")
    ap.add_argument("--no-split-on-check", action="store_true")
    ap.add_argument("--out", required=True)
    a = ap.parse_args(argv)
    rules = load_rules(a.rules)
    T = rules["time"]
    ev = read_events(a.events)
    commits = [e for e in ev if e["kind"] == "commit"]
    merges = [e for e in ev if e["kind"] == "merge"]
    tags = [e for e in ev if e["kind"] == "tag"]

    # 1. Витки по коммитам
    groups = []
    by_branch = {}
    for c in commits:
        b = c.get("branch") or ""
        if b and b not in (a.line, a.main):
            by_branch.setdefault(b, []).append(c)
    for b, cs in by_branch.items():
        for seg in segments(cs, not a.no_split_on_check, rules):
            groups.append({"branch": b, "commits": seg})
    direct = [c for c in commits if (c.get("branch") or "") in ("", a.line, a.main)]
    cur = []
    for c in direct:
        if cur and c["_t0"] - cur[-1]["_t1"] > dt.timedelta(hours=T["direct_commit_gap_h"]):
            groups.append({"branch": "", "commits": cur})
            cur = []
        cur.append(c)
    if cur:
        groups.append({"branch": "", "commits": cur})
    groups.sort(key=lambda g: g["commits"][-1]["_t1"])
    last_commit = max(c["_t1"] for c in commits)
    release_t = max([t["_t1"] for t in tags] + [m["_t1"] for m in merges if m.get("into") == a.main] + [last_commit])

    # 2. Спираль 2: события после выпуска, по перерывам
    after = [e for e in ev if e["_t0"] > release_t and e["kind"] not in ("commit", "merge", "tag")]
    confirm, cur = [], []
    for e in after:
        if cur and e["_t0"] - cur[-1]["_t1"] > dt.timedelta(hours=T["confirm_gap_h"]):
            confirm.append(cur)
            cur = []
        cur.append(e)
    if cur:
        confirm.append(cur)

    # 3. Отнесение событий к виткам спирали 1: первый виток, закончившийся после события
    ends = [g["commits"][-1]["_t1"] for g in groups]
    for g in groups:
        g["events"] = []
    for e in ev:
        if e["kind"] in ("commit", "tag") or e["_t0"] > release_t:
            continue
        if e["kind"] == "merge":
            # слияние ветки — к последнему витку этой ветки; слияние в main — к последнему витку
            idx = max((i for i, g in enumerate(groups) if g["branch"] and g["branch"] == e.get("branch")),
                      default=len(groups) - 1)
        else:
            idx = next((i for i, t in enumerate(ends) if t >= e["_t0"]), len(groups) - 1)
        groups[idx]["events"].append(e)
    if tags:
        groups[-1]["events"] += tags

    def tasks_for(g_events, g_commits, branch, first_of_branch):
        tasks = []
        lane_of = {"local": "Локальный стенд", "remote": "Удалённый стенд"}
        runs = {}
        for e in g_events:
            if e["kind"] in ("run", "job"):
                key = (e["source"], lane_of.get(e.get("stand"), "Локальный стенд"))
                r = runs.setdefault(key, {"n": 0, "fails": 0, "sec": 0.0, "names": []})
                r["n"] += 1
                r["fails"] += e.get("status") not in ("PASS", "SKIP")
                r["sec"] += float(e.get("seconds") or 0)
                if len(r["names"]) < 3:
                    r["names"].append(e.get("case") or e.get("subject", ""))
        for (source, lane), r in runs.items():
            m = r["sec"] / 60 + r["n"] * T["launch_min"] + r["fails"] * T["fail_analysis_min"]
            name = ("Прогоны сценариев" if source == "hil" else "Задания стенда") + ": " + ", ".join(r["names"]) \
                + (" и др." if r["n"] > len(r["names"]) else "")
            tasks.append({"name": name, "lane": lane, "min": round(m, 1), "src": "fact", "n": r["n"],
                          "fails": r["fails"]})
        nci = sum(1 for e in g_events if e["kind"] == "local_ci")
        if nci:
            tasks.append({"name": "Локальный CI", "lane": "Локальный CI и скрипты",
                          "min": nci * (T["local_ci_min"] + T["launch_min"]), "src": "fact", "n": nci, "fails": 0})
        for e in g_events:
            if e["kind"] in ("recording", "manual"):
                dur = (e["_t1"] - e["_t0"]).total_seconds() / 60
                tasks.append({"name": e.get("subject", ""), "lane": e.get("lane") or
                              ("Лаборатория" if e["kind"] == "recording" else "Ручные испытания"),
                              "min": round(float(e.get("minutes") or dur), 1), "src": "fact", "n": 0, "fails": 0})
        gm = [e for e in g_events if e["kind"] == "merge"]
        pipes = len(gm) * 2 + (1 if branch and first_of_branch else 0)
        if pipes:
            tasks.append({"name": "CI сервера: push, MR и слияния (%d конвейеров)" % pipes, "lane": "CI сервера",
                          "min": pipes * T["pipeline_branch_min"], "src": "est", "n": 0, "fails": 0})
        if any(e["kind"] == "tag" for e in g_events):
            tasks.append({"name": "CI сервера: тег — сборки, пакет, релиз", "lane": "CI сервера",
                          "min": T["pipeline_tag_min"], "src": "est", "n": 0, "fails": 0})
        if g_commits:
            busy = union_minutes([(c["_t0"], c["_t1"]) for c in g_commits], T["session_gap_min"])
            count = {"plan": 0, "change": 0, "check": 0, "release": 0}
            for c in g_commits:
                count[commit_sector(c["subject"], rules)] += 1
            total = sum(count.values())
            plan = busy * (count["plan"] + count["release"]) / total
            change = busy - plan
            if plan:
                tasks.insert(0, {"name": "ТЗ, памятка и документы (%d коммитов)" % (count["plan"] + count["release"]),
                                 "lane": "План и ТЗ", "min": round(plan, 0), "src": "est", "n": 0, "fails": 0})
            if change:
                tasks.insert(1 if plan else 0, {"name": "Изменения и сценарии (%d коммитов)" % (count["change"] + count["check"]),
                                                "lane": "Изменение", "min": round(change, 0), "src": "est", "n": 0,
                                                "fails": 0})
        return tasks

    turns, seen = [], set()
    for i, g in enumerate(groups, 1):
        cs = g["commits"]
        first = g["branch"] not in seen
        seen.add(g["branch"])
        turns.append({"n": i, "spiral": 1, "branch": g["branch"],
                      "name": (g["branch"].split("/")[-1] if g["branch"] else "Прямые коммиты") + ": " + cs[0]["subject"][:60],
                      "dates": "%s–%s" % (cs[0]["_t0"].strftime("%d.%m"), cs[-1]["_t1"].strftime("%d.%m")),
                      "result": "; ".join(c["subject"] for c in cs[-2:])[:160], "notes": "",
                      "t0": iso(min([cs[0]["_t0"]] + [e["_t0"] for e in g["events"]])), "t1": iso(cs[-1]["_t1"]),
                      "commits": [c["ref"] for c in cs],
                      "tasks": tasks_for(g["events"], cs, g["branch"], first)})
    release_turn = len(turns)
    for k, grp in enumerate(confirm, 1):
        turns.append({"n": release_turn + k, "spiral": 2, "branch": "", "name": "Подтверждение %d" % k,
                      "dates": "%s–%s" % (grp[0]["_t0"].strftime("%d.%m"), grp[-1]["_t1"].strftime("%d.%m")),
                      "result": "", "notes": "", "t0": iso(grp[0]["_t0"]), "t1": iso(grp[-1]["_t1"]), "commits": [],
                      "tasks": tasks_for(grp, [], "", False)})
    chain = [["push\nветки", len(by_branch), "рабочие ветки"],
             ["MR\nв линию", sum(1 for m in merges if m.get("into") == a.line), ""],
             ["слияние\nв линию", sum(1 for m in merges if m.get("into") == a.line), ""],
             ["MR\nв " + a.main, sum(1 for m in merges if m.get("into") == a.main), ""],
             ["слияние\nв " + a.main, sum(1 for m in merges if m.get("into") == a.main), ""],
             ["тег", len(tags), "выпуск"]]
    model = {"schema": 1, "versions": a.versions.split(","), "release_turn": release_turn, "line": a.line,
             "rules": rules, "ci_chain": chain, "turns": turns}
    with open(a.out, "w", encoding="utf-8") as f:
        json.dump(model, f, ensure_ascii=False, indent=1)
    n = sum(t["n"] for tt in turns for t in tt["tasks"])
    print("%s: витков %d (спираль 1 — %d, спираль 2 — %d), запусков %d" % (
        a.out, len(turns), release_turn, len(turns) - release_turn, n))
    return 0


if __name__ == "__main__":
    sys.exit(main())
