import glob
import os

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, cmake_layout
from conan.tools.env import Environment


class AtkTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "CMakeDeps", "CMakeToolchain", "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def build(self):
        with self._build_environment().vars(self).apply():
            cmake = CMake(self)
            cmake.configure()
            cmake.build()

    def _build_environment(self):
        environment = Environment()
        if self.settings.os == "OHOS":
            llvm_lib = self._sdk_llvm_lib_dir()
            if llvm_lib:
                environment.prepend_path("LD_LIBRARY_PATH", llvm_lib)
        return environment

    def _sdk_llvm_lib_dir(self):
        llvm_lib = "/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/llvm/lib"
        if os.path.isdir(llvm_lib):
            return llvm_lib
        candidates = sorted(glob.glob("/data/service/hnp/ohos-sdk.org/*/ohos/native/llvm/lib"))
        return candidates[0] if candidates else None

    def test(self):
        if not can_run(self):
            return
        suffix = ".exe" if str(self.settings.os) == "Windows" else ""
        executable = os.path.join(self.cpp.build.bindirs[0], "test_atk" + suffix)
        self.run(f'"{executable}"', env="conanrun", cwd=self.build_folder)
