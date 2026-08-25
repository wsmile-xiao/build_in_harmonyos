import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class LibgfshareTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
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
        # Run the consumer binary directly so the test genuinely links
        # against the packaged libgfshare (R34: test must depend on the
        # package under test, not on the upstream source tree).
        cmd = os.path.join(self.cpp.build.bindirs[0], "test_libgfshare")
        self.run(cmd, env="conanrun")
