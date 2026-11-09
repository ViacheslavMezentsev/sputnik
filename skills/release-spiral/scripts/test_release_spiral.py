#!/usr/bin/env python3
"""Проверка без оборудования: синтетический репозиторий и журнал стенда -> события -> витки (-> PDF).

PDF строится, только если доступны matplotlib, numpy, reportlab и Pillow; иначе этот шаг пропускается.
"""
import json
import os
import pathlib
import subprocess
import sys
import tempfile

HERE = pathlib.Path(__file__).resolve().parent


def sh(cwd, *args, env=None):
    subprocess.run(args, cwd=cwd, check=True, capture_output=True, env=env)


def commit(repo, subject, when):
    env = dict(os.environ, GIT_AUTHOR_DATE=when, GIT_COMMITTER_DATE=when, GIT_AUTHOR_NAME="t", GIT_AUTHOR_EMAIL="t@t",
               GIT_COMMITTER_NAME="t", GIT_COMMITTER_EMAIL="t@t")
    (repo / "f.txt").write_text(subject + "\n", encoding="utf-8")
    sh(repo, "git", "add", "f.txt", env=env)
    sh(repo, "git", "-c", "commit.gpgsign=false", "commit", "-q", "-m", subject, env=env)


def merge(repo, branch, into, when):
    env = dict(os.environ, GIT_AUTHOR_DATE=when, GIT_COMMITTER_DATE=when, GIT_AUTHOR_NAME="t", GIT_AUTHOR_EMAIL="t@t",
               GIT_COMMITTER_NAME="t", GIT_COMMITTER_EMAIL="t@t")
    sh(repo, "git", "checkout", "-q", into)
    sh(repo, "git", "-c", "commit.gpgsign=false", "merge", "-q", "--no-ff", "-X", "theirs", "-m",
       "Merge branch '%s' into '%s'" % (branch, into), branch, env=env)


def main():
    tmp = pathlib.Path(tempfile.mkdtemp())
    repo = tmp / "repo"
    repo.mkdir()
    sh(repo, "git", "init", "-q", "-b", "main")
    commit(repo, "chore: version 1.0.0", "2026-01-01T10:00:00+00:00")
    sh(repo, "git", "-c", "tag.gpgsign=false", "tag", "v1.0.0")
    sh(repo, "git", "checkout", "-q", "-b", "line")
    sh(repo, "git", "checkout", "-q", "-b", "feat-a")
    commit(repo, "docs(spec): revision 1.1", "2026-01-05T09:00:00+00:00")
    commit(repo, "feat(app): feature A", "2026-01-05T09:40:00+00:00")
    commit(repo, "test(hil): scenario A passes", "2026-01-05T10:30:00+00:00")
    commit(repo, "fix(app): issue B", "2026-01-05T11:00:00+00:00")
    commit(repo, "test(hil): scenario B passes", "2026-01-05T11:40:00+00:00")
    merge(repo, "feat-a", "line", "2026-01-05T12:00:00+00:00")
    commit(repo, "docs(changelog): 1.1.0", "2026-01-06T09:00:00+00:00")
    merge(repo, "line", "main", "2026-01-06T09:30:00+00:00")
    sh(repo, "git", "-c", "tag.gpgsign=false", "tag", "v1.1.0")
    results = tmp / "results"
    for i, (start, sec, status) in enumerate((("2026-01-05T10:00:00Z", 300, "FAIL"), ("2026-01-05T10:15:00Z", 300, "PASS"),
                                              ("2026-01-05T11:20:00Z", 600, "PASS"), ("2026-01-06T12:00:00Z", 900, "PASS"))):
        d = results / ("%03d-job" % i)
        d.mkdir(parents=True)
        (d / "summary.json").write_text(json.dumps({"repo": "app", "started_utc": start, "seconds": sec,
                                                    "status": status, "git": {"branch": "feat-a"}, "steps": [1]}),
                                        encoding="utf-8")
    events, turns = tmp / "events.jsonl", tmp / "turns.json"
    py = sys.executable
    subprocess.run([py, HERE / "collect_events.py", "--repo", repo, "--range", "v1.0.0..v1.1.0", "--out", events,
                    "--bridge-results", results, "--bridge-repo", "app"], check=True)
    subprocess.run([py, HERE / "build_turns.py", events, "--line", "line", "--versions", "1.0.0,1.1.0,1.2.0",
                    "--out", turns], check=True)
    m = json.loads(turns.read_text(encoding="utf-8"))
    s1 = [t for t in m["turns"] if t["spiral"] == 1]
    s2 = [t for t in m["turns"] if t["spiral"] == 2]
    assert len(s1) == 3, [t["name"] for t in s1]               # A, B (после test…), выпуск по прямому коммиту
    assert len(s2) == 1, s2                                    # задание после тега
    first = s1[0]["tasks"]
    stand = [x for x in first if x["src"] == "fact"]
    assert stand and stand[0]["n"] == 2 and stand[0]["fails"] == 1, first
    assert abs(stand[0]["min"] - (10 + 2 * 3 + 10)) < 0.01, stand[0]
    chain = {c[0].replace("\n", " "): c[1] for c in m["ci_chain"]}
    assert chain["MR в линию"] == 1 and chain["MR в main"] == 1 and chain["тег"] == 1, chain
    print("журнал и витки: OK")
    try:
        import matplotlib, numpy, reportlab, PIL  # noqa: F401
    except ImportError:
        print("PDF: пропущено (нет matplotlib/numpy/reportlab/Pillow)")
        return 0
    pdf = tmp / "spiral.pdf"
    subprocess.run([py, HERE / "render_spiral.py", turns, "--events", events, "--out", pdf], check=True,
                   capture_output=True)
    assert pdf.stat().st_size > 20000
    print("PDF: OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
