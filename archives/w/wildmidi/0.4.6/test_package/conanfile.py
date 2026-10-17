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
        # Run the consumer binary directly on the OHOS device (build host ==
        # target device). conanrun env carries the runtime library paths.
        exe = os.path.join(self.cpp.build.bindirs[0], "test_wildmidi")
        self.run(exe, env="conanrun")
