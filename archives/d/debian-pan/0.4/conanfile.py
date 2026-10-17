#!/usr/bin/env python3
"""Conan recipe — debian-pan 0.4 (Debian Pure Blend, metadata/task package).

Debian Pan (PAN = Photons And Neutrons) is a Debian Pure Blend for X-ray and
neutron science: one Debian-native source package (35 files) generates 18
`Architecture: all` binary packages — `pan-tasks` (the tasksel description
package), `pan-config` (the blend config package), plus 16 `pan-<topic>`
metapackages whose real payload is metadata (a Deb822 task file under
tasks/, a tasksel description entry, and dpkg Depends/Recommends/Suggests
lists). There is no compiled library, no executable and no C/C++ source: all
the "software selection" lives in the 18 Deb822 task files under tasks/.

Conan modelling decision (honest, zero fake linkage):
  - single recipe, data/metadata package (`package_type="unknown"`);
  - package() ships the authentic upstream artifacts: the 18 task files, the
    genblends-produced debian-pan-tasks.desc, the official machine-readable
    dependency snapshot dependency_data/debian-pan_0.4.json, and a
    registry.json derived in build() straight from those task files and the
    debian/control stanzas (no apt, no blends-dev, no genblends, no external
    tooling). No fake executables or libraries.
  - No Debian dependency is translated into Conan `requires`: the 446 distinct
    entries in the 0.4 snapshot are OS/distro package selections
    (metadata-only), so the Conan requires list stays empty. Mechanically
    copying them would fabricate an unsatisfiable dependency graph.
  - Debian semantic recorded verbatim: unlike the older blends packages, the
    debian-pan 0.4 task files use the NEW blends 1.1 format and carry an
    explicit `Format: https://blends.debian.org/blends/1.1` header. The task
    list is expressed with file-level `Recommends:`/`Suggests:` and no
    file-level `Depends:`; every `pan-<topic>` metapackage additionally
    `Depends: pan-config (= ${source:Version})` and
    `pan-tasks (= ${source:Version})`. This mapping is embedded in the
    generated registry so consumers can reconstruct the Debian meaning.
  - Note the mapping asymmetry (recorded in the registry, not "fixed"): the
    task file set is a strict superset of the metapackage set — `laue` and
    `mx-dev` have task files but no `pan-laue`/`pan-mx-dev` metapackage.
"""
import json
import os
import re

from conan import ConanFile
from conan.tools.files import (apply_conandata_patches, copy,
                              export_conandata_patches, get)


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


class DebianPanConan(ConanFile):
    name = "debian-pan"
    version = "0.4"
    package_type = "unknown"
    description = ("Debian Pan Pure Blend (PAN = Photons And Neutrons) task/metapackage "
                   "metadata: 18 Architecture: all binary packages, no compilable code")
    license = "GPL-3"
    homepage = "https://salsa.debian.org/blends-team/pan"
    url = ""  # CI fills this

    settings = "os", "compiler", "build_type", "arch"  # CI L0 gate; data package, no real semantics
    options = None
    default_options = None

    def export_sources(self):
        # 本包 patches 为空（patches: {}），此处仅为 CI G1 配方完整性契约；
        # export_conandata_patches 对空 patches 段是 no-op。
        export_conandata_patches(self)

    def requirements(self):
        pass  # 零 Conan requires：全部 Depends/Recommends/Suggests 是 OS 包选择（metadata-only）

    def layout(self):
        self.folders.source = "."

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        # patches: {} 为空段 → no-op；保持与全仓无补丁配方的统一契约。
        apply_conandata_patches(self)
        # 纯解析：tasks/* (Deb822) + debian/control 段落 + tasksel desc + 官方快照
        # -> registry.json（不调用 apt/blends-dev/genblends；不重写任何上游文件）
        src = self.source_folder
        task_dir = os.path.join(src, "tasks")
        version = str(self.version)

        # --- debian/control：18 个二进制包声明（pan-tasks + pan-config + 16 元包）---
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

        # --- tasks/*：18 个 Deb822 任务文件（新格式，带 Format: 1.1 头）---
        tasks = []
        task_formats = set()
        for fn in sorted(os.listdir(task_dir)):
            path = os.path.join(task_dir, fn)
            if not os.path.isfile(path):
                continue
            with open(path, encoding="utf-8", errors="replace") as fh:
                para = _deb822_parse_paragraph(fh.read())
            fmt = _first(para.get("Format")).strip()
            if fmt:
                task_formats.add(fmt)
            title = _first(para.get("Task")).strip()
            desc = _first(para.get("Description"))
            depends = sorted(v for v in _as_list(para.get("Depends")) if v)
            suggests = sorted(v for v in _as_list(para.get("Suggests")) if v)
            recommends = sorted(v for v in _as_list(para.get("Recommends")) if v)
            install = _first(para.get("Install")).strip().lower()
            metapackage = _first(para.get("Metapackage")).strip().lower()
            tasks.append({
                "file": fn,
                "format": fmt,
                "task_title": title,
                "description_synopsis": desc.splitlines()[0].strip() if desc else "",
                "comment": _first(para.get("Comment")).strip(),
                "wnpp": sorted(v for v in _as_list(para.get("WNPP")) if v),
                "install": install if install in ("true", "false") else None,
                "metapackage": metapackage if metapackage in ("true", "false") else None,
                "file_depends": depends,
                "file_recommends": recommends,
                "file_suggests": suggests,
                # 新格式（blends 1.1）：任务文件不写文件级 Depends，
                # 元包 Recommends/Suggests 直接沿用文件级 Recommends/Suggests。
                "debian_metapackage_recommends": recommends,
                "debian_metapackage_suggests": suggests,
            })

        # --- tasksel desc：父 debian-pan + 16 个 pan-<topic> 子任务 ---
        desc_tasks = []
        desc_keys = []
        desc_path = os.path.join(src, "debian-pan-tasks.desc")
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

        # --- 官方机器可读依赖快照（0.1 -> 0.4 系列，仅登记 0.4 + 序列）---
        dep_dir = os.path.join(src, "dependency_data")
        snapshot_files = []
        snapshot_04 = {}
        if os.path.isdir(dep_dir):
            snapshot_files = sorted(f for f in os.listdir(dep_dir) if f.endswith(".json"))
            cur = os.path.join(dep_dir, "debian-pan_%s.json" % version)
            if os.path.isfile(cur):
                with open(cur, encoding="utf-8") as fh:
                    snapshot_04 = json.load(fh)

        snapshot_refs = set()
        for topic, entry in snapshot_04.items():
            if not isinstance(entry, dict):
                continue
            for field in ("depends", "recommends", "suggests"):
                for ref in entry.get(field, []) or []:
                    ref = str(ref).strip()
                    if ref and ref != "\\":
                        snapshot_refs.add(ref)

        registry = {
            "version": version,
            "blend": "debian-pan",
            "semantics": {
                "source": "Debian Pure Blend (debian-pan) %s" % version,
                "blends_format": ("new format (blends 1.1, explicit 'Format:' header): "
                                  "task files carry file-level Recommends/Suggests and "
                                  "no file-level Depends; each pan-<topic> metapackage "
                                  "Depends: pan-config (= ${source:Version}) + "
                                  "pan-tasks (= ${source:Version})"),
                "metapackage_rule": ("new-format task files (with 'Format:' header) -> "
                                     "file-level Recommends maps to metapackage "
                                     "Recommends; Suggests stays Suggests; each metapackage "
                                     "also Depends: pan-config + pan-tasks (=%s)" % version),
                "mapping_asymmetry": ("task file set is a strict superset of the "
                                      "metapackage set: 'laue' and 'mx-dev' have task "
                                      "files but no pan-laue/pan-mx-dev metapackage "
                                      "(recorded verbatim, not normalised)"),
                "conan_requires": "none (all OS/distro package selections are metadata-only)",
                "snapshot_refs": "counted from dependency_data/debian-pan_%s.json" % version,
            },
            "counts": {
                "task_files": len(tasks),
                "task_formats": sorted(task_formats),
                "desc_paragraphs": len(desc_tasks),
                "desc_keys": len(desc_keys),
                "control_packages": len(control_pkgs),
                "arch_all_packages": sum(1 for p in control_pkgs if p["architecture"] == "all"),
                # 元包 = pan-<主题>，不含基础设施包 pan-tasks / pan-config
                "metapackages": sum(1 for p in control_pkgs
                                    if p["package"].startswith("pan-")
                                    and p["package"] not in ("pan-tasks", "pan-config")),
                "snapshot_files": len(snapshot_files),
                "snapshot_refs_0_4": len(snapshot_refs),
            },
            "tasks": tasks,
            "desc_tasks": desc_tasks,
            "desc_keys": desc_keys,
            "control_packages": control_pkgs,
            "snapshot": {
                "file": "debian-pan_%s.json" % version,
                "topics": sorted(snapshot_04.keys()),
                "distinct_refs": len(snapshot_refs),
            },
        }

        out = os.path.join(self.build_folder, "stage")
        os.makedirs(out, exist_ok=True)
        with open(os.path.join(out, "registry.json"), "w", encoding="utf-8") as fh:
            json.dump(registry, fh, ensure_ascii=False, indent=1, sort_keys=True)

        self.output.info("=== debian-pan %s registry built ===" % version)
        self.output.info("  task files        : %d" % len(tasks))
        self.output.info("  task formats      : %s" % ", ".join(sorted(task_formats)))
        self.output.info("  desc paragraphs   : %d (keys: %d)" % (len(desc_tasks), len(desc_keys)))
        self.output.info("  control packages  : %d (arch:all: %d, pan-*: %d)"
                         % (len(control_pkgs), registry["counts"]["arch_all_packages"],
                            registry["counts"]["metapackages"]))
        self.output.info("  snapshot files    : %d" % len(snapshot_files))
        self.output.info("  distinct OS refs  : %d" % len(snapshot_refs))

    def package(self):
        src = self.source_folder
        stage = os.path.join(self.build_folder, "stage")
        dst = os.path.join(self.package_folder, "share", "debian-pan")
        copy(self, "*", src=os.path.join(src, "tasks"), dst=os.path.join(dst, "tasks"))
        copy(self, "debian-pan-tasks.desc", src=src, dst=os.path.join(dst, "tasksel"))
        copy(self, "registry.json", src=stage, dst=dst)
        snapshot = "debian-pan_%s.json" % self.version
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
