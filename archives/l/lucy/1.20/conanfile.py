#!/usr/bin/env python3
"""Conan recipe for Lucy 1.20 — TIGR DNA sequence quality and vector trimming tool.

Lucy prepares raw DNA sequence fragments for sequence assembly: quality
assessment, confidence reassurance, vector trimming and vector removal.  It is
a fully integrated, stand-alone program (no database, no dependencies) that
reads multi-FASTA sequence + phred quality files and writes the surviving
sequences plus a per-sequence cleavage coordinate report.

Upstream ships a **raw Makefile** (targets: `all`, `lucy`, `beep`, `clean`; no
`configure`, no `install`, no `check`).  Its documented self-test lives in
`README.FIRST` §Testing and is driven by the bundled ABI fixture (`atie.seq` /
`atie.qul` / `atie.2nd`), the vector fixtures (`PUC19`, `PUC19splice`) and the
golden cleave report `lucy.debug`.  That procedure is shipped here as
`check/upstream-regression.sh` and executed from `build()` so that a plain
`conan create` runs the upstream suite (TEST_QUALITY_SPEC layer 1).

OHOS notes
----------
* The upstream Makefile hardcodes ``CC = cc``; the OHOS sysroot only provides
  clang, so ``CC`` is injected from the Conan toolchain conf.  R33: the recipe
  never reads ``${CC}``/``${CFLAGS}`` from the shell environment.
* ``LIBS = -lpthread`` resolves against the OHOS musl libc; the threaded build
  is exercised by the regression test (single-thread vs ``-x N`` equivalence).
* No patches are required — the 1.20 sources compile with clang 15 as-is.
* The build product is a CLI tool, so the software-level ``commands.json`` is
  declared (R38).
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.env import VirtualBuildEnv
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
)
from conan.tools.layout import basic_layout


class LucyConan(ConanFile):
    name = "lucy"
    version = "1.20"
    description = (
        "Lucy — prepares raw DNA sequence fragments for sequence assembly: "
        "quality assessment, confidence reassurance, vector trimming and "
        "vector removal"
    )
    license = "Artistic-1.0"
    homepage = "https://lucy.sourceforge.net"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "application"
    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)
        # Upstream has no `check` target; ship the README.FIRST §Testing
        # procedure (plus its OHOS case) so build() can run it.
        copy(self, "check/*", self.recipe_folder, self.export_sources_folder)

    def layout(self):
        basic_layout(self)

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration("lucy supports Linux/OHOS only")

    def generate(self):
        VirtualBuildEnv(self).generate()

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        # 1.20 needs no patch (conandata declares `patches: []`), but the
        # standard hook is kept so a future portability fix only has to add an
        # entry to conandata.yml.
        apply_conandata_patches(self)

        # R33: compiler comes from the Conan toolchain conf, never from ${CC}.
        # (the OHOS conan does not register the `:c` sub-key form, so read the
        #  whole dict — repo convention, see archives/*/*/*/conanfile.py)
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ) or {}
        cc = compilers.get("c", "clang")
        # lucy's build system is a raw in-source Makefile with no out-of-tree
        # support, so both the build and the test run happen in source_folder.
        # R9: single job.  `make` builds the `lucy` target plus upstream's
        # `beep` no-op target; upstream's own CFLAGS (-O) are left untouched so
        # the Conan buildenv flags are not shadowed.
        src = self.source_folder.replace("\\", "/")
        self.run(f"cd '{src}' && make -j1 CC={cc}", env="conanbuild")

        # ── Layer 1: upstream official test suite (README.FIRST §Testing) ──
        shell = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        check = os.path.join(src, "check", "upstream-regression.sh")
        self.run(f'{shell} "{check}" "{src}"', env="conanbuild")

    def package(self):
        src = self.source_folder.replace("\\", "/")
        copy(self, "lucy", src, os.path.join(self.package_folder, "bin"))
        copy(self, "lucy.1", src,
             os.path.join(self.package_folder, "share", "man", "man1"))
        # copy() does not guarantee the executable bit on every platform.
        binary = os.path.join(self.package_folder, "bin", "lucy")
        if os.path.isfile(binary):
            os.chmod(binary, 0o755)

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.runenv_info.prepend_path(
            "PATH", os.path.join(self.package_folder, "bin")
        )
        self.buildenv_info.prepend_path(
            "PATH", os.path.join(self.package_folder, "bin")
        )
