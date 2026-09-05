#!/usr/bin/env python3
"""Conan test_package — paps 0.8.0 (application: run the 'paps' binary).

R34: the test actually executes the paps converter end to end — it feeds
the upstream multilingual sample (examples/small-hello.utf8) through the
real pango/cairo/fmt pipeline and verifies the PostScript/PDF/SVG output
content. Not a print-only shell.

The binary is executed via /data/service/hnp/bin/bash because the OHOS
default /system/bin/sh (mksh) cannot exec ELF binaries with a DT_RUNPATH
resolving to HMDFS-mounted package folders.
"""
import os

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import cross_building


class PapsTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        if cross_building(self):
            self.output.warning("paps: cross-building - skipping runtime test of the target binary")
            return

        dep = self.dependencies["paps"]
        bin_dir = os.path.join(dep.package_folder, dep.cpp_info.bindirs[0])
        paps = os.path.join(bin_dir, "paps")
        if not os.path.isfile(paps):
            raise ConanException("paps: binary not found in package: %s" % paps)

        work = os.path.join(self.build_folder, "paps-test-work")
        os.makedirs(work, exist_ok=True)
        script = os.path.join(self.source_folder, "test_paps.sh")

        # OHOS: /system/bin/sh (mksh) cannot exec ELF; wrap with bash.
        bash = os.environ.get("CONFIG_SHELL") or "/data/service/hnp/bin/bash"

        # paps is self-contained ($ORIGIN/../lib DT_RUNPATH); no extra
        # LD_LIBRARY_PATH setup is needed when patchelf is available. When
        # patchelf was missing at package time, fall back to the conanrun
        # environment (runenv_info LD_LIBRARY_PATH covers <pkg>/lib).
        env = "conanrun"
        self.run('"%s" "%s" "%s" "%s"' % (bash, script, paps, work), env=env)
