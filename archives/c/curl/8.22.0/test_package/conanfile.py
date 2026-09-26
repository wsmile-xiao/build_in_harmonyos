import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class CurlTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain", "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        bash = "bash"
        if str(self.settings.os) == "OHOS":
            bash = self.conf.get("user.curl:bash", default="/data/service/hnp/bin/bash")
        bash = os.fspath(bash)
        self.run(f"{bash} -c './curl_test'", env="conanrun")
        self.run(f"{bash} -c 'curl --version'", env="conanrun")
