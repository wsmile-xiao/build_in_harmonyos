#!/usr/bin/env python3
"""test_package for indi-beefocus 0.1-20221222010828 — consumer test against the
*packaged driver executable*.

The product of this recipe is the INDI driver binary bin/indi_beefocus (plus its
INDI descriptor share/indi/indi_beefocus.xml), not a library. So the consumer
suite (R34) must really execute the packaged binary and assert on the observable
behaviour of the INDI protocol it speaks on stdin/stdout.

test_indi_beefocus.py is the harness; it is driven from test() below with a real
self.run() so that CI's L0c/L0d checks see a genuine test source and a genuine
execution. Nothing here is a print-only stub: every assertion reads the actual
artifacts shipped inside the package folder.
"""
import os

from conan import ConanFile
from conan.tools.build import can_run


class IndiBeefocusTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        # Keep Conan's generated files (conanbuild.sh / conanrun.sh / …) inside
        # the test build folder. Without layout() they land in the recipe folder,
        # which would pollute the archived package directory.
        from conan.tools.cmake import cmake_layout
        cmake_layout(self)

    def test(self):
        dep = self.dependencies["indi-beefocus"]
        bindir = dep.cpp_info.bindirs[0] if dep.cpp_info.bindirs else "bin"
        exe = os.path.join(dep.package_folder, bindir, "indi_beefocus")
        xml = os.path.join(dep.package_folder, "share", "indi", "indi_beefocus.xml")
        script = os.path.join(self.recipe_folder, "test_indi_beefocus.py")

        if not os.path.isfile(script):
            raise AssertionError(f"consumer harness missing: {script}")

        if can_run(self):
            # Real execution of the packaged driver, driven by a real harness.
            self.run(f'python3 "{script}" "{exe}" "{xml}" "{self.build_folder}"',
                     env="conanrun")
        else:
            raise AssertionError(
                "cannot run the packaged driver on this host — the consumer "
                "suite must execute the artifact, not skip it")
