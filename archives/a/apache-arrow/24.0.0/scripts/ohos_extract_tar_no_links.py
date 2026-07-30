#!/usr/bin/env python3
"""Extract a tar archive while replacing links with ordinary copies.

Some HarmonyOS test filesystems reject symlink and hardlink creation.  This
helper is intended for upstream test probes where a third-party source archive
contains link entries that are not required to remain links.
"""

from __future__ import annotations

import argparse
import os
import shutil
import tarfile
from pathlib import Path


def safe_path(root: Path, name: str) -> Path:
    path = (root / name).resolve()
    root_resolved = root.resolve()
    if path != root_resolved and root_resolved not in path.parents:
        raise ValueError(f"archive member escapes destination: {name}")
    return path


def relative_link_path(link_path: Path, link_name: str) -> Path:
    return (link_path.parent / link_name).resolve()


def copy_entry(source: Path, dest: Path) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    if source.is_dir():
        if dest.exists():
            return
        shutil.copytree(source, dest, symlinks=False)
    elif source.is_file():
        shutil.copy2(source, dest)
    else:
        raise FileNotFoundError(f"link target is not a regular file or directory: {source}")


def extract_no_links(archive: Path, dest: Path) -> int:
    dest.mkdir(parents=True, exist_ok=True)
    link_members: list[tarfile.TarInfo] = []
    skipped = 0

    with tarfile.open(archive, "r:*") as tf:
        members = tf.getmembers()

        for member in members:
            target = safe_path(dest, member.name)
            if member.isdir():
                target.mkdir(parents=True, exist_ok=True)
            elif member.isreg():
                target.parent.mkdir(parents=True, exist_ok=True)
                src = tf.extractfile(member)
                if src is None:
                    raise RuntimeError(f"unable to read archive member: {member.name}")
                with src, target.open("wb") as out:
                    shutil.copyfileobj(src, out)
                try:
                    os.chmod(target, member.mode)
                except OSError:
                    pass
            elif member.issym() or member.islnk():
                link_members.append(member)
            else:
                skipped += 1

        for member in link_members:
            link_path = safe_path(dest, member.name)
            if member.issym():
                source = relative_link_path(link_path, member.linkname)
            else:
                source = safe_path(dest, member.linkname)
            copy_entry(source, link_path)

    print(f"archive={archive}")
    print(f"dest={dest}")
    print(f"links_copied={len(link_members)}")
    print(f"special_entries_skipped={skipped}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--archive", required=True, type=Path)
    parser.add_argument("--dest", required=True, type=Path)
    args = parser.parse_args()
    return extract_no_links(args.archive, args.dest)


if __name__ == "__main__":
    raise SystemExit(main())
