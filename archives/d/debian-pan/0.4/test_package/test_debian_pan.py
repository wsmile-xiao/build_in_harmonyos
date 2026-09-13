#!/usr/bin/env python3
"""debian-pan 0.4 — packaged-artifact validation (test_package body).

Validates the authentic upstream metadata shipped by the recipe: the 18 Deb822
task files, the tasksel description file, the official dependency snapshot, the
derived registry.json, and the license. Exit code != 0 on any failure so the
Conan/CI test step fails loudly.

Usage: python3 test_debian_pan.py <package_folder>
"""
import json
import os
import re
import sys

FAILURES = []
CHECKS = 0


def check(cond, label, detail=""):
    global CHECKS
    CHECKS += 1
    if cond:
        print("  [PASS] %s" % label)
    else:
        print("  [FAIL] %s %s" % (label, detail))
        FAILURES.append(label)


def deb822_parse(text):
    """Same reader semantics as the recipe (kept independent for cross-check)."""
    fields = {}
    cur = None
    for raw in text.splitlines():
        if raw.startswith((" ", "\t")):
            stripped = raw.strip()
            if cur is not None and stripped and not stripped.startswith(";"):
                fields[cur][-1] += "\n" + stripped
            continue
        m = re.match(r"^([A-Za-z][A-Za-z0-9-]*):\s*(.*)$", raw)
        if m:
            cur = m.group(1)
            fields.setdefault(cur, []).append(m.group(2).strip())
        else:
            cur = None
    return {k: (v[0] if len(v) == 1 else v) for k, v in fields.items()}


def as_list(v):
    if v is None:
        return []
    return v if isinstance(v, list) else [v]


def first(v):
    return v[0] if isinstance(v, list) else (v or "")


def main(pkg):
    share = os.path.join(pkg, "share", "debian-pan")
    print("debian-pan 0.4 package validation")
    print("  package folder: %s" % pkg)

    # ── ① packaged layout ────────────────────────────────────────────
    task_dir = os.path.join(share, "tasks")
    desc_file = os.path.join(share, "tasksel", "debian-pan-tasks.desc")
    registry_file = os.path.join(share, "registry.json")
    snapshot_file = os.path.join(share, "dependency_data", "debian-pan_0.4.json")
    copyright_file = os.path.join(pkg, "licenses", "copyright")

    check(os.path.isdir(task_dir), "layout: share/debian-pan/tasks/ exists")
    check(os.path.isfile(desc_file), "layout: tasksel/debian-pan-tasks.desc exists")
    check(os.path.isfile(registry_file), "layout: registry.json exists")
    check(os.path.isfile(snapshot_file), "layout: dependency_data/debian-pan_0.4.json exists")
    check(os.path.isfile(copyright_file), "layout: licenses/copyright exists")

    task_files = (sorted(f for f in os.listdir(task_dir)
                         if os.path.isfile(os.path.join(task_dir, f)))
                  if os.path.isdir(task_dir) else [])
    check(len(task_files) == 18, "tasks: exactly 18 task files packaged", "(got %d)" % len(task_files))

    # ── ② 鸿蒙特有测试：OHOS 平台适配预检（5 项）────────────────────
    # 本包为数据/元数据包：OHOS 侧交付面必须无二进制产物（未签名 ELF 在 OHOS
    # 被拒 execve）、无 CLI 伪装（L0k/R38）、无编译器产物目录（R26 不适用）。
    print("  ── 鸿蒙特有测试（OHOS 平台适配预检）──")
    check(not os.path.isdir(os.path.join(pkg, "bin")),
          "OHOS: no bin/ directory packaged (L0k/R38 不伪装 CLI 工具)")
    check(not os.path.isdir(os.path.join(pkg, "lib")),
          "OHOS: no lib/ directory packaged (R26 系统同名库隔离不适用)")
    elf = []
    for root, _dirs, files in os.walk(pkg):
        for fn in files:
            fp = os.path.join(root, fn)
            try:
                with open(fp, "rb") as fh:
                    if fh.read(4) == b"\x7fELF":
                        elf.append(fp)
            except OSError:
                pass
    check(not elf,
          "OHOS: no ELF artifacts (未签名 ELF 在 OHOS 不可执行；零二进制交付)", str(elf))
    lib_artifacts = []
    for root, _dirs, files in os.walk(pkg):
        for fn in files:
            if fn.endswith((".so", ".a", ".o")) or ".so." in fn:
                lib_artifacts.append(os.path.join(root, fn))
    check(not lib_artifacts, "OHOS: no .so/.a/.o library artifacts", str(lib_artifacts[:5]))
    top = sorted(d for d in os.listdir(pkg) if os.path.isdir(os.path.join(pkg, d)))
    check(top == ["licenses", "share"],
          "OHOS: delivery surface is share/ + licenses/ only (数据包部署形态)", str(top))

    # ── ② tasks/ Deb822 structure (blends 1.1 new format) ────────────
    bad_format, bad_task, bad_desc = [], [], []
    formats = set()
    parsed_tasks = {}
    for fn in task_files:
        with open(os.path.join(task_dir, fn), encoding="utf-8", errors="replace") as fh:
            para = deb822_parse(fh.read())
        parsed_tasks[fn] = para
        fmt = first(para.get("Format")).strip()
        formats.add(fmt)
        if not fmt.startswith("https://blends.debian.org/blends/"):
            bad_format.append(fn)
        if first(para.get("Task")).strip() != fn:
            bad_task.append(fn)
        if not first(para.get("Description")).strip():
            bad_desc.append(fn)

    check(not bad_format, "tasks: all 18 carry blends Format header", str(bad_format))
    check(formats == {"https://blends.debian.org/blends/1.1"},
          "tasks: blends format is 1.1 (new format)", str(sorted(formats)))
    check(not bad_task, "tasks: Task field == filename for all 18", str(bad_task))
    check(not bad_desc, "tasks: non-empty Description for all 18", str(bad_desc))

    # ── ③ tasksel desc structure ─────────────────────────────────────
    desc_text = ""
    if os.path.isfile(desc_file):
        with open(desc_file, encoding="utf-8", errors="replace") as fh:
            desc_text = fh.read()
    desc_paras = [p for p in re.split(r"\n\s*\n", desc_text) if "Task:" in p]
    desc_tasks, desc_keys = [], []
    for p in desc_paras:
        f = deb822_parse(p)
        t = first(f.get("Task")).strip()
        k = first(f.get("Key")).strip()
        if t:
            desc_tasks.append(t)
        if k:
            desc_keys.append(k)
    check(len(desc_tasks) == 17, "tasksel desc: 17 task paragraphs", "(got %d)" % len(desc_tasks))
    check("debian-pan" in desc_tasks,
          "tasksel desc: parent task 'debian-pan' present")
    check(len(desc_keys) == 16, "tasksel desc: 16 Key entries", "(got %d)" % len(desc_keys))
    check(all(k.startswith("pan-") for k in desc_keys),
          "tasksel desc: all Keys are pan-* metapackages")
    # 每个 Key 必须能在 desc 段落里找到同名 Task（1:1 时 Key == Task；
    # 若 Key 无前缀则须有 "pan-"+Key 的 Task）—— 去掉恒真的 or 兜底
    unmapped = sorted(k for k in desc_keys
                      if k not in desc_tasks and ("pan-" + k) not in desc_tasks)
    check(not unmapped,
          "tasksel desc: every Key maps to a task entry", str(unmapped))

    # ── ④ registry.json cross-check against packaged files ───────────
    reg = {}
    if os.path.isfile(registry_file):
        with open(registry_file, encoding="utf-8") as fh:
            reg = json.load(fh)
    check(reg.get("blend") == "debian-pan", "registry: blend == debian-pan")
    check(reg.get("version") == "0.4", "registry: version == 0.4")
    counts = reg.get("counts", {})
    check(counts.get("task_files") == len(task_files),
          "registry: counts.task_files matches packaged tasks",
          "(%s vs %d)" % (counts.get("task_files"), len(task_files)))
    check(counts.get("desc_paragraphs") == len(desc_tasks),
          "registry: counts.desc_paragraphs matches packaged desc",
          "(%s vs %d)" % (counts.get("desc_paragraphs"), len(desc_tasks)))
    check(counts.get("desc_keys") == len(desc_keys),
          "registry: counts.desc_keys matches packaged desc keys")
    check(counts.get("control_packages") == 18,
          "registry: counts.control_packages == 18", "(got %s)" % counts.get("control_packages"))
    check(counts.get("arch_all_packages") == 18,
          "registry: all 18 control packages are Architecture: all")
    check(counts.get("metapackages") == 16,
          "registry: 16 pan-* metapackages", "(got %s)" % counts.get("metapackages"))
    check(counts.get("snapshot_files") == 4,
          "registry: 4 dependency_data snapshot files", "(got %s)" % counts.get("snapshot_files"))

    # re-derive per-task title/recommends from the packaged files and compare
    reg_tasks = {t["file"]: t for t in reg.get("tasks", [])}
    check(set(reg_tasks) == set(task_files),
          "registry: tasks[] keyed by the same 18 files")
    mismatched = []
    for fn, para in parsed_tasks.items():
        rt = reg_tasks.get(fn, {})
        if rt.get("task_title") != first(para.get("Task")).strip():
            mismatched.append(fn)
    check(not mismatched, "registry: task titles re-derive identically", str(mismatched))

    # format recorded per task
    check(all(t.get("format", "").startswith("https://blends.debian.org/blends/1.1")
              for t in reg.get("tasks", [])),
          "registry: every task records the blends 1.1 format")

    # ── ⑤ debian/control declared packages ───────────────────────────
    ctrl = reg.get("control_packages", [])
    check(len(ctrl) == 18, "control: 18 declared binary packages", "(got %d)" % len(ctrl))
    check(all(p.get("architecture") == "all" for p in ctrl),
          "control: every declared package is Architecture: all")
    check(all(p.get("description_synopsis") for p in ctrl),
          "control: every declared package has a description")
    ctrl_names = {p["package"] for p in ctrl}
    check("pan-tasks" in ctrl_names and "pan-config" in ctrl_names,
          "control: pan-tasks and pan-config present")
    metas = {p["package"] for p in ctrl
             if p["package"].startswith("pan-")
             and p["package"] not in ("pan-tasks", "pan-config")}
    check(len(metas) == 16, "control: 16 pan-* metapackages", "(got %d)" % len(metas))
    # tasks ⊇ metapackages (laue / mx-dev are task-only; recorded, not normalised)
    task_stems = set(task_files)
    missing = sorted(m[4:] for m in metas if m[4:] not in task_stems)
    check(not missing, "control: every metapackage stem has a task file", str(missing))
    check("laue" in task_stems and "pan-laue" not in ctrl_names,
          "control: mapping asymmetry recorded (laue task-only)")
    check("mx-dev" in task_stems and "pan-mx-dev" not in ctrl_names,
          "control: mapping asymmetry recorded (mx-dev task-only)")

    # ── ⑥ official dependency snapshot ───────────────────────────────
    snap = {}
    if os.path.isfile(snapshot_file):
        with open(snapshot_file, encoding="utf-8") as fh:
            snap = json.load(fh)
    check(set(snap.keys()) == set(task_files),
          "snapshot: topic set == tasks/ file set (18/18)",
          "(only-snap=%s only-tasks=%s)"
          % (sorted(set(snap) - set(task_files)), sorted(set(task_files) - set(snap))))
    field_bad = []
    for topic, entry in snap.items():
        for key in ("depends", "suggests", "recommends", "ignore", "avoid"):
            if key not in entry or not isinstance(entry[key], list):
                field_bad.append("%s:%s" % (topic, key))
    check(not field_bad, "snapshot: all 5 fields are arrays for all 18 topics", str(field_bad[:5]))

    refs = set()
    for topic, entry in snap.items():
        for field in ("depends", "recommends", "suggests"):
            for ref in entry.get(field, []) or []:
                ref = str(ref).strip()
                if ref and ref != "\\":
                    refs.add(ref)
    check(len(refs) == 446, "snapshot: 446 distinct OS package refs", "(got %d)" % len(refs))
    check(reg.get("snapshot", {}).get("distinct_refs") == len(refs),
          "registry: snapshot.distinct_refs matches re-derived count")
    check(sorted(snap.keys()) == reg.get("snapshot", {}).get("topics"),
          "registry: snapshot.topics matches snapshot file keys")

    # ── ⑦ semantics recorded (blends 1.1 + zero conan requires) ──────
    sem = reg.get("semantics", {})
    check(sem.get("conan_requires", "").startswith("none"),
          "semantics: conan_requires == none (no fabricated dep graph)")
    check("blends 1.1" in sem.get("blends_format", ""),
          "semantics: blends 1.1 new format recorded")
    check("superset" in sem.get("mapping_asymmetry", ""),
          "semantics: task/metapackage mapping asymmetry recorded")

    # ── summary ──────────────────────────────────────────────────────
    print("")
    print("  checks: %d, failures: %d" % (CHECKS, len(FAILURES)))
    if FAILURES:
        print("  ==> FAILED (%.1f%%)" % (100.0 * (CHECKS - len(FAILURES)) / CHECKS))
        for f in FAILURES:
            print("      - %s" % f)
        return 1
    print("  ==> ALL PASSED (100.0%)")
    return 0


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("usage: python3 test_debian_pan.py <package_folder>")
        sys.exit(2)
    sys.exit(main(sys.argv[1]))
