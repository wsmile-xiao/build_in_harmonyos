#!/usr/bin/env python3
"""Conan recipe for mtx 1.3.12 (Autotools, SCSI media changer CLI tools).

MTX drives SCSI media changers and tape drives. On Linux/OHOS the SCSI
pass-through goes through the SCSI generic interface (`<scsi/sg.h>`,
`SG_IO`), which the OHOS musl sysroot provides, so the upstream Linux
backend is used unchanged.  What does need patching is the 2004 vintage
autoconf machinery shipped in the release tarball: its `config.guess`
has no HarmonyOS branch, and its `config.sub` knows neither `aarch64`
nor the `linux-ohos` triplet, so `--host=aarch64-linux-ohos` aborts
configure.  `configure.in` itself already matches `*linux*`, so
`TARGET=linux` and `AC_DEFINE(LINUX)` come out right without changes.

Upstream `make install` ignores `DESTDIR` and writes straight into
`$(sbindir)`, which would escape the Conan package folder, and it reads
the preformatted man pages by bare name even though `basic_layout()`
builds out of source.  `0003-Makefile.in-destdir-and-srcdir-man.patch`
fixes both so `Autotools.install()` can stage the package.
"""

import os
import re

from conan import ConanFile
from conan.tools.files import (
    apply_conandata_patches,
    export_conandata_patches,
    get,
    load,
)
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class MtxConan(ConanFile):
    name = "mtx"
    version = "1.3.12"
    description = "SCSI media changer and tape drive control tools"
    license = "GPL-2.0-or-later"
    homepage = "https://sourceforge.net/projects/mtx/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        tc.generate()

    def _has_upstream_check_target(self):
        """MTX ships no test suite, so gate the layer-1 hook on the target.

        `make -n check` on this Makefile fails with "No rule to make target",
        which would abort the build; running it only when a project actually
        provides the target keeps the TEST_QUALITY_SPEC layer-1 hook honest
        without inventing a passing result.  The exemption is declared in
        test_package/MANIFEST.yml (upstream_test_in_build: false).
        """
        makefile = load(self, os.path.join(self.source_folder, "Makefile.in"))
        return re.search(r"^check\s*:", makefile, re.MULTILINE) is not None

    def build(self):
        apply_conandata_patches(self)
        autotools = Autotools(self)
        autotools.configure()
        autotools.make(args=["-j1"])
        if self._has_upstream_check_target():
            autotools.make(target="check")

    def package(self):
        autotools = Autotools(self)
        autotools.install()

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
