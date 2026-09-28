#!/usr/bin/env python3
"""test_package for WMmp 0.12.6 (HarmonyOS consumer test).

WMmp is an executable (no exported headers or libraries), so the consumer
use-case test compiles a small driver (wmmp_consumer.c) that executes the
packaged ``WMmp`` binary through its real command-line entry points:

  * ``WMmp -v`` prints "WMmp version ..." and exits 0
  * ``WMmp -h`` prints "Usage : ..." and exits 0

Both paths are reached through parse_arguments() *before* the dockapp tries
to open an X display, so they are deterministic without a running X server
while still proving that the OHOS ELF loads (dynamic linking against
libX11/libXext/libXpm resolves) and runs on this platform.

On OHOS the packaged executable must carry a .codesign section before it can
be executed; the copy is signed in place with binary-sign-tool, mirroring the
CI-verified libxpm/3.5.17 pattern.
"""

import os
import shutil
import subprocess

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout


class WmmpTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    test_type = "explicit"
    exports_sources = "CMakeLists.txt", "wmmp_consumer.c"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.generate()
        CMakeDeps(self).generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        if not can_run(self):
            raise ConanException("wmmp target consumers are not runnable")

        wmmp_package = None
        for dep in self.dependencies.values():
            if dep.ref.name == "wmmp":
                wmmp_package = dep
                break
        if wmmp_package is None:
            raise ConanException("wmmp not found among test dependencies")

        packaged = os.path.join(wmmp_package.package_folder, "bin", "WMmp")
        if not os.path.isfile(packaged):
            raise ConanException(f"packaged WMmp binary missing: {packaged}")

        executable = os.path.join(self.cpp.build.bindir, "wmmp_consumer")
        if str(self.settings.os) == "OHOS":
            wmmp_bin = self._sign_ohos_elf(packaged)
        else:
            wmmp_bin = packaged
        # 被测二进制路径经内联环境变量传入消费者驱动（Conan 2 self.run 不接受 dict）
        self.run(f'WMMP_BIN="{wmmp_bin}" "{executable}"', env="conanrun")

    def _sign_ohos_elf(self, path):
        """Sign a copy of the packaged executable and return the signed path."""
        signed = os.path.join(self.build_folder, "WMmp.ohos-signed")
        shutil.copy2(path, signed)
        signer = shutil.which("binary-sign-tool") or (
            "/data/service/hnp/bin/binary-sign-tool"
        )
        readelf = shutil.which("llvm-readelf") or (
            "/data/service/hnp/bin/llvm-readelf"
        )
        if not os.path.isfile(signer) or not os.path.isfile(readelf):
            raise ConanException("required OHOS signing tools are missing")
        temporary = f"{signed}.tmp"
        subprocess.run(
            [
                signer,
                "sign",
                "-inFile",
                signed,
                "-outFile",
                temporary,
                "-selfSign",
                "1",
            ],
            check=True,
            timeout=60,
        )
        sections = subprocess.run(
            [readelf, "-SW", temporary],
            check=True,
            capture_output=True,
            text=True,
            timeout=30,
        ).stdout
        if sections.count(".codesign") != 1:
            raise ConanException(f"signed consumer has invalid .codesign: {signed}")
        os.chmod(temporary, (os.stat(signed).st_mode & 0o777) | 0o055)
        os.replace(temporary, signed)
        return signed
