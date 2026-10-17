#!/usr/bin/env python3
"""Conan recipe — debian-science 1.15 (Debian Pure Blend, metadata/task package).

Debian Science is a Debian Pure Blend: one Debian-native source package generates
45 `Architecture: all` binary packages — `science-tasks` (the tasksel description
package), `science-config`/`science-all`/`science-electronics` (config and
umbrella packages), plus 41 `science-<topic>` metapackages whose real payload is
metadata (a one-line title file under /usr/share/blends/tasks/debian-science/ and
dpkg Depends/Recommends/Suggests lists). There is no compiled library, no
executable and no C/C++ source: all the "software selection" lives in the 46
Deb822 task files under tasks/.

Conan modelling decision (honest, zero fake linkage):
  - single recipe, data/metadata package (`package_type="unknown"`);
  - package() ships the authentic upstream artifacts: the 46 task files, the
    genblends-produced debian-science-tasks.desc, the official machine-readable
    dependency snapshot dependency_data/debian-science_1.15.json, and a
    registry.json derived in build() straight from those task files and the
    debian/control stanzas (no apt, no external tooling). No fake executables or
    libraries.
  - No Debian dependency is translated into Conan `requires`: the ~1976 distinct
    entries in the 1.15 snapshot are OS/distro package selections (metadata-only),
    so the Conan requires list stays empty. Mechanically copying them would
    fabricate an unsatisfiable dependency graph.
  - Debian semantic recorded verbatim: the task files use the old blends format
    (no `Format:` header), so genblends lowers a task file's file-level
    `Depends:` to metapackage `Recommends:` and keeps `Suggests:` as `Suggests:`;
    every metapackage additionally `Depends: debian-science-tasks (=version)`.
    This mapping is embedded in the generated registry so consumers can
    reconstruct the Debian meaning.
"""
import json
import os
import re

from conan import ConanFile
from conan.tools.files import copy, get


def _deb822_parse_paragraph(text):
    """Small Deb822 reader tuned to blends task/control files: returns a dict of
    {field: [values]} for repeated single-line fields plus folded text."""
    fields = {}
    cur = None
    for raw in text.splitlines():
        if raw.startswith((" ", "\t")):
            # blends-inject annotations (leading ';') are machine-added comments,
            # not Deb822 values — genblends does not carry them into the .deb.
            # Blank continuation lines (a lone space) fold to nothing.
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


class DebianScienceConan(ConanFile):
    name = "debian-science"
    version = "1.15"
    package_type = "unknown"

    settings = "os", "compiler", "build_type", "arch"  # CI L0 gate; data package, no real semantics
    options = None
    default_options = None

    def requirements(self):
        pass  # 零 Conan requires：全部 Depends/Recommends/Suggests 是 OS 包选择（metadata-only）

    def layout(self):
        self.folders.source = "."

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        # 纯解析：tasks/* (Deb822) + debian/control 段落 -> registry.json
        # （不调用 apt/genblends；旧格式 Depends->Recommends 降级语义只记录，不改写文件）
        src = self.source_folder
        task_dir = os.path.join(src, "tasks")
        version = str(self.version)

        # --- debian/control：45 个二进制元包声明 ---
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
                control_pkgs.append({
                    "package": name,
                    "architecture": _first(f.get("Architecture")).strip(),
                    "section": _first(f.get("Section")).strip(),
                    "depends": sorted(_as_list(f.get("Depends"))),
                    "recommends": sorted(_as_list(f.get("Recommends"))),
                    "suggests": sorted(_as_list(f.get("Suggests"))),
                    "description_synopsis": _first(f.get("Description")).splitlines()[0].strip()
                                             if _first(f.get("Description")) else "",
                })

        # --- tasks/*：46 个 Deb822 任务文件 ---
        tasks = []
        for fn in sorted(os.listdir(task_dir)):
            path = os.path.join(task_dir, fn)
            if not os.path.isfile(path):
                continue
            with open(path, encoding="utf-8", errors="replace") as fh:
                para = _deb822_parse_paragraph(fh.read())
            title = _first(para.get("Task")).strip()
            desc = _first(para.get("Description"))
            depends = sorted(v for v in _as_list(para.get("Depends")) if v)
            suggests = sorted(v for v in _as_list(para.get("Suggests")) if v)
            recommends = sorted(v for v in _as_list(para.get("Recommends")) if v)
            install = _first(para.get("Install")).strip().lower()
            metapackage = _first(para.get("Metapackage")).strip().lower()
            tasks.append({
                "file": fn,
                "task_title": title,
                "description_synopsis": desc.splitlines()[0].strip() if desc else "",
                "install": install if install in ("true", "false") else None,
                "metapackage": metapackage if metapackage in ("true", "false") else None,
                "file_depends": depends,
                "file_recommends": recommends,
                "file_suggests": suggests,
                # 旧格式降级规则：文件级 Depends -> 元包 Recommends
                "debian_metapackage_recommends": depends,
                "debian_metapackage_suggests": suggests,
            })

        # --- tasksel desc：父 debian-science + 41 个 science-<topic> 子任务 ---
        desc_tasks = []
        desc_keys = []
        desc_path = os.path.join(src, "debian-science-tasks.desc")
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

        # --- 官方机器可读依赖快照（0.1 -> 1.15 系列，仅登记 1.15 + 序列）---
        dep_dir = os.path.join(src, "dependency_data")
        snapshot_files = []
        snapshot_115 = {}
        if os.path.isdir(dep_dir):
            snapshot_files = sorted(f for f in os.listdir(dep_dir) if f.endswith(".json"))
            cur = os.path.join(dep_dir, "debian-science_%s.json" % version)
            if os.path.isfile(cur):
                with open(cur, encoding="utf-8") as fh:
                    snapshot_115 = json.load(fh)

        snapshot_refs = set()
        for topic, entry in snapshot_115.items():
            if not isinstance(entry, dict):
                continue
            for field in ("depends", "recommends", "suggests"):
                for ref in entry.get(field, []) or []:
                    ref = str(ref).strip()
                    if ref and ref != "\\":
                        snapshot_refs.add(ref)

        registry = {
            "version": version,
            "blend": "debian-science",
            "semantics": {
                "source": "Debian Pure Blend (debian-science) %s" % version,
                "metapackage_rule": ("old-format task files (no 'Format:' header) -> "
                                     "genblends lowers file-level Depends to metapackage "
                                     "Recommends; Suggests stays Suggests; each metapackage "
                                     "also Depends: debian-science-tasks (=%s)" % version),
                "conan_requires": "none (all OS/distro package selections are metadata-only)",
                "snapshot_refs": "counted from dependency_data/debian-science_%s.json" % version,
            },
            "counts": {
                "task_files": len(tasks),
                "desc_paragraphs": len(desc_tasks),
                "desc_keys": len(desc_keys),
                "control_packages": len(control_pkgs),
                "arch_all_packages": sum(1 for p in control_pkgs if p["architecture"] == "all"),
                "snapshot_files": len(snapshot_files),
                "snapshot_refs_1_15": len(snapshot_refs),
            },
            "tasks": tasks,
            "desc_tasks": desc_tasks,
            "desc_keys": desc_keys,
            "control_packages": control_pkgs,
            "snapshot": {
                "file": "debian-science_%s.json" % version,
                "topics": sorted(snapshot_115.keys()),
                "distinct_refs": len(snapshot_refs),
            },
        }

        out = os.path.join(self.build_folder, "stage")
        os.makedirs(out, exist_ok=True)
        with open(os.path.join(out, "registry.json"), "w", encoding="utf-8") as fh:
            json.dump(registry, fh, ensure_ascii=False, indent=1, sort_keys=True)

        self.output.info("=== debian-science %s registry built ===" % version)
        self.output.info("  task files        : %d" % len(tasks))
        self.output.info("  desc paragraphs   : %d (keys: %d)" % (len(desc_tasks), len(desc_keys)))
        self.output.info("  control packages  : %d (arch:all: %d)"
                         % (len(control_pkgs), registry["counts"]["arch_all_packages"]))
        self.output.info("  snapshot files    : %d" % len(snapshot_files))
        self.output.info("  distinct OS refs  : %d" % len(snapshot_refs))

    def package(self):
        src = self.source_folder
        stage = os.path.join(self.build_folder, "stage")
        dst = os.path.join(self.package_folder, "share", "debian-science")
        copy(self, "*", src=os.path.join(src, "tasks"), dst=os.path.join(dst, "tasks"))
        copy(self, "debian-science-tasks.desc", src=src, dst=os.path.join(dst, "tasksel"))
        copy(self, "registry.json", src=stage, dst=dst)
        snapshot = "debian-science_%s.json" % self.version
        copy(self, snapshot, src=os.path.join(src, "dependency_data"),
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
