import glob
import os
import shutil

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.env import Environment


class WvTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        CMakeDeps(self).generate()
        CMakeToolchain(self).generate()
        if self.settings.os == "OHOS":
            env = Environment()
            for name, pattern in {
                "cmake": "/data/service/hnp/cmake.org/cmake_*/bin/cmake",
                "make": "/data/service/hnp/make.org/make_*/bin/make",
            }.items():
                executable = shutil.which(name)
                if not executable:
                    candidates = sorted(
                        glob.glob(pattern), reverse=True)
                    if candidates:
                        executable = candidates[0]
                if executable:
                    env.prepend_path("PATH", os.path.dirname(executable))
            sdk_llvm_libdirs = sorted(glob.glob(
                "/data/service/hnp/ohos-sdk.org/*/ohos/native/llvm/lib"),
                reverse=True)
            if sdk_llvm_libdirs:
                # lld itself depends on the SDK's libxml2 runtime.
                env.prepend_path(
                    "LD_LIBRARY_PATH", sdk_llvm_libdirs[0])
            env.vars(self).save_script("wv_test_tools")

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build(build_tool_args=["-j1"])

    def test(self):
        self.run("./wv_test", env="conanrun")
