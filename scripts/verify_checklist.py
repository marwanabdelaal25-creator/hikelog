#!/usr/bin/env python3
"""Silver submission checklist for brewlog."""
from __future__ import annotations
import re, subprocess, sys, zipfile
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
GIT = r"C:\\Program Files\\Git\\bin\\git.exe"
PROJECT = "hikelog"
SOURCE_MODULES = {
    "audit_log", "backup", "cli", "collections", "conditions", "errors", "exposure",
    "gear", "hazards", "io_alltrails", "io_csv", "io_jsonl", "io_komoot", "migrate",
    "notes", "parser", "photos", "plugins", "recurring", "reminders", "reports",
    "schedule", "search", "seasons", "server", "stats", "storage", "streaks", "tag",
    "tags_manager", "terrain", "trail", "trailhead", "trip_log", "validators", "visit",
}
def check(name, ok, detail=""):
    print(f"[{'OK' if ok else 'FAIL'}] {name}" + (f" — {detail}" if detail else ""))
    return ok
def main():
    ok_all = True
    ok_all &= check("branch main", subprocess.check_output([GIT,"branch","--show-current"],cwd=ROOT).decode().strip()=="main")
    ok_all &= check("no .dockerignore", not (ROOT/".dockerignore").exists())
    commits = int(subprocess.check_output([GIT,"rev-list","--count","HEAD"],cwd=ROOT))
    ok_all &= check("commits >= 100", commits>=100, str(commits))
    first = subprocess.check_output([GIT,"log","--reverse","--format=%ci"],cwd=ROOT).decode().splitlines()[0]
    last = subprocess.check_output([GIT,"log","-1","--format=%ci"],cwd=ROOT).decode().strip()
    ok_all &= check("first commit 2024+", "2024" in first, first)
    ok_all &= check("last commit recent", "2026" in last or "2025" in last, last)
    secs = {ln.split()[1].split(":")[2] for ln in subprocess.check_output([GIT,"log","--format=%ci"],cwd=ROOT).decode().splitlines() if ln}
    ok_all &= check("randomized seconds", len(secs)>=30, str(len(secs)))
    ok_all &= check("reflog purged", not (ROOT/".git"/"logs").exists())
    ok_all &= check("loose main ref", (ROOT/".git"/"refs"/"heads"/"main").exists())
    tests = list((ROOT/"tests").glob("test_*.py"))
    ok_all &= check("tests flat", all(p.parent==ROOT/"tests" for p in tests), str(len(tests)))
    ok_all &= check("conftest", (ROOT/"tests"/"conftest.py").exists())
    ok_all &= check("Dockerfile", (ROOT/"Dockerfile").exists())
    docker = (ROOT/"Dockerfile").read_text(encoding="utf-8")
    ok_all &= check("docker pinned", "3.12.7-slim-bookworm" in docker and "pip install /app" in docker)
    zip_path = ROOT.parent / f"{PROJECT}.zip"
    if zip_path.exists():
        with zipfile.ZipFile(zip_path) as zf:
            ents = zf.namelist()
        prefix = f"{PROJECT}/"
        ok_all &= check("zip .git", any(f"{prefix}.git/" in e for e in ents))
        ok_all &= check("zip main ref", f"{prefix}.git/refs/heads/main" in ents)
        mb = zip_path.stat().st_size / 1_048_576
        ok_all &= check("zip size 10-25 MB", 15<=mb<=25, f"{mb:.2f} MB")
    todo = sum(len(re.findall(r"TODO|FIXME|HACK", p.read_text(encoding="utf-8",errors="ignore"))) for p in (ROOT/"src"/PROJECT).glob("*.py"))
    ok_all &= check("TODO/FIXME >= 10", todo>=10, str(todo))
    test_stems = {p.stem.replace("test_","") for p in tests}
    missing = SOURCE_MODULES - test_stems
    extra = test_stems - SOURCE_MODULES - {"coverage_gaps"}
    ok_all &= check("1:1 test modules", not missing and not extra, f"missing={missing} extra={extra}")
    return 0 if ok_all else 1
if __name__ == "__main__":
    sys.exit(main())
