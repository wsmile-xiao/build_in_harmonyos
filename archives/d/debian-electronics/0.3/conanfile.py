#!/usr/bin/env python3
"""Conan recipe — debian-electronics 0.3 (Debian Pure Blend, metadata/task package).

Debian Electronics is a Debian Pure Blend: one Debian-native source package generates
15 `Architecture: all` binary packages — `electronics-tasks` (the tasksel description
package), `electronics-all` (the umbrella metapackage that Recommends all 13 topic
metapackages), plus 13 `electronics-<topic>` metapackages whose real payload is a
one-line title file under /usr/share/blends/tasks/electronics/ plus dpkg
Depends/Recommends/Suggests lists. There is no compiled library, no executable and
no C/C++ source: all the "software selection" lives in the 13 Deb822 task files under
tasks/.

Conan modelling decision (honest, zero fake linkage):
  - single recipe, data/metadata package (`package_type="unknown"`);
  - package() ships the authentic upstream artifacts: the 13 task files, the
    genblends-produced debian-electronics-tasks.desc, the latest official machine-
    readable dependency snapshot dependency_data/debian-electronics_0.2.json (the
    0.3 release ships no fresh snapshot; see notes.md), and a registry.json derived
    in build() straight from those task files and the debian/control stanzas (no apt,
    no external tooling). No fake executables or libraries.
  - No Debian dependency is translated into Conan `requires`: all entries in the
    snapshots/control are OS/distro package selections (metadata-only), so the Conan
    requires list stays empty. Mechanically copying them would fabricate an
    unsatisfiable dependency graph.
  - Debian semantic recorded verbatim: all 13 task files use the NEW blends 1.1
    format (`Format: https://blends.debian.org/blends/1.1` header present), so the
    file-level `Recommends:`/`Suggests:` feed the metapackage directly (no old-format
    Depends->Recommends lowering as in debian-science). genblends still applies
    apt-availability filtering: some task-file Recommends entries are demoted to
    metapackage Suggests in debian/control (e.g. analog: gwave/qucs). Every topic
    metapackage additionally Depends: electronics-tasks (=0.3); electronics-tasks
    Depends: tasksel. This mapping is embedded in the generated registry.
"""
import json
import os
import re

from conan import ConanFile
from conan.tools.files import (apply_conandata_patches, copy, export_conandata_patches,
                               get)


def _deb822_parse_paragraph(text):
    """Small Deb822 reader tuned to blends task/control files: returns a dict of
    {field: [values]} for repeated single-line fields plus folded text."""
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


def _as_list(v):
    if v is None:
        return []
    return v if isinstance(v, list) else [v]


def _first(v):
    return v[0] if isinstance(v, list) else (v or "")


def _csv_items(v):
    """Split a control-field value (possibly folded over lines) on commas."""
    if v is None:
        return []
    out = []
    for one in _as_list(v):
        for item in str(one).replace("\n", ",").split(","):
            item = item.strip()
            if item and item not in out:
                out.append(item)
    return sorted(out)


def _control_depends(v, version):
    """debian/control Depends: resolve build-time templates — '${source:Version}'
    becomes the blend version; '${misc:Depends}' expands to nothing here (no misc
    dependency is generated for these pure metapackages, verified against the
    published .deb control)."""
    out = []
    for item in _csv_items(v):
        item = item.replace("${source:Version}", version).strip()
        if "${misc:Depends}" in item or not item:
            continue
        if item not in out:
            out.append(item)
    return sorted(out)


class DebianElectronicsConan(ConanFile):
    name = "debian-electronics"
    version = "0.3"
    package_type = "unknown"

    settings = "os", "compiler", "build_type", "arch"  # CI L0 gate; data package, no real semantics
    options = None
    default_options = None

    def requirements(self):
        pass  # 零 Conan requires：全部 Depends/Recommends/Suggests 是 OS 包选择（metadata-only）

    def layout(self):
        self.folders.source = "."

    def export_sources(self):
        export_conandata_patches(self)  # conandata.yml patches 为空时导出为空集（no-op）

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)  # conandata.yml patches: {} => no-op
        # 纯解析：tasks/* (Deb822, 新 blends 1.1 格式) + debian/control 段落 -> registry.json
        # （不调用 apt/genblends；apt 可用性过滤导致的 Recommends->Suggests 降级只记录）
        src = self.source_folder
        task_dir = os.path.join(src, "tasks")
        version = str(self.version)

        # --- debian/control：15 个二进制元包声明 ---
        control_pkgs = []
        control_path = os.path.join(src, "debian", "control")
        if os.path.isfile(control_path):
            with open(control_path, encoding="utf-8", errors="replace") as fh:
                text = fh.read()
            for para in [p for p in re.split(r"\n\s*\n", text) if "Package:" in p]:
                f = _deb822_parse_paragraph(para)
                name = _first(f.get("Package")).strip()
                if not name:
                    continue
                desc = _first(f.get("Description"))
                control_pkgs.append({
                    "package": name,
                    "architecture": _first(f.get("Architecture")).strip(),
                    "section": _first(f.get("Section")).strip() or "misc",
                    "depends": _control_depends(f.get("Depends"), version),
                    "recommends": _csv_items(f.get("Recommends")),
                    "suggests": _csv_items(f.get("Suggests")),
                    "description_synopsis": desc.splitlines()[0].strip() if desc else "",
                })

        # --- tasks/*：13 个 Deb822 任务文件（全部带 Format: 头 = 新 blends 1.1 格式）---
        tasks = []
        for fn in sorted(os.listdir(task_dir)):
            path = os.path.join(task_dir, fn)
            if not os.path.isfile(path):
                continue
            with open(path, encoding="utf-8", errors="replace") as fh:
                para = _deb822_parse_paragraph(fh.read())
            title = _first(para.get("Task")).strip()
            desc = _first(para.get("Description"))
            fmt = _first(para.get("Format")).strip()
            install = _first(para.get("Install")).strip().lower()
            tasks.append({
                "file": fn,
                "task_title": title,
                "description_synopsis": desc.splitlines()[0].strip() if desc else "",
                "install": install if install in ("true", "false") else None,
                "format": fmt,  # 新格式：blends/1.1（Format: 头存在 => 无 Depends->Recommends 降级）
                "file_recommends": _csv_items(para.get("Recommends")),
                "file_suggests": _csv_items(para.get("Suggests")),
            })

        # --- genblends apt 可用性过滤：任务文件 Recommends 中被降级为元包 Suggests 的项 ---
        topic_pkgs = {p["package"]: p for p in control_pkgs}
        demotions = {}
        for t in tasks:
            pk = "electronics-" + t["file"]
            cp = topic_pkgs.get(pk)
            if cp is None:
                continue
            demoted = sorted(set(t["file_recommends"]) - set(cp["recommends"]))
            kept_in_suggests = sorted(d for d in demoted if d in cp["suggests"])
            if demoted:  # 仅记录确有 apt 可用性降级的包
                demotions[pk] = {
                    "demoted_from_task_recommends": demoted,
                    "kept_in_metapackage_suggests": kept_in_suggests,
                }

        # --- tasksel desc：父 debian-electronics + 13 个 electronics-<topic> 子任务 ---
        desc_tasks = []
        desc_keys = []
        desc_path = os.path.join(src, "debian-electronics-tasks.desc")
        if os.path.isfile(desc_path):
            with open(desc_path, encoding="utf-8", errors="replace") as fh:
                text = fh.read()
            for para in [p for p in re.split(r"\n\s*\n", text) if "Task:" in p]:
                f = _deb822_parse_paragraph(para)
                t = _first(f.get("Task")).strip()
                k = _first(f.get("Key")).strip()
                if t:
                    desc_tasks.append(t)
                if k:
                    desc_keys.append(k)

        # --- 官方机器可读依赖快照：0.3 源树仅带 0.1/0.2，最新为 0.2 ---
        dep_dir = os.path.join(src, "dependency_data")
        snapshot_files = []
        snapshot_latest = {}
        if os.path.isdir(dep_dir):
            snapshot_files = sorted(f for f in os.listdir(dep_dir) if f.endswith(".json"))
            latest = "debian-electronics_%s.json" % version
            if not os.path.isfile(os.path.join(dep_dir, latest)):
                latest = snapshot_files[-1] if snapshot_files else ""
            if latest and os.path.isfile(os.path.join(dep_dir, latest)):
                with open(os.path.join(dep_dir, latest), encoding="utf-8") as fh:
                    snapshot_latest = json.load(fh)

        snapshot_refs = set()
        for topic, entry in snapshot_latest.items():
            if not isinstance(entry, dict):
                continue
            for field in ("depends", "recommends", "suggests"):
                for ref in entry.get(field, []) or []:
                    ref = str(ref).strip()
                    if ref and ref != "\\":
                        snapshot_refs.add(ref)

        registry = {
            "version": version,
            "blend": "debian-electronics",
            "semantics": {
                "source": "Debian Pure Blend (debian-electronics) %s" % version,
                "task_format": ("all 13 task files carry 'Format: "
                                "https://blends.debian.org/blends/1.1' (NEW format) "
                                "-> file-level Recommends/Suggests feed the metapackage "
                                "directly; no old-format Depends->Recommends lowering"),
                "metapackage_rule": ("genblends applies apt-availability filtering: some "
                                     "task-file Recommends entries are demoted to metapackage "
                                     "Suggests in debian/control (recorded per package); every "
                                     "topic metapackage additionally Depends: "
                                     "electronics-tasks (=%s); electronics-tasks Depends: "
                                     "tasksel; electronics-all Recommends all 13 topic "
                                     "metapackages" % version),
                "conan_requires": "none (all OS/distro package selections are metadata-only)",
                "snapshot_refs": ("counted from dependency_data/debian-electronics_0.2.json "
                                  "(latest snapshot shipped; the 0.3 release itself ships no "
                                  "fresh snapshot — only 0.1 and 0.2 exist in the source tree)"),
            },
            "counts": {
                "task_files": len(tasks),
                "desc_paragraphs": len(desc_tasks),
                "desc_keys": len(desc_keys),
                "control_packages": len(control_pkgs),
                "arch_all_packages": sum(1 for p in control_pkgs
                                         if p["architecture"] == "all"),
                "snapshot_files": len(snapshot_files),
                "snapshot_refs_latest": len(snapshot_refs),
                "demotions": len(demotions),
            },
            "tasks": tasks,
            "desc_tasks": desc_tasks,
            "desc_keys": desc_keys,
            "control_packages": control_pkgs,
            "demotions": demotions,
            "snapshot": {
                "file": "debian-electronics_%s.json" % version
                if os.path.isfile(os.path.join(dep_dir,
                                               "debian-electronics_%s.json" % version))
                else (snapshot_files[-1] if snapshot_files else ""),
                "topics": sorted(snapshot_latest.keys()),
                "distinct_refs": len(snapshot_refs),
            },
        }

        out = os.path.join(self.build_folder, "stage")
        os.makedirs(out, exist_ok=True)
        with open(os.path.join(out, "registry.json"), "w", encoding="utf-8") as fh:
            json.dump(registry, fh, ensure_ascii=False, indent=1, sort_keys=True)

        self.output.info("=== debian-electronics %s registry built ===" % version)
        self.output.info("  task files        : %d" % len(tasks))
        self.output.info("  desc paragraphs   : %d (keys: %d)" % (len(desc_tasks), len(desc_keys)))
        self.output.info("  control packages  : %d (arch:all: %d)"
                         % (len(control_pkgs), registry["counts"]["arch_all_packages"]))
        self.output.info("  snapshot files    : %d" % len(snapshot_files))
        self.output.info("  distinct OS refs  : %d" % len(snapshot_refs))
        self.output.info("  Recommends demoted: %d" % len(demotions))

    def package(self):
        src = self.source_folder
        stage = os.path.join(self.build_folder, "stage")
        dst = os.path.join(self.package_folder, "share", "debian-electronics")
        copy(self, "*", src=os.path.join(src, "tasks"), dst=os.path.join(dst, "tasks"))
        copy(self, "debian-electronics-tasks.desc", src=src,
             dst=os.path.join(dst, "tasksel"))
        copy(self, "registry.json", src=stage, dst=dst)
        # 0.3 源树无 debian-electronics_0.3.json，打包最新可用快照（0.2）
        snap_file = os.path.join(src, "dependency_data", "debian-electronics_0.2.json")
        if os.path.isfile(snap_file):
            copy(self, "debian-electronics_0.2.json",
                 src=os.path.join(src, "dependency_data"),
                 dst=os.path.join(dst, "dependency_data"))
        cp = os.path.join(src, "debian", "copyright")
        if os.path.exists(cp):
            copy(self, "copyright", src=os.path.dirname(cp),
                 dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = []
        self.cpp_info.resdirs = ["share"]
