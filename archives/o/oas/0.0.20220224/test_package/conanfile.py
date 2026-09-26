import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class OasTestConan(ConanFile):
    """test_package for oas -- links liboas and runs four oas_address_score()
    assertions (NULL argument yields the no-match sentinel; a sockaddr_in6 yields
    the sentinel or a positive rule number; two calls on the same address agree;
    dlsym on the installed liboas.so resolves the exported oas_address_score),
    executing the binary through bash (OHOS: /system/bin/sh cannot exec ELF
    binaries). The connect() interposer is not exercised by this test_package;
    the gap is disclosed in notes.md section 3."""

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
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        self.run(bash + " test.sh", env="conanrun")
