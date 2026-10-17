#!/usr/bin/env python3
"""Verify packaged debian-electronics metadata (upstream has no test suite).

The upstream Debian Pure Blend ships zero tests (no tests/ dir, no ctest/pytest
registration), so this consumer-side script validates the packaged data assets
against the facts re-derived from those very files:

  1.  layout        — tasks/, tasksel desc, registry.json, dependency snapshot, license
  2.  tasks/        — 13 Deb822 task files (NEW blends 1.1 format: 'Format:' header),
                      each with Task/Description/Install
  3.  tasksel desc  — 14 paragraphs, parent 'debian-electronics', 13 'electronics-*' keys
  4.  registry      — counts and per-file fields cross-checked against packaged files
  5.  debian/control — 15 declared packages, all Architecture: all, all electronics-*
  6.  snapshot      — dependency_data 0.2 topic set == tasks/ file set
  7.  semantics     — new-format blends mapping recorded (no Depends->Recommends
                      lowering), genblends apt demotions recorded, conan_requires == none
  8.  naming        — every referenced OS package matches Debian naming rules

Usage: python3 test_debian_electronics.py <package_folder>
"""
import json
import os
import re
import sys

EXPECTED_TASKS = 13
EXPECTED_DESC_TASKS = 14
EXPECTED_DESC_KEYS = 13
EXPECTED_CONTROL_PACKAGES = 15
EXPECTED_INSTALL_TRUE = 13
EXPECTED_INSTALL_FALSE = 0
EXPECTED_SNAPSHOT_TOPICS = 13
EXPECTED_SNAPSHOT_REFS = 109
EXPECTED_SNAPSHOT_FILES = 2
EXPECTED_DEMOTIONS = 9
EXPECTED_TOPIC_METAPACKAGES = 13

_failures = 0


def check(cond, label, detail=""):
    global _failures
    if cond:
        print("[PASS] %s" % label)
    else:
        _failures += 1
        print("[FAIL] %s %s" % (label, ("-- " + detail) if detail else ""))


def fields(text):
    """Deb822 reader: {field: [values]}, folding indented continuation lines."""
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


def nonempty(values):
    return [v.strip() for v in (values or []) if v.strip()]


def first(values):
    return nonempty(values)[0] if nonempty(values) else ""


def csv_items(values):
    """Split a control-field value (possibly folded) on commas; keep order unique."""
    out = []
    for one in (values or []):
        for item in str(one).replace("\n", ",").split(","):
            item = item.strip()
            if item and item not in out:
                out.append(item)
    return sorted(out)


def main():
    if len(sys.argv) < 2:
        print("Usage: python3 test_debian_electronics.py <package_folder>")
        return 1

    root = sys.argv[1]
    base = os.path.join(root, "share", "debian-electronics")
    task_dir = os.path.join(base, "tasks")
    desc_path = os.path.join(base, "tasksel", "debian-electronics-tasks.desc")
    reg_path = os.path.join(base, "registry.json")
    snap_dir = os.path.join(base, "dependency_data")
    snap_path = os.path.join(snap_dir, "debian-electronics_0.2.json")
    license_path = os.path.join(root, "licenses", "copyright")

    print("=" * 66)
    print("test_debian_electronics.py — debian-electronics 0.3 packaged metadata")
    print("=" * 66)

    # ── 1. layout ──────────────────────────────────────────────────────────
    print("\n--- [1] packaged layout ---")
    check(os.path.exists(task_dir), "exists: tasks/ dir", task_dir)
    check(os.path.exists(desc_path), "exists: tasksel desc", desc_path)
    check(os.path.exists(reg_path), "exists: registry.json", reg_path)
    check(os.path.exists(snap_path), "exists: dependency snapshot", snap_path)
    check(os.path.exists(license_path), "exists: licenses/copyright", license_path)

    if _failures:
        print("\nABORT: packaged layout incomplete")
        return 1

    # ── 2. tasks/ ──────────────────────────────────────────────────────────
    print("\n--- [2] tasks/ Deb822 task files ---")
    task_files = sorted(f for f in os.listdir(task_dir)
                        if os.path.isfile(os.path.join(task_dir, f)))
    check(len(task_files) == EXPECTED_TASKS,
          "task file count == %d" % EXPECTED_TASKS, "got %d" % len(task_files))

    parsed = {}
    for fn in task_files:
        with open(os.path.join(task_dir, fn), encoding="utf-8", errors="replace") as fh:
            parsed[fn] = fields(fh.read())

    missing_title = [f for f, d in parsed.items() if not first(d.get("Task"))]
    missing_desc = [f for f, d in parsed.items() if not first(d.get("Description"))]
    check(not missing_title, "every task file has non-empty 'Task:'", str(missing_title))
    check(not missing_desc, "every task file has non-empty 'Description:'", str(missing_desc))

    # NEW blends 1.1 format: every task file carries a 'Format:' header
    no_format = [f for f, d in parsed.items()
                 if not str(first(d.get("Format"))).startswith("https://blends.debian.org/blends/1")]
    check(not no_format, "every task file has new-format 'Format:' header (blends/1.1)",
          str(no_format))

    # no file-level Depends field in the new format (nothing to lower to Recommends)
    has_depends = [f for f, d in parsed.items() if nonempty(d.get("Depends"))]
    check(not has_depends, "no task file carries a file-level 'Depends:' field",
          str(has_depends))

    installs = [first(d.get("Install")).lower() for d in parsed.values()]
    bad_install = [v for v in installs if v not in ("true", "false")]
    check(not bad_install, "every 'Install:' is true|false", str(bad_install))
    check(installs.count("true") == EXPECTED_INSTALL_TRUE
          and installs.count("false") == EXPECTED_INSTALL_FALSE,
          "Install split == %d true / %d false" % (EXPECTED_INSTALL_TRUE, EXPECTED_INSTALL_FALSE),
          "got %d/%d" % (installs.count("true"), installs.count("false")))

    # ── 3. tasksel desc ────────────────────────────────────────────────────
    print("\n--- [3] tasksel description ---")
    with open(desc_path, encoding="utf-8", errors="replace") as fh:
        desc_text = fh.read()
    desc_paras = [p for p in re.split(r"\n\s*\n", desc_text) if "Task:" in p]
    desc_tasks = [first(fields(p).get("Task")) for p in desc_paras]
    desc_keys = [first(fields(p).get("Key")) for p in desc_paras]
    desc_keys = [k for k in desc_keys if k]

    check(len(desc_paras) == EXPECTED_DESC_TASKS,
          "desc paragraph count == %d" % EXPECTED_DESC_TASKS, "got %d" % len(desc_paras))
    check("debian-electronics" in desc_tasks, "desc contains parent task 'debian-electronics'")
    check(len(desc_keys) == EXPECTED_DESC_KEYS,
          "desc 'Key:' count == %d" % EXPECTED_DESC_KEYS, "got %d" % len(desc_keys))
    check(all(k.startswith("electronics-") for k in desc_keys),
          "all desc keys use the 'electronics-' prefix",
          str([k for k in desc_keys if not k.startswith("electronics-")]))

    key_topics = {k[len("electronics-"):] for k in desc_keys}
    unknown_keys = sorted(key_topics - set(task_files))
    check(not unknown_keys,
          "every desc key maps to a packaged task file", str(unknown_keys))

    parents = [first(fields(p).get("Parent")) for p in desc_paras]
    bad_parent = [t for t, par in zip(desc_tasks, parents)
                  if t != "debian-electronics" and par != "debian-electronics"]
    check(not bad_parent, "every child task has Parent: debian-electronics", str(bad_parent))

    # ── 4. registry cross-check ────────────────────────────────────────────
    print("\n--- [4] registry.json vs packaged files (re-derived) ---")
    with open(reg_path, encoding="utf-8") as fh:
        reg = json.load(fh)

    counted = reg.get("counts", {})

    reg_tasks = {t["file"]: t for t in reg.get("tasks", [])}

    mismatched = []
    for fn in task_files:
        d = parsed[fn]
        entry = reg_tasks.get(fn, {})
        if (entry.get("task_title") != first(d.get("Task"))
                or entry.get("file_recommends") != csv_items(d.get("Recommends"))
                or entry.get("file_suggests") != csv_items(d.get("Suggests"))
                or entry.get("install") != first(d.get("Install")).strip().lower()):
            mismatched.append(fn)
    check(not mismatched,
          "registry per-task title/recommends/suggests/install cross-check",
          str(mismatched[:5]))


    # ── 5. debian/control declared packages ────────────────────────────────
    print("\n--- [5] debian/control metapackage declarations ---")
    control_pkgs = reg.get("control_packages", [])
    check(len(control_pkgs) == EXPECTED_CONTROL_PACKAGES,
          "control declares %d packages" % EXPECTED_CONTROL_PACKAGES,
          "got %d" % len(control_pkgs))
    not_all = [p["package"] for p in control_pkgs if p.get("architecture") != "all"]
    check(not not_all, "every declared package is Architecture: all", str(not_all))
    bad_prefix = [p["package"] for p in control_pkgs
                  if not p["package"].startswith("electronics-")]
    check(not bad_prefix, "every declared package uses the 'electronics-' prefix",
          str(bad_prefix))
    no_synopsis = [p["package"] for p in control_pkgs if not p.get("description_synopsis")]
    check(not no_synopsis, "every declared package has a Description synopsis",
          str(no_synopsis))

    ctl_by_name = {p["package"]: p for p in control_pkgs}
    # every topic metapackage Depends: electronics-tasks (= version)
    topic_pkgs = sorted((p for p in control_pkgs
                          if p["package"].startswith("electronics-")
                          and p["package"] not in ("electronics-tasks", "electronics-all")),
                         key=lambda p: p["package"])
    check(len(topic_pkgs) == EXPECTED_TOPIC_METAPACKAGES,
          "there are %d topic metapackages" % EXPECTED_TOPIC_METAPACKAGES,
          "got %d" % len(topic_pkgs))
    missing_tasks_dep = [
        p["package"] for p in topic_pkgs
        if not any("electronics-tasks" in d and "0.3" in d for d in p.get("depends", []))]
    check(not missing_tasks_dep,
          "every topic metapackage Depends: electronics-tasks (=0.3)",
          str(missing_tasks_dep))

    tasks_pkg = ctl_by_name.get("electronics-tasks", {})
    check(any("tasksel" in d for d in tasks_pkg.get("depends", [])),
          "electronics-tasks Depends: tasksel")

    all_pkg = ctl_by_name.get("electronics-all", {})
    all_recs = set(all_pkg.get("recommends", []))
    expected_all_recs = {p["package"] for p in topic_pkgs}
    check(all_recs == expected_all_recs,
          "electronics-all Recommends == all %d topic metapackages"
          % EXPECTED_TOPIC_METAPACKAGES,
          "missing=%s extra=%s" % (sorted(expected_all_recs - all_recs)[:3],
                                   sorted(all_recs - expected_all_recs)[:3]))

    # ── 6. official dependency snapshot ────────────────────────────────────
    print("\n--- [6] official dependency snapshot (0.2) ---")
    with open(snap_path, encoding="utf-8") as fh:
        snap = json.load(fh)
    check(set(snap.keys()) == set(task_files),
          "snapshot topic set == tasks/ file set (%d keys)" % len(snap),
          "sym-diff %s" % str(sorted(set(snap) ^ set(task_files))[:5]))

    refs = set()
    for topic, entry in snap.items():
        if not isinstance(entry, dict):
            continue
        for field in ("depends", "recommends", "suggests"):
            for ref in entry.get(field, []) or []:
                ref = str(ref).strip()
                if ref and ref != "\\":
                    refs.add(ref)
    check(len(refs) == EXPECTED_SNAPSHOT_REFS,
          "snapshot distinct OS refs == %d" % EXPECTED_SNAPSHOT_REFS,
          "got %d" % len(refs))
    check(reg.get("snapshot", {}).get("distinct_refs") == len(refs),
          "registry recorded snapshot ref count == re-derived count",
          "%r vs %d" % (reg.get("snapshot", {}).get("distinct_refs"), len(refs)))
    check(reg.get("snapshot", {}).get("file") == "debian-electronics_0.2.json",
          "registry snapshot.file == the packaged 0.2 snapshot",
          str(reg.get("snapshot", {}).get("file")))

    name_re = re.compile(r"^[a-z0-9][a-z0-9+.-]*$")

    def _members(ref):
        return [p.strip() for p in re.split(r"[|,]", ref) if p.strip()]

    alternative_groups = sorted(r for r in refs if len(_members(r)) > 1)
    bad_names = []
    for ref in refs:
        bad_names.extend(p for p in _members(ref) if not name_re.match(p))
    check(not bad_names, "every snapshot reference member matches Debian naming rules",
          str(bad_names[:5]))
    print("[INFO] alternative dependency groups in snapshot: %d %s"
          % (len(alternative_groups), alternative_groups[:3]))

    # ── 7. semantics ───────────────────────────────────────────────────────
    print("\n--- [7] Debian semantic mapping ---")
    sem = reg.get("semantics", {})
    check(bool(sem), "registry carries 'semantics' block")
    check("none" in str(sem.get("conan_requires", "")),
          "semantics records conan_requires == none",
          str(sem.get("conan_requires")))
    check("blends/1.1" in str(sem.get("task_format", "")),
          "semantics records the new blends/1.1 format (no Depends lowering)")
    check("depends" in str(reg.get("semantics", {}).get("metapackage_rule", "")).lower()
          or "Recommends" in str(reg.get("semantics", {}).get("metapackage_rule", "")),
          "semantics records the metapackage rule")
    dem = reg.get("demotions", {})
    check(len(dem) == EXPECTED_DEMOTIONS,
          "registry records %d packages with apt-availability demotions"
          % EXPECTED_DEMOTIONS, "got %d" % len(dem))
    # spot-check the analog demotion (gwave/qucs task-Recommends -> metapackage Suggests)
    analog_dem = dem.get("electronics-analog", {})
    demoted = analog_dem.get("demoted_from_task_recommends", [])
    check({"gwave", "qucs"} <= set(demoted),
          "analog task-Recommends gwave/qucs demoted by apt filtering",
          str(demoted))
    check(all(d in analog_dem.get("kept_in_metapackage_suggests", [])
              for d in demoted),
          "every demoted analog entry kept in metapackage Suggests",
          str(analog_dem.get("kept_in_metapackage_suggests")))
    check(str(reg.get("version")) == "0.3", "registry version == 0.3",
          str(reg.get("version")))

    print("\n" + "=" * 66)
    if _failures == 0:
        print("OK: debian-electronics metadata verified "
              "(tasks=%d, desc=%d/%d keys, control=%d all arch:all, "
              "snapshot topics=%d, distinct OS refs=%d, demotions=%d)"
              % (len(task_files), len(desc_paras), len(desc_keys),
                 len(control_pkgs), len(snap), len(refs), len(dem)))
        print("ALL checks PASSED")
    else:
        print("%d check(s) FAILED" % _failures)
    print("=" * 66)
    return 1 if _failures else 0


if __name__ == "__main__":
    sys.exit(main())
