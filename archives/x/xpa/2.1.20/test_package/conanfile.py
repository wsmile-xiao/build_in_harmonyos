import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class XpaTestConan(ConanFile):
    """test_package for xpa library — compiles a consumer program against
    the packaged libxpa/headers, then runs it under bash (OHOS mksh may
    refuse to exec ELF directly)."""
    settings = "os", "arch", "compiler", "build_type"
    generators = "CMakeToolchain", "CMakeDeps", "VirtualRunEnv"
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
        # test() runs with an unspecified CWD (not this source folder), so
        # point at test.sh via this conanfile's absolute path, and hand the
        # dependency's bin dir over explicitly — PATH lookup via the run
        # env is a nice-to-have, not a dependency of this test.
        dep = self.dependencies[self.tested_reference_str]
        bin_dir = os.path.join(dep.package_folder, "bin")
        assert os.path.isdir(bin_dir), f"xpa bin dir not found: {bin_dir}"
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        test_sh = os.path.join(os.path.dirname(os.path.abspath(__file__)), "test.sh")
        self.run(f'"{bash}" "{test_sh}" "{bin_dir}"', env="conanrun")
