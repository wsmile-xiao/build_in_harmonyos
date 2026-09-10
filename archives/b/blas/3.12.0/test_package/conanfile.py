"""Conan consumer test for the packaged reference BLAS."""

import os
import shutil

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.env import VirtualRunEnv


class BlasTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        CMakeDeps(self).generate()
        CMakeToolchain(self).generate()
        VirtualRunEnv(self).generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        executable = os.path.join(
            self.cpp.build.bindirs[0],
            "test_blas" + (".exe" if str(self.settings.os) == "Windows" else ""),
        )
        if not can_run(self):
            if not os.path.isfile(executable):
                raise ConanException(
                    "consumer executable was not built: {}".format(executable)
                )
            self.output.warning("Cross-built consumer cannot run on the build host.")
            return
        if str(self.settings.os) == "OHOS":
            self._sign_executable(executable)
        self.run('"{}"'.format(executable), env="conanrun", cwd=self.build_folder)

    def _sign_executable(self, executable):
        objcopy = self._find_ohos_tool("llvm-objcopy")
        signer = self._find_ohos_tool("binary-sign-tool")
        if not objcopy or not signer:
            raise ConanInvalidConfiguration(
                "OHOS consumer execution requires llvm-objcopy and binary-sign-tool"
            )
        temporary = executable + ".signing"
        original_mode = os.stat(executable).st_mode
        try:
            shutil.copy2(executable, temporary)
            self.run('"{}" --remove-section .codesign "{}"'.format(objcopy, temporary))
            self.run(
                '"{}" sign -inFile "{}" -outFile "{}" -selfSign 1'.format(
                    signer, temporary, temporary
                )
            )
            os.chmod(temporary, original_mode)
            os.replace(temporary, executable)
        finally:
            if os.path.exists(temporary):
                os.remove(temporary)

    def _find_ohos_tool(self, name):
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ) or {}
        compiler_dir = os.path.dirname(compilers.get("cpp", ""))
        candidates = [
            os.path.join(compiler_dir, name) if compiler_dir else "",
            os.path.join("/data/service/hnp/bin", name),
            shutil.which(name) or "",
        ]
        return next((path for path in candidates if os.path.isfile(path)), "")
