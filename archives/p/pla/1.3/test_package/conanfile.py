#!/usr/bin/env python3
"""Conan test_package for pla 1.3.

pla is an application. This consumer-side test really executes the packaged
`pla` binary (R34) and asks it to render a real Gantt chart PNG through cairo.

Note about the runtime environment: on HarmonyOS HMDFS the dynamic loader can
not follow .so symlinks (knowledge E073), so the shared libraries that conanrun
places in LD_LIBRARY_PATH are staged as real-file copies by test.sh before the
binary is executed.  The test itself is fully self-contained and offline.
"""

from conan import ConanFile


class PlaTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    exports_sources = "test.sh"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        self.run("bash test.sh", env="conanrun")
