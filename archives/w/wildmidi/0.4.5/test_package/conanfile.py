import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class WildmidiTestConan(ConanFile):
    """Consumer test: compile a real program against wildmidi and run it."""
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
        # OHOS: /system/bin/sh (mksh) may not execute ELF binaries reliably.
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        self.run(f"{bash} -c './test_wildmidi'", env="conanrun")
