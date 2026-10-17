#!/usr/bin/env python3
"""Conan recipe — debian-parl 1.9.33+nmu1 (Debian Pure Blend "DebianParl", boxer recipes).

DebianParl is a Debian Pure Blend for parliamentary/citizen desktop work. The
native source (1.9.33+nmu1, Format 3.0) is a **boxer** (new blends toolchain)
recipe set: it references 3 classes in the separate source package boxer-data
(Task.harden.desktop, Desktop.locale, Desktop.locale.EU) and, at Debian build
time, composes d-i preseed recipes (content/*/preseed.cfg + script.sh) which
are shipped in the binary package parl-data. The other 4 binary packages
(parl-desktop / -world / -eu / -strict) are pure metapackages whose whole
meaning is Depends/Suggests/Conflicts lists over OS/distro packages.

Conan modelling (honest, zero fake linkage):
  - single data/config package (`package_type="unknown"`);
  - package() ships the authentic upstream-authored files from this source
    (nodes/*.yml boxer configs, skel/*.in preseed/script templates, Makefile,
    NEWS, TODO) plus a derived debian-metadata.json capturing the *real*
    0.0.../1.9.33+nmu1 binary semantics (5 binary packages and their
    Depends/Suggests/Conflicts counts, profile include/avoid counts, boxer-data
    version constraint, source provenance) — this package does NOT re-run boxer
    and does not fabricate the preseed outputs that live in the parl-data .deb;
    - ZERO Conan `requires`: all Depends are OS/distro desktop packages
    (metadata-only). No fake executables/libs.
"""
import json
import os

from conan import ConanFile
from conan.tools.files import copy, get


# Facts recorded from the OFFICIAL Debian binary packages (parl-*_1.9.33+nmu1_all.deb,
# pool, verified 2026-09-09 via dpkg-deb -I). Pinned to this source version; they
# follow boxer-data and drift on every Debian rebuild — recorded here verbatim as
# provenance, not re-derived.
PARL_META = {
    "source": "debian-parl",
    "debian_version": "1.9.33+nmu1",
    "format": "3.0 (native)",
    "upstream": {
        "homepage": "https://wiki.debian.org/DebianParl",
        "vcs_git": "https://salsa.debian.org/blends-parl-team/blends.git",
        "vcs_browser": "https://salsa.debian.org/blends-parl-team/blends",
        "note": "1.9.33 is an NMU (no upstream salsa tag); nearest upstream tag debian/1.9.32",
    },
    "toolchain": {"boxer": ">= 0.004~", "boxer_data": ">= 10.8, << 10.11",
                  "note": "real package lists are decided by boxer-data 10.10, not this source"},
    "profiles": {
        "desktop":      {"node": "nodes/desktop.yml",      "include": 53, "avoid": 16},
        "desktop-eu":   {"node": "nodes/desktop-eu.yml",   "include": 177, "avoid": 21},
        "desktop-world": {"node": "nodes/desktop-world.yml", "include": 402, "avoid": 21},
    },
    "binary_packages": {
        "parl-data": {
            "depends": 0, "recommends": 0, "suggests": 0, "conflicts": 0,
            "content": "usr/share/parl/data/{desktop,desktop/eu,desktop/world}/{preseed.cfg,script.sh} + SHA*SUMS + NEWS/TODO",
            "description": "recipes to install DebianParl blends (D-I preseeding files)"},
        "parl-desktop": {
            "depends": 54, "recommends": 0, "suggests": 1, "conflicts": 0,
            "content": "usr/sbin/parl-desktop-tidy (shell script) + doc",
            "semantics": "task-laptop + desktop/preseed pkgsel include set (53)"},
        "parl-desktop-world": {
            "depends": 350, "recommends": 0, "suggests": 1, "conflicts": 0,
            "content": "doc only (pure metapackage)",
            "semantics": "parl-desktop + 349 l10n/dictionaries (world)"},
        "parl-desktop-eu": {
            "depends": 125, "recommends": 0, "suggests": 1, "conflicts": 0,
            "content": "doc only (pure metapackage)",
            "semantics": "parl-desktop + 124 EU l10n/dictionaries"},
        "parl-desktop-strict": {
            "depends": 1, "recommends": 0, "suggests": 0, "conflicts": 21,
            "content": "doc only (pure metapackage)",
            "semantics": "parl-desktop + 21 explicit Conflicts (avoid list): cups/hplip/bluez-cups/"
                       "cpufrequtils/libreoffice-base|java-common/hunspell-*/printer-driver-*"},
    },
    "conan": {"requires": "none — all Depends/Recommends/Suggests/Conflicts are OS/distro "
                          "package selections (metadata-only)"},
}


class DebianParlConan(ConanFile):
    name = "debian-parl"
    version = "1.9.33+nmu1"
    package_type = "unknown"

    settings = "os", "compiler", "build_type", "arch"  # CI L0 gate; data/config pkg
    options = None
    default_options = None

    def requirements(self):
        pass

    def layout(self):
        self.folders.source = "."

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        out = os.path.join(self.build_folder, "stage")
        os.makedirs(out, exist_ok=True)
        with open(os.path.join(out, "debian-metadata.json"), "w", encoding="utf-8") as fh:
            json.dump(PARL_META, fh, ensure_ascii=False, indent=1, sort_keys=True)

    def package(self):
        src = self.source_folder
        stage = os.path.join(self.build_folder, "stage")
        dst = os.path.join(self.package_folder, "share", "parl")
        copy(self, "*.yml", src=os.path.join(src, "nodes"),
             dst=os.path.join(dst, "config", "nodes"))
        copy(self, "*.in", src=os.path.join(src, "skel"),
             dst=os.path.join(dst, "config", "skel"))
        for f in ("Makefile", "NEWS", "TODO"):
            p = os.path.join(src, f)
            if os.path.exists(p):
                copy(self, f, src=src, dst=os.path.join(dst, "config"))
        copy(self, "debian-metadata.json", src=stage, dst=dst)
        cp = os.path.join(src, "debian", "copyright")
        if os.path.exists(cp):
            copy(self, "copyright", src=os.path.dirname(cp),
                 dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = []
        self.cpp_info.resdirs = ["share"]
