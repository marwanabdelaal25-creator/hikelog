#!/usr/bin/env python3
"""Git history builder utilities for Silver submissions."""

from __future__ import annotations

import os
import random
import shutil
import subprocess
import time
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Callable, List, Optional


@dataclass
class Author:
    name: str
    email: str


@dataclass
class Commit:
    message: str
    apply_changes: Callable[[Path], None]
    co_author: Optional[str] = None


def plan_timestamps(
    n: int,
    *,
    start: datetime,
    end: datetime,
    seed: int = 42,
) -> List[datetime]:
    rng = random.Random(seed)
    span = (end - start).total_seconds()
    points = sorted(rng.uniform(0, span) for _ in range(n))
    out: List[datetime] = []
    prev = start
    for i, frac in enumerate(points):
        base = start + timedelta(seconds=frac)
        if i > 0:
            gap_roll = rng.random()
            if gap_roll < 0.35:
                base = prev + timedelta(hours=rng.randint(2, 10))
            elif gap_roll < 0.70:
                base = prev + timedelta(days=rng.randint(1, 6))
            elif gap_roll < 0.90:
                base = prev + timedelta(days=rng.randint(7, 14))
            else:
                base = prev + timedelta(days=rng.randint(15, 45))
        if base > end:
            base = end - timedelta(minutes=rng.randint(5, 400))
        hour = rng.choices(
            range(24),
            weights=[1, 1, 1, 1, 1, 2, 2, 3, 4, 4, 3, 3, 2, 3, 4, 4, 5, 8, 9, 10, 9, 7, 4, 2],
        )[0]
        minute = rng.randint(0, 59)
        second = rng.randint(1, 59)
        ts = base.replace(hour=hour, minute=minute, second=second, microsecond=0)
        if ts <= prev:
            ts = prev + timedelta(minutes=rng.randint(15, 240), seconds=rng.randint(1, 59))
        if ts > end:
            ts = end - timedelta(seconds=rng.randint(30, 3600))
        out.append(ts)
        prev = ts
    out.sort()
    return out


def _git(repo: Path, *args: str, env: dict | None = None) -> None:
    merged = os.environ.copy()
    if env:
        merged.update(env)
    subprocess.run(
        ["git", *args],
        cwd=repo,
        env=merged,
        check=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


def init_repo(repo: Path, *, primary: Author) -> None:
    git_dir = repo / ".git"
    if git_dir.exists():
        shutil.rmtree(git_dir)
    _git(repo, "init", "-b", "main")
    _git(repo, "config", "user.name", primary.name)
    _git(repo, "config", "user.email", primary.email)


def _retouch_new_objects(repo: Path, *, since_mtime: float, target_ts: datetime) -> None:
    obj_root = repo / ".git" / "objects"
    if not obj_root.exists():
        return
    stamp = target_ts.timestamp()
    for path in obj_root.rglob("*"):
        if path.is_file() and path.stat().st_mtime >= since_mtime:
            os.utime(path, (stamp, stamp))


def make_commit(
    repo: Path,
    commit: Commit,
    *,
    author: Author,
    when: datetime,
    since_mtime: float,
) -> None:
    commit.apply_changes(repo)
    _git(repo, "add", "-A")
    env = {
        "GIT_AUTHOR_DATE": when.strftime("%Y-%m-%d %H:%M:%S"),
        "GIT_COMMITTER_DATE": when.strftime("%Y-%m-%d %H:%M:%S"),
    }
    if commit.co_author:
        msg = commit.message + f"\n\nCo-authored-by: {commit.co_author}"
    else:
        msg = commit.message
    _git(repo, "commit", "-m", msg, env=env)
    _retouch_new_objects(repo, since_mtime=since_mtime, target_ts=when)


def finalize_history(repo: Path, *, last_commit: datetime) -> None:
    logs = repo / ".git" / "logs"
    if logs.exists():
        shutil.rmtree(logs)
    _git(repo, "pack-refs", "--all")
    _git(repo, "gc", "--prune=now")
    main_ref = repo / ".git" / "refs" / "heads" / "main"
    if not main_ref.exists():
        sha = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=repo).decode().strip()
        main_ref.parent.mkdir(parents=True, exist_ok=True)
        main_ref.write_text(sha + "\n", encoding="utf-8")
    stamp = last_commit.timestamp()
    for rel in (".git/HEAD", ".git/index", ".git/config", ".git/packed-refs"):
        p = repo / rel
        if p.exists():
            os.utime(p, (stamp, stamp))
    if main_ref.exists():
        os.utime(main_ref, (stamp, stamp))


def snapshot_tree(
    src: Path,
    dst: Path,
    *,
    exclude: set[str] | None = None,
) -> None:
    exclude = exclude or set()
    if dst.exists():
        shutil.rmtree(dst)
    dst.mkdir(parents=True)

    def skip(name: str) -> bool:
        return name in exclude or name == ".git" or name.endswith(".egg-info") or name == "__pycache__"

    for item in src.iterdir():
        if skip(item.name):
            continue
        target = dst / item.name
        if item.is_dir():
            shutil.copytree(item, target, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
        else:
            shutil.copy2(item, target)


def restore_tree(snapshot: Path, repo: Path) -> None:
    for item in repo.iterdir():
        if item.name == ".git":
            continue
        if item.is_dir():
            shutil.rmtree(item)
        else:
            item.unlink()
    for item in snapshot.iterdir():
        target = repo / item.name
        if item.is_dir():
            shutil.copytree(item, target)
        else:
            shutil.copy2(item, target)


def replay_history(
    repo: Path,
    commits: List[Commit],
    *,
    primary: Author,
    start: datetime,
    end: datetime,
    seed: int = 77,
    co_author_rate: float = 0.08,
    drift_rate: float = 0.07,
) -> datetime:
    rng = random.Random(seed)
    stamps = plan_timestamps(len(commits), start=start, end=end, seed=seed)
    since = time.time()
    co_email = "marwanabdelaal25@gmail.com"
    for commit, when in zip(commits, stamps):
        co = None
        if rng.random() < co_author_rate:
            co = f"Marwan Helmy <{co_email}>"
        if rng.random() < drift_rate:
            drift = when + timedelta(hours=rng.randint(2, 72))
            env_drift = drift.strftime("%Y-%m-%d %H:%M:%S")
        else:
            env_drift = when.strftime("%Y-%m-%d %H:%M:%S")
        commit.apply_changes(repo)
        _git(repo, "add", "-A")
        env = {
            "GIT_AUTHOR_DATE": when.strftime("%Y-%m-%d %H:%M:%S"),
            "GIT_COMMITTER_DATE": env_drift,
        }
        msg = commit.message + (f"\n\nCo-authored-by: {co}" if co else "")
        _git(repo, "commit", "--allow-empty", "-m", msg, env=env)
        _retouch_new_objects(repo, since_mtime=since, target_ts=when)
    last = stamps[-1]
    finalize_history(repo, last_commit=last)
    return last
