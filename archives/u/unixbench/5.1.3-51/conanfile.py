#!/usr/bin/env python3
"""Conan recipe for unixbench 5.1.3-51 — BYTE UNIX Benchmarks (byte-unixbench).

UnixBench is the classic BYTE Magazine Unix benchmark suite: a Perl driver
(`Run`) that compiles, selects and executes a set of C benchmark programs
(CPU/arithmetic, process, pipe, system call, file I/O, shell and X11 graphics)
and normalises the scores against a baseline (`pgms/index.base`).

OHOS adaptation notes (HarmonyOS PC, aarch64):

* One portability patch (`patches/0001-src-arith.c.patch`): marks the
  SIGALRM-updated counter in `src/arith.c` `volatile`.  With clang -O2 the
  counter otherwise stays in a register (no external calls inside the pure
  computation loop), so every selectable arithmetic benchmark reports
  `COUNT|0` and `Run` aborts with "Can't take log of 0".  The Makefile itself
  is unmodified; the suite builds with the OHOS SDK clang via
  `make CC=<clang>`; the upstream Makefile hardcodes `CC=gcc`, so the compiler
  is passed from the Conan conf (`tools.build:compiler_executables`, R33),
  never from a bare shell variable.
* Graphics tests stay disabled, as upstream ships them disabled by default
  (`GRAPHIC_TESTS` is commented out in the Makefile).  Building them would
  require X11 headers/libs and `x11perf`, none of which exist on OHOS.
* The tarball expands to `byte-unixbench-5.1.3/UnixBench/...`; `source()`
  promotes the nested `UnixBench/` directory to the source root so the
  Makefile, the shipped patch and `package()` all share one root.
* `package()` ships the complete prebuilt run directory under
  `bin/unixbench` so consumers can copy it to a writable directory and run
  `perl Run [options] [tests]` without a compiler.  `Run`'s
  `preChecks()` calls `make check`; with the shipped timestamps the targets
  are already up to date, so no compiler is invoked.  Copy with
  `cp -a` (preserve timestamps) — see README.md.
* No `install` target exists upstream; artifacts are copied directly.
* License: GitHub declares GPL-2.0; the v5.1.3 tarball carries no standalone
  LICENSE file, so the archive ships a provenance note instead of a fabricated
  licence text (see notes.md).
"""

import os
import shutil

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
    save,
)
from conan.tools.layout import basic_layout

required_conan_version = ">=2.0"


class UnixbenchConan(ConanFile):
    name = "unixbench"
    version = "5.1.3-51"
    description = (
        "BYTE UNIX Benchmarks (byte-unixbench) 5.1.3: CPU, arithmetic, process, "
        "pipe, system call, file I/O and shell benchmark suite with index scoring"
    )
    license = "GPL-2.0"
    homepage = "https://github.com/kdlucas/byte-unixbench"
    url = "https://atomgit.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    topics = ("benchmark", "unixbench", "byte-unixbench", "performance", "cpu")
    package_type = "application"
    settings = "os", "arch", "compiler", "build_type"

    def export_sources(self):
        export_conandata_patches(self)

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "unixbench targets POSIX systems (perl driver, POSIX shell and C "
                f"benchmarks); got {self.settings.os}"
            )

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        # GitHub tag tarball expands to byte-unixbench-<ver>/UnixBench/...; after
        # strip_root the suite sits one level deep in UnixBench/.  Promote its
        # contents to the source root so the Makefile, patches and packaging all
        # share the same root (the repo patch tooling diffs .orig/.work, whose
        # root is the suite root).
        sub = os.path.join(self.source_folder, "UnixBench")
        if os.path.isdir(sub):
            for item in os.listdir(sub):
                shutil.move(os.path.join(sub, item), self.source_folder)
            os.rmdir(sub)

    def _suite_dir(self):
        suite = self.source_folder
        if not os.path.isfile(os.path.join(suite, "Makefile")):
            raise ConanException(
                "unixbench suite not found: expected Makefile under {0}".format(suite)
            )
        return suite

    def build(self):
        # Apply the shipped portability patch (src/arith.c volatile) through
        # the standard conandata hook.
        apply_conandata_patches(self)
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        )
        cc = compilers.get("c", "clang") if compilers else "clang"
        # R9: -j1; R33: compiler path from Conan conf, not a bare shell variable.
        self.run('make -j1 CC="{0}"'.format(cc), cwd=self._suite_dir())

    def package(self):
        suite = self._suite_dir()
        dst = os.path.join(self.package_folder, "bin", "unixbench")
        for name in ("Makefile", "Run", "USAGE", "README", "WRITING_TESTS"):
            copy(self, name, src=suite, dst=dst)
        copy(self, "pgms/*", src=suite, dst=dst)
        copy(self, "src/*", src=suite, dst=dst)
        copy(self, "testdir/*", src=suite, dst=dst)
        # `Run` requires tmp/ (kill_run) and results/ (report files) to exist;
        # Conan packages do not keep empty directories, so keep placeholders.
        save(self, os.path.join(dst, "tmp", ".keep"), "")
        save(self, os.path.join(dst, "results", ".keep"), "")
        save(
            self,
            os.path.join(self.package_folder, "licenses", "README.license"),
            "unixbench (byte-unixbench) is distributed under the GNU General "
            "Public License v2.0 as declared by the upstream repository "
            "https://github.com/kdlucas/byte-unixbench . The v5.1.3 source "
            "tarball does not ship a standalone LICENSE file; no licence text "
            "was fabricated for this package.\n",
        )

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.runenv_info.prepend_path(
            "PATH", os.path.join(self.package_folder, "bin", "unixbench")
        )
        self.runenv_info.prepend_path(
            "PATH", os.path.join(self.package_folder, "bin", "unixbench", "pgms")
        )
