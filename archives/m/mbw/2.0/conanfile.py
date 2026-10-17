#!/usr/bin/env python3
"""Conan recipe for mbw 2.0 (memory bandwidth benchmark).

mbw is a small dependency-free C benchmark that measures memory read/write
bandwidth by timing memcpy / dumb-copy loops between two large in-memory
arrays.  The upstream build is a bare Makefile that compiles the single
mbw.c into the `mbw` executable using the system C compiler; it only uses
libc (calloc/memcpy/gettimeofday/getopt/printf), so it compiles cleanly
under the OHOS clang toolchain with no configure step and no third-party
dependencies.

This recipe follows the repo's raw-make tool pattern (cf. 7zip): build the
executable, install it into bin/, and validate with a consumer that runs the
binary on a small array.
"""

import os
import shutil

from conan import ConanFile
from conan.tools.env import VirtualBuildEnv
from conan.tools.files import copy, get
from conan.tools.layout import basic_layout


class MbwConan(ConanFile):
    name = "mbw"
    version = "2.0"
    description = "Memory bandwidth benchmark (mbw)"
    license = "GPL-2.0"
    homepage = "https://github.com/raas/mbw"
    url = "https://github.com/raas/mbw"
    package_type = "application"
    settings = "os", "arch", "compiler", "build_type"
    exports_sources = "conandata.yml"

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"][str(self.version)], strip_root=True)

    def build(self):
        # Bare Makefile: `mbw: mbw.c` compiles with the ambient CC.  Use the
        # OHOS clang toolchain explicitly and -j1 to mirror the CI-verified
        # pattern used elsewhere in this repo (workers lack /tmp and have no
        # build uid in /etc/passwd, so parallel make can race on temp files).
        tmpdir = os.path.join(self.build_folder, "tmp")
        os.makedirs(tmpdir, exist_ok=True)
        cc = self._compiler_executable("c", "clang")
        with VirtualBuildEnv(self).vars().apply():
            self.run(
                f"make -C {self.source_folder} CC={cc} -j1 "
                f"TMPDIR={tmpdir} TMP={tmpdir} TEMP={tmpdir}"
            )

    def _compiler_executable(self, key, fallback_name):
        executables = self.conf.get(
            "tools.build:compiler_executables",
            default={},
            check_type=dict,
        ) or {}
        configured = executables.get(key)
        if configured and os.path.isfile(configured):
            return configured
        found = shutil.which(fallback_name)
        return found or configured or fallback_name

    def package(self):
        copy(
            self,
            "mbw",
            self.source_folder,
            os.path.join(self.package_folder, "bin"),
            keep_path=False,
        )
        copy(
            self,
            "mbw.1",
            self.source_folder,
            os.path.join(self.package_folder, "share", "man", "man1"),
            keep_path=False,
        )
        copy(
            self,
            "LICENSE",
            self.source_folder,
            os.path.join(self.package_folder, "licenses"),
            keep_path=False,
        )

    def package_info(self):
        self.output.info(f"mbw benchmark installed to bin/mbw")
