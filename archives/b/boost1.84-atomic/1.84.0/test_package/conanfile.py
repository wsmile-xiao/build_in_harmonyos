#!/usr/bin/env python3
"""Consumer test for boost1.84-atomic (L1 smoke test).

Runs the packaged boost headers + libboost_atomic.a static library through a
CMake consumer (find_package boost1.84-atomic COMPONENTS atomic), then executes
the built binary on the OHOS build host:
- LD_LIBRARY_PATH points at the SDK libc++_shared.so directory (located via
  `clang++ -print-file-name=libc++_shared.so`, no hardcoded SDK version);
- OHOS executables are signed (llvm-objcopy --remove-section .codesign +
  binary-sign-tool self-sign), same as boost 1.90.0.2.1 / 1.85.0 precedent.
"""
import os
import shutil
import subprocess

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.env import VirtualRunEnv


class BoostAtomicTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        CMakeDeps(self).generate()
        VirtualRunEnv(self).generate()
        CMakeToolchain(self).generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        if not can_run(self):
            self.output.warning("Cross-built consumer cannot run on the build host.")
            return

        suffix = ".exe" if str(self.settings.os) == "Windows" else ""
        executable = os.path.join(
            self.cpp.build.bindirs[0], "test_boost1_84_atomic" + suffix
        )
        if self.settings.os == "OHOS":
            self._sign_executable(executable)
            libcxx_dir = self._find_libcxx_dir()
            command = 'LD_LIBRARY_PATH="{}:${{LD_LIBRARY_PATH:-}}" "{}"'.format(
                libcxx_dir, executable
            )
            self.run(command, env="conanrun", cwd=self.build_folder)
            return

        self.run(f'"{executable}"', env="conanrun", cwd=self.build_folder)

    def _find_libcxx_dir(self):
        """Locate the SDK libc++_shared.so directory via compiler introspection."""
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ) or {}
        cxx = compilers.get("cpp", "clang++")
        try:
            out = subprocess.check_output(
                [cxx, "-print-file-name=libc++_shared.so"], text=True
            ).strip()
        except Exception as exc:
            raise ConanInvalidConfiguration(
                "failed to locate libc++_shared.so via {}: {}".format(cxx, exc)
            )
        if not out or out == "libc++_shared.so":
            raise ConanInvalidConfiguration(
                "clang could not locate libc++_shared.so"
            )
        return os.path.dirname(out)

    def _sign_executable(self, executable):
        objcopy = self._find_ohos_tool("llvm-objcopy")
        signer = self._find_ohos_tool("binary-sign-tool")
        if not objcopy or not signer:
            raise ConanInvalidConfiguration(
                "OHOS consumer execution requires llvm-objcopy and binary-sign-tool"
            )
        self._sign_elf_atomically(executable, objcopy, signer)

    def _sign_elf_atomically(self, path, objcopy, signer):
        original_mode = os.stat(path).st_mode
        temporary = f"{path}.signing"
        try:
            shutil.copy2(path, temporary)
            self.run(f'"{objcopy}" --remove-section .codesign "{temporary}"')
            self.run(
                f'"{signer}" sign -inFile "{temporary}" '
                f'-outFile "{temporary}" -selfSign 1'
            )
            os.chmod(temporary, original_mode)
            os.replace(temporary, path)
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
