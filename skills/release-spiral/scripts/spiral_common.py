"""Общее для скриптов спирали выпуска: журнал событий, правила, время."""
import datetime as dt
import json
import pathlib
import re

HERE = pathlib.Path(__file__).resolve().parent
UTC = dt.timezone.utc


def load_rules(path=None):
    rules = json.loads((HERE / "rules.json").read_text(encoding="utf-8"))
    if path:
        user = json.loads(pathlib.Path(path).read_text(encoding="utf-8"))
        for key, value in user.items():
            if isinstance(value, dict) and isinstance(rules.get(key), dict):
                rules[key].update(value)
            else:
                rules[key] = value
    return rules


def parse_time(text, tz=None):
    """ISO 8601, 'YYYYMMDDTHHMMSS[.f]Z' (результаты stm32-gdbtest) или 'YYYYMMDD-HHMMSS' (с tz)."""
    text = text.strip()
    m = re.fullmatch(r"(\d{8})T(\d{6})(\.\d+)?Z", text)
    if m:
        return dt.datetime.strptime(m.group(1) + m.group(2), "%Y%m%d%H%M%S").replace(tzinfo=UTC)
    m = re.fullmatch(r"(\d{8})-(\d{6})", text)
    if m:
        return dt.datetime.strptime(m.group(1) + m.group(2), "%Y%m%d%H%M%S").replace(tzinfo=tz or UTC)
    text = re.sub(r"(\.\d{6})\d+", r"\1", text)          # .NET пишет 7 знаков долей секунды
    t = dt.datetime.fromisoformat(text.replace("Z", "+00:00"))
    return t if t.tzinfo else t.replace(tzinfo=tz or UTC)


def iso(t):
    return t.astimezone(UTC).isoformat(timespec="seconds")


def read_events(path):
    out = []
    for line in pathlib.Path(path).read_text(encoding="utf-8").splitlines():
        if line.strip():
            e = json.loads(line)
            e["_t0"], e["_t1"] = parse_time(e["t0"]), parse_time(e["t1"])
            out.append(e)
    out.sort(key=lambda e: e["_t0"])
    return out


def write_events(path, events):
    with open(path, "w", encoding="utf-8") as f:
        for e in sorted(events, key=lambda e: e["t0"]):
            f.write(json.dumps({k: v for k, v in e.items() if not k.startswith("_")}, ensure_ascii=False) + "\n")


def commit_sector(subject, rules):
    """Сектор по теме коммита: plan, change, check, release (по умолчанию change)."""
    for sector in ("plan", "check", "release", "change"):
        if any(re.search(p, subject) for p in rules["commit_types"][sector]):
            return sector
    return "change"


def merge_branch(subject, rules):
    for p in rules["merge_patterns"]:
        m = re.search(p, subject)
        if m:
            d = m.groupdict()
            return d.get("src"), d.get("dst")
    return None, None


def union_minutes(intervals, gap_min=0):
    """Сумма объединения интервалов (минуты); промежутки до gap_min считаются занятостью."""
    total, cur = 0.0, None
    gap = dt.timedelta(minutes=gap_min)
    for a, b in sorted(intervals):
        if cur and a <= cur[1] + gap:
            cur[1] = max(cur[1], b)
        else:
            if cur:
                total += (cur[1] - cur[0]).total_seconds() / 60
            cur = [a, b]
    if cur:
        total += (cur[1] - cur[0]).total_seconds() / 60
    return total
