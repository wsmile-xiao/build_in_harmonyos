#!/usr/bin/env python3
"""Conan recipe — debichem 0.0.12 (Debian Pure Blend, metadata/task package).

Debichem is a Debian Pure Blend (computational chemistry): one Debian-native
source package generates 13 Architecture:all binary packages — `debichem-tasks`
(tasksel description) + 12 `debichem-<task>` metapackages whose real payload is
metadata (a one-line title file under /usr/share/blends/tasks/debichem/ and
dpkg Depends/Recommends/Suggests lists). There is no compiled library; all the
"software selection" lives in the 12 Deb822 task files under tasks/.

Conan modelling decision (honest, zero fake linkage):
  - single recipe, data/metadata package (`package_type="unknown"`);
  - package() ships the authentic source artifacts: the 12 task files, the
    genblends-produced debichem-tasks.desc, and a machine-readable
    registry.json derived in build() straight from those task files (no apt,
    no external tooling). No fake executables/libs. No Depends are translated
    into Conan `requires` — they are OS/distro package selections
    (metadata-only); Conan requires list is empty.
  - Debian semantic recorded verbatim: old-format task files (no `Format:`
    header) make genblends lower file-level `Depends:` to metapackage
    `Recommends:` and `Suggests:` to `Suggests:`; each metapackage additionally
    `Depends: debichem-tasks (=version)`. This mapping is embedded in the
    generated registry so consumers can reconstruct the Debian meaning.
"""
import json
import os
import re

from conan import ConanFile
from conan.tools.files import copy, get


def _deb822_parse_paragraph(text):
    """Very small Deb822 reader tuned to blends task files: returns a dict of
    {field: [values]} for repeated single-line fields plus folded text."""
    fields = {}
    cur = None
    for raw in text.splitlines():
        if raw.startswith((" ", "\t")):
            if cur is not None:
                fields[cur][-1] += "\n" + raw.strip()
            continue
        m = re.match(r"^([A-Za-z][A-Za-z0-9-]*):\s*(.*)$", raw)
        if m:
            cur = m.group(1)
            fields.setdefault(cur, []).append(m.group(2).strip())
        else:
            cur = None
    return {k: (v[0] if len(v) == 1 else v) for k, v in fields.items()}


def _task_title_description(paragraph):
    title = ""
    desc = ""
    t = paragraph.get("Task")
    title = t[0] if isinstance(t, list) else (t or "")
    d = paragraph.get("Description")
    if isinstance(d, list):
        d = d[0]
    desc = (d or "").splitlines()[0] if d else ""
    return title.strip(), desc.strip()


class DebichemConan(ConanFile):
    name = "debichem"
    version = "0.0.12"
    package_type = "unknown"

    settings = "os", "compiler", "build_type", "arch"  # CI L0 gate; data pkg, no real semantics
    options = None
    default_options = None

    def requirements(self):
        pass  # 零 Conan requires：全部 Depends/Recommends/Suggests 是 OS 包选择（metadata-only）

    def layout(self):
        self.folders.source = "."

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        # 纯解析：tasks/* (Deb822) → registry.json（不调用 apt/blends；与 genblends
        # 无关部分一致：Depends→recommends 语义降级记录在 json，不改写文件）
        src = self.source_folder
        task_dir = os.path.join(src, "tasks")
        registry = {"version": "0.0.12", "blend": "debichem", "tasks": [],
                    "semantics": {
                        "source": "Debian Pure Blend (debichem) 0.0.12",
                        "metapackage_rule": ("old-format task files (no 'Format:' header) -> "
                                             "genblends lowers file-level Depends to metapackage "
                                             "Recommends; Suggests stays Suggests; each metapackage "
                                             "also Depends: debichem-tasks (=version)"),
                        "conan_requires": "none (all OS/distro package selections are metadata-only)"}}
        for fn in sorted(os.listdir(task_dir)):
            path = os.path.join(task_dir, fn)
            if not os.path.isfile(path):
                continue
            para = _deb822_parse_paragraph(open(path, encoding="utf-8", errors="replace").read())
            title, synopsis = _task_title_description(para)
            depends = sorted(v for v in _as_list(para.get("Depends")) if v)
            suggests = sorted(v for v in _as_list(para.get("Suggests")) if v)
            registry["tasks"].append({
                "file": fn,
                "key": f"debichem-{fn}",
                "title": title,
                "description_synopsis": synopsis,
                "file_depends": depends,      # task 文件原文 Depends
                "file_suggests": suggests,    # task 文件原文 Suggests
                "debian_metapackage_recommends": depends,  # 旧格式降级规则
            })
        out = os.path.join(self.build_folder, "stage")
        os.makedirs(out, exist_ok=True)
        with open(os.path.join(out, "registry.json"), "w", encoding="utf-8") as fh:
            json.dump(registry, fh, ensure_ascii=False, indent=1, sort_keys=True)

    def package(self):
        src = self.source_folder
        stage = os.path.join(self.build_folder, "stage")
        dst = os.path.join(self.package_folder, "share", "debichem")
        copy(self, "*", src=os.path.join(src, "tasks"), dst=os.path.join(dst, "tasks"))
        copy(self, "debichem-tasks.desc", src=src, dst=os.path.join(dst, "tasksel"))
        copy(self, "registry.json", src=stage, dst=dst)
        cp = os.path.join(src, "debian", "copyright")
        if os.path.exists(cp):
            copy(self, "copyright", src=os.path.dirname(cp),
                 dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = []
        self.cpp_info.resdirs = ["share"]


def _as_list(v):
    if v is None:
        return []
    return v if isinstance(v, list) else [v]
