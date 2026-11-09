#!/usr/bin/env python3
"""Журнал событий для спирали выпуска: git, прогоны, CI, записи испытаний -> events.jsonl.

Каждое событие — строка JSON: t0, t1 (ISO, UTC), kind, source, subject и поля источника.
Источники включаются ключами; ничего не угадывается: что не найдено, то в журнал не попадает.

    python3 collect_events.py --repo . --range v1.2.0..v1.3.0 --out build/spiral/events.jsonl \\
        --hil-runs 'build/*-hil/hwtest/runs' --bridge-results ../stand-bridge/results --bridge-repo app \\
        --local-ci 'build/local-ci-*' --local-tz +05:00 --recordings recordings.csv --manual manual.csv

recordings.csv и manual.csv: t0,t1,kind,subject[,lane][,stand] (время ISO с зоной).
"""
import argparse
import csv
import datetime as dt
import glob
import json
import os
import pathlib
import re
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from spiral_common import UTC, iso, load_rules, merge_branch, parse_time, write_events  # noqa: E402


def tz_arg(text):
    m = re.fullmatch(r"([+-])(\d{2}):?(\d{2})", text)
    if not m:
        raise argparse.ArgumentTypeError("зона вида +05:00")
    sign = 1 if m.group(1) == "+" else -1
    return dt.timezone(sign * dt.timedelta(hours=int(m.group(2)), minutes=int(m.group(3))))


def git(repo, *args):
    return subprocess.run(["git", "-C", repo, "-c", "core.autocrlf=true", *args], capture_output=True, text=True,
                          check=True).stdout


def git_events(repo, rng, rules):
    """Коммиты и слияния диапазона; у коммитов ветки — имя ветки из темы слияния, которое их принесло."""
    out = []
    log = git(repo, "log", "--reverse", "--format=%H%x1f%P%x1f%aI%x1f%s", rng)
    rows = [line.split("\x1f") for line in log.splitlines() if line]
    branch_of = {}
    for sha, parents, _t, subject in rows:
        ps = parents.split()
        if len(ps) > 1:
            src, _dst = merge_branch(subject, rules)
            if src:
                for c in git(repo, "rev-list", "%s..%s" % (ps[0], ps[1])).split():
                    branch_of.setdefault(c, src)
    first = set(git(repo, "rev-list", "--first-parent", rng.split("..")[-1] if ".." in rng else rng).split())
    for sha, parents, t, subject in rows:
        ps = parents.split()
        t1 = parse_time(t)
        merge = len(ps) > 1
        src, dst = merge_branch(subject, rules) if merge else (None, None)
        w = rules["time"]["merge_window_min" if merge else "commit_window_min"]
        out.append({"t0": iso(t1 - dt.timedelta(minutes=w)), "t1": iso(t1), "kind": "merge" if merge else "commit",
                    "source": "git", "ref": sha[:10], "subject": subject,
                    "branch": src if merge else branch_of.get(sha, ""), "into": dst or "",
                    "line": sha in first})
    a, _, b = rng.partition("..")
    for tag in git(repo, "tag", "--points-at", b or a).split():
        t = parse_time(git(repo, "log", "-1", "--format=%cI", tag).strip())
        out.append({"t0": iso(t), "t1": iso(t), "kind": "tag", "source": "git", "ref": tag, "subject": "тег " + tag})
    return out


def hil_runs(patterns, t0, t1):
    """Результаты stm32-gdbtest: <runs>/<run>/result.json (id, status, started_utc, duration_s)."""
    out = []
    for pattern in patterns:
        for path in glob.glob(os.path.join(pattern, "*", "result.json")):
            try:
                r = json.loads(pathlib.Path(path).read_text(encoding="utf-8"))
                a = parse_time(r["started_utc"])
            except Exception:
                continue
            if not (t0 <= a <= t1) or r.get("mode") not in (None, "hardware", "hw"):
                continue
            b = a + dt.timedelta(seconds=float(r.get("duration_s") or 0))
            remote = bool(r.get("remote_server")) or bool(r.get("server_host"))
            out.append({"t0": iso(a), "t1": iso(b), "kind": "run", "source": "hil", "case": r.get("id", ""),
                        "status": r.get("status", ""), "seconds": float(r.get("duration_s") or 0),
                        "stand": "remote" if remote else "local", "subject": r.get("id", ""),
                        "profile": pathlib.Path(path).parts[-5] if len(pathlib.Path(path).parts) > 5 else ""})
    return out


def bridge_results(directory, repo_name, t0, t1):
    """Журнал моста стенда: results/<id>/summary.json (started_utc, seconds, status, git.branch, steps)."""
    out = []
    for path in glob.glob(os.path.join(directory, "*", "summary.json")):
        try:
            s = json.loads(pathlib.Path(path).read_text(encoding="utf-8-sig"))
            a = parse_time(s["started_utc"])
        except Exception:
            continue
        if repo_name and s.get("repo") != repo_name or not (t0 <= a <= t1):
            continue
        sec = float(s.get("seconds") or 0)
        out.append({"t0": iso(a), "t1": iso(a + dt.timedelta(seconds=sec)), "kind": "job", "source": "bridge",
                    "case": pathlib.Path(path).parent.name, "status": s.get("status", ""), "seconds": sec,
                    "steps": len(s.get("steps") or []), "branch": (s.get("git") or {}).get("branch", ""),
                    "subject": pathlib.Path(path).parent.name})
    return out


def local_ci(patterns, tz, t0, t1):
    """Каталоги прогонов локального CI с меткой времени в имени (…-YYYYMMDD-HHMMSS-…)."""
    out = []
    for pattern in patterns:
        for path in glob.glob(pattern):
            m = re.search(r"(\d{8}-\d{6})", os.path.basename(path))
            if not m:
                continue
            a = parse_time(m.group(1), tz)
            if t0 <= a <= t1:
                out.append({"t0": iso(a), "t1": iso(a), "kind": "local_ci", "source": "local-ci",
                            "subject": os.path.basename(path)})
    return out


def csv_events(path, default_kind):
    out = []
    with open(path, encoding="utf-8") as f:
        for row in csv.DictReader(f):
            a, b = parse_time(row["t0"]), parse_time(row.get("t1") or row["t0"])
            e = {"t0": iso(a), "t1": iso(b), "kind": row.get("kind") or default_kind, "source": "manual",
                 "subject": row.get("subject", "")}
            for k in ("lane", "stand", "turn", "minutes"):
                if row.get(k):
                    e[k] = row[k]
            out.append(e)
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--repo", default=".")
    ap.add_argument("--range", required=True, help="диапазон git, например v1.2.0..v1.3.0")
    ap.add_argument("--until", help="конец окна событий кроме git (ISO), по умолчанию — время тега + 14 дней")
    ap.add_argument("--hil-runs", action="append", default=[], help="каталог runs stm32-gdbtest (glob)")
    ap.add_argument("--bridge-results", help="каталог results моста стенда")
    ap.add_argument("--bridge-repo", help="поле repo в summary.json, которое относится к проекту")
    ap.add_argument("--local-ci", action="append", default=[], help="glob каталогов локального CI")
    ap.add_argument("--local-tz", type=tz_arg, default=UTC, help="зона времени в именах каталогов, +05:00")
    ap.add_argument("--recordings", help="CSV записей испытаний (rosbag, анализатор)")
    ap.add_argument("--manual", help="CSV ручных событий (замер, нажатия, смена платы)")
    ap.add_argument("--rules")
    ap.add_argument("--out", required=True)
    a = ap.parse_args(argv)
    rules = load_rules(a.rules)
    events = git_events(a.repo, a.range, rules)
    times = [parse_time(e["t1"]) for e in events if e["kind"] in ("commit", "merge")]
    if not times:
        print("в диапазоне нет коммитов", file=sys.stderr)
        return 2
    start = a.range.partition("..")[0]
    lo = parse_time(git(a.repo, "log", "-1", "--format=%cI", start).strip()) if ".." in a.range else min(times)
    hi = parse_time(a.until) if a.until else max(times) + dt.timedelta(days=14)
    events += hil_runs(a.hil_runs, lo, hi)
    if a.bridge_results:
        events += bridge_results(a.bridge_results, a.bridge_repo, lo, hi)
    # Прогоны внутри задания моста — части этого задания: время и запуск считаются по заданию.
    jobs = [(parse_time(e["t0"]), parse_time(e["t1"])) for e in events if e["kind"] == "job"]
    events = [e for e in events if e["kind"] != "run" or
              not any(j0 <= parse_time(e["t0"]) <= j1 for j0, j1 in jobs)]
    events += local_ci(a.local_ci, a.local_tz, lo, hi)
    if a.recordings:
        events += csv_events(a.recordings, "recording")
    if a.manual:
        events += csv_events(a.manual, "manual")
    os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
    write_events(a.out, events)
    kinds = {}
    for e in events:
        kinds[e["kind"]] = kinds.get(e["kind"], 0) + 1
    print("%s: %d событий (%s)" % (a.out, len(events), ", ".join("%s %d" % kv for kv in sorted(kinds.items()))))
    return 0


if __name__ == "__main__":
    sys.exit(main())
