#!/usr/bin/env python3
"""Verify packaged debichem metadata (no upstream test suite exists)."""
import json
import os
import re
import sys


def _fields(text):
    """Return {field: [values]} for Deb822, folding indented continuation lines
    into the preceding field value (Key:/Description: are folded)."""
    out = {}
    cur = None
    for raw in text.splitlines():
        if raw[:1] in (" ", "\t"):
            if cur is not None and out.get(cur):
                out[cur][-1] += "\n" + raw.strip()
            continue
        m = re.match(r"^([A-Za-z][A-Za-z0-9-]*):\s*(.*)$", raw)
        if m:
            cur = m.group(1)
            out.setdefault(cur, []).append(m.group(2).strip())
    return out


def _nonempty(values):
    return [v.strip() for v in (values or []) if v.strip()]


def main():
    root = sys.argv[1]
    base = os.path.join(root, "share", "debichem")
    task_dir = os.path.join(base, "tasks")
    desc = os.path.join(base, "tasksel", "debichem-tasks.desc")
    reg = os.path.join(base, "registry.json")

    for p in (task_dir, desc, reg, os.path.join(root, "licenses", "copyright")):
        if not os.path.exists(p):
            print(f"FAIL: missing {p}")
            return 1

    tasks = sorted(os.listdir(task_dir))
    if len(tasks) != 12:
        print(f"FAIL: tasks count {len(tasks)} != 12")
        return 1

    # tasksel desc structure: parent debichem + 12 children, Key == debichem-<task>
    dt = _fields(open(desc, encoding="utf-8", errors="replace").read())
    if "debichem" not in dt.get("Task", []):
        print("FAIL: desc missing parent Task 'debichem'")
        return 1
    keys = sorted(_nonempty(dt.get("Key", [])))
    expect_keys = sorted(f"debichem-{t}" for t in tasks)
    if keys != expect_keys:
        print(f"FAIL: desc Key set {keys} != tasks {expect_keys}")
        return 1
    if len(_nonempty(dt.get("Task", []))) != 13:
        print(f"FAIL: desc Task count {len(_nonempty(dt.get('Task', [])))} != 13 (1+12)")
        return 1

    # registry cross-check: re-derive from packaged task files and compare
    reg_data = json.load(open(reg, encoding="utf-8"))
    rtasks = {t["file"]: t for t in reg_data.get("tasks", [])}
    if set(rtasks) != set(tasks):
        print("FAIL: registry task files != packaged tasks dir")
        return 1
    seen_dep = set()
    for t in tasks:
        text = open(os.path.join(task_dir, t), encoding="utf-8", errors="replace").read()
        f = _fields(text)
        title = (f.get("Task") or [""])[0]
        entry = rtasks[t]
        if entry.get("title") != title:
            print(f"FAIL: registry title for {t}: {entry.get('title')!r} != {title!r}")
            return 1
        depends = sorted(f.get("Depends") or [])
        suggests = sorted(f.get("Suggests") or [])
        if entry.get("file_depends") != depends or entry.get("file_suggests") != suggests:
            print(f"FAIL: registry depends/suggests mismatch for {t}")
            return 1
        seen_dep.update(depends)
        seen_dep.update(suggests)
        for dep in depends + suggests:
            if not re.match(r"^[a-z0-9][a-z0-9+.-]*$", dep):
                print(f"FAIL: bad package name {dep!r} in {t}")
                return 1

    # record Debian mapping metadata present
    if "semantics" not in reg_data:
        print("FAIL: registry missing 'semantics' (Debian metapackage mapping)")
        return 1

    print(f"OK: debichem metadata verified (tasks={len(tasks)}, desc tasks=13, "
          f"registry cross-check ok, distinct OS-package refs={len(seen_dep)})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
