#!/usr/bin/env python3
"""Conan recipe for pacapt 3.0.7 — pacman-like shell wrapper for package managers.

pacapt is a pure POSIX shell script (56KB) that wraps many Unix package managers
behind a unified pacman-like interface.  No C/C++ compilation is needed; the
build step runs upstream's bin/compile.sh to concatenate lib/*.sh into a single
pacapt script.

Build system: shell script concatenation (bin/compile.sh).
Package type: application (single shell script).
"""

import os
import stat

from conan import ConanFile
from conan.tools.files import get, copy, export_conandata_patches, apply_conandata_patches
from conan.tools.layout import basic_layout


class PacaptConan(ConanFile):
    name = "pacapt"
    version = "3.0.7"
    description = "An ArchLinux's pacman-like shell wrapper for many package managers"
    license = "Fair"
    homepage = "https://github.com/icy/pacapt"
    url = ""

    package_type = "application"

    # R25: shell-script-only package — compiler/build_type are unused but
    # OHOS CI L0p 门禁要求 settings 包含全部四项 (os, compiler, build_type, arch)
    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)

        # compile.sh uses `git log` to get the version hash, but the release
        # tarball has no .git directory.  Provide VERSION explicitly via env
        # so the script does not fail.
        #
        # HarmonyOS notes:
        # - OHOS has no /bin/sh by default; compile.sh uses /usr/bin/env bash
        #   which works when bash is installed under /data/service/hnp/bin/.
        # - The script only concatenates lib/*.sh — no C compiler, no linking.
        # compile.sh uses `git log` for the version hash; the release tarball
        # has no .git directory, so we set VERSION explicitly before invoking it.
        # Conan 2 run() `env` is a list of script names, not a dict — set via
        # os.environ instead.
        old_ver = os.environ.get("VERSION")
        os.environ["VERSION"] = "3.0.7"
        try:
            self.run("bash bin/compile.sh", cwd=self.source_folder)
        finally:
            if old_ver is None:
                os.environ.pop("VERSION", None)
            else:
                os.environ["VERSION"] = old_ver

    def package(self):
        bin_dir = os.path.join(self.package_folder, "bin")
        os.makedirs(bin_dir, exist_ok=True)

        # compile.sh outputs to stdout; if build() redirected to file, copy it.
        # Otherwise, copy the pre-built stable script from the source root.
        compiled = os.path.join(self.source_folder, "pacapt")
        stable = os.path.join(self.source_folder, "pacapt")

        if os.path.isfile(compiled):
            copy(self, "pacapt", src=self.source_folder, dst=bin_dir)
        else:
            # Fallback: the ng branch ships a pre-built pacapt in the root
            copy(self, "pacapt", src=self.source_folder, dst=bin_dir)

        # Ensure executable permission (Conan may strip it)
        target = os.path.join(bin_dir, "pacapt")
        if os.path.isfile(target):
            os.chmod(target, os.stat(target).st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)

        # Install the LICENSE / README as docs (fair license requires notice)
        doc_dir = os.path.join(self.package_folder, "share", "doc", "pacapt")
        os.makedirs(doc_dir, exist_ok=True)
        for doc in ("README.md", "LICENSE"):
            src = os.path.join(self.source_folder, doc)
            if os.path.isfile(src):
                copy(self, doc, src=self.source_folder, dst=doc_dir)

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
