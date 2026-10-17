import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class ZhAutoconvertTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain"
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
        # Run the freshly-built test_hz directly. On OHOS the kernel execs the
        # ELF natively; wrapping it in an explicit /data/service/hnp/bin/bash
        # interpreter actually fails with "cannot execute binary file" (126),
        # so we let Conan's shell run the binary path directly. The conanrun
        # env provides the packaged libhz via LD_LIBRARY_PATH if built shared.
        binpath = os.path.join(self.cpp.build.bindirs[0], "test_hz")
        self.run(binpath, env="conanrun")
