#!/usr/bin/env python3
"""Consumer test for the packaged xplc 0.3.13.

Two independent halves:
  * test_xplc  — C++ consumer linking xplc::xplc through CMakeDeps.  Proves the
                 versioned include/lib dirs, the UNSTABLE define and the
                 repaired SONAME all reach a real downstream build.
  * uuidgen    — the packaged CLI (bindirs) run for its output shape, so the
                 recipe is also exercised as a tool package (R38).
"""
import os
import re
import shutil

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, cmake_layout


class XplcTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "CMakeDeps", "CMakeToolchain", "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        # cmake_layout puts single-config binaries in build/<build_type>.
        bin_dir = self.cpp.build.bindirs[0]
        consumer = os.path.join(bin_dir, "test_xplc")
        assert os.path.isfile(consumer), "test_xplc was not built: %s" % consumer
        self.run(consumer, env="conanrun")

        # OHOS is the real-device runtime this profile targets; keep the tool
        # half alive when only the host profile is handed to `conan test`.
        if str(self.settings.os) == "OHOS" or can_run(self):
            pkg_folder = self.dependencies["xplc"].package_folder
            uuidgen = os.path.join(pkg_folder, "bin", "uuidgen")
            assert os.path.isfile(uuidgen), "uuidgen missing: %s" % uuidgen

            shell = (
                os.environ.get("CONFIG_SHELL")
                or shutil.which("sh")
                or "/bin/sh"
            )
            # R34: absolute path to the packaged tool, and assert on the shape
            # of what it prints instead of only its exit code.
            script = os.path.join(self.source_folder, "test_uuidgen.sh")
            self.run('"%s" "%s" "%s"' % (shell, script, uuidgen),
                     env="conanrun")
