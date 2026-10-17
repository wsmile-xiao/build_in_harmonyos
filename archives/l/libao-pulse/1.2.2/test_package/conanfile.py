#!/usr/bin/env python3
"""Installed-package tests for libao-pulse 1.2.2.

Upstream libao ships no automated test suite (the tarball has no
check_PROGRAMS / TESTS, and `make check` has nothing to run), so the coverage
of this package comes from this consumer:

  * ``CMakeLists.txt`` builds ``libao_pulse_consumer`` against the published
    package (``find_package(ao)`` / ``ao::ao``) with ``-Werror``;
  * ``test.sh`` asserts the installed layout, the ELF contract of
    ``libao.so`` and of the pulse plugin (including the ``.codesign`` section
    the OHOS loader requires), the plugin's ``DT_NEEDED`` PulseAudio ABI, and
    then runs the consumer so that libao has to dlopen the plugin and
    register the pulse driver.
"""

import os
import shutil
import subprocess

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout


class LibaoPulseTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    test_type = "explicit"
    exports_sources = "CMakeLists.txt", "*.c", "test.sh"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        CMakeDeps(self).generate()
        CMakeToolchain(self).generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        if not can_run(self):
            raise ConanException("libao-pulse consumers are not runnable")
        executable = os.path.join(self.cpp.build.bindir, "libao_pulse_consumer")
        if str(self.settings.os) == "OHOS":
            self._sign_ohos_elf(executable)
        package_folder = self.dependencies[self.tested_reference_str].package_folder
        shell = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        script = os.path.join(self.source_folder, "test.sh")
        self.run(f'"{shell}" "{script}" "{executable}" "{package_folder}"',
                 env="conanrun")

    def _sign_ohos_elf(self, path):
        """The OHOS loader refuses to map an unsigned object."""
        signer = shutil.which("binary-sign-tool") or (
            "/data/service/hnp/bin/binary-sign-tool"
        )
        readelf = shutil.which("llvm-readelf") or (
            "/data/service/hnp/bin/llvm-readelf"
        )
        if not os.path.isfile(signer) or not os.path.isfile(readelf):
            raise ConanException("required OHOS signing tools are missing")
        temporary = f"{path}.signed"
        subprocess.run(
            [signer, "sign", "-inFile", path, "-outFile", temporary,
             "-selfSign", "1"],
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
            raise ConanException(f"signed consumer has invalid .codesign: {path}")
        os.chmod(temporary, (os.stat(path).st_mode & 0o777) | 0o055)
        os.replace(temporary, path)