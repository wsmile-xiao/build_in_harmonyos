#!/usr/bin/env python3
"""Installed-package tests for marco 1.26.2 (MATE window manager).

marco ships no automated test suite upstream: the release tarball has no
tests/ directory, its autotools build registers no TESTS/check_PROGRAMS, and
the only "test" sources (src/wm-tester/*.c, src/core/testboxes.c,
src/core/testasyncgetprop.c, src/ui/testgradient.c) are noinst interactive /
random demonstration programs (not an automated suite -- testboxes.c's
g_asserts are run-time self-checks of a random demo, not a CI suite).
The consumers here link the
published libmarco-private.so and drive it *without* an X server, which is what
the headless OHOS CI worker provides:

  * marco_api_surface        strong-typed relocation of every geometry helper
                             and GObject type constructor exported by
                             libmarco-private.so; GType names come from
                             dlsym(RTLD_DEFAULT, "g_type_name") so the test
                             needs no link-time glib dependency.
  * marco_geometry_contract  behavioural assertions on the pure rectangle
                             algebra (union/intersect/overlap/contains/...).
  * marco_no_display_guard   pins the "no X server -> degrade, do not crash"
                             contract for the GDK/X11 seam helpers.
  * run_marco_cli.sh         runs the packaged bin/marco --version/--help
                             (both exit before any X connection) and checks an
                             unknown option exits non-zero.
"""

import os
import shutil
import subprocess

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout


TEST_EXECUTABLES = (
    "marco_api_surface",
    "marco_geometry_contract",
    "marco_no_display_guard",
)


class MarcoTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    test_type = "explicit"
    exports_sources = "CMakeLists.txt", "*.c", "*.sh"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        # The marco recipe exports no cmake_file_name/cmake_target_name, so the
        # published libmarco-private.so is located by find_library/find_path in
        # CMakeLists.txt using this package folder.
        dep = self.dependencies["marco"]
        tc = CMakeToolchain(self)
        tc.variables["MARCO_PACKAGE_ROOT"] = dep.package_folder
        tc.generate()
        CMakeDeps(self).generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        if not can_run(self):
            raise ConanException("marco target consumers are not runnable")

        for name in TEST_EXECUTABLES:
            executable = os.path.join(self.cpp.build.bindir, name)
            if str(self.settings.os) == "OHOS":
                self._sign_ohos_elf(executable)
            self.run(f'"{executable}"', env="conanrun")

        dep = self.dependencies["marco"]
        marco_bin = os.path.join(dep.package_folder, "bin", "marco")
        pkg_libdir = self._existing_libdir(dep.package_folder)
        # CI injects SHELL=/bin/sh (HMBS [shell_getcwd]); never hardcode bash.
        shell = (
            os.environ.get("SHELL")
            or os.environ.get("CONFIG_SHELL")
            or shutil.which("bash")
            or "/bin/sh"
        )
        script = os.path.join(self.source_folder, "run_marco_cli.sh")
        self.run(f'"{shell}" "{script}" "{marco_bin}" "{pkg_libdir}"',
                 env="conanrun")

    @staticmethod
    def _existing_libdir(package_folder):
        for name in ("lib", "lib64"):
            candidate = os.path.join(package_folder, name)
            if os.path.isdir(candidate):
                return candidate
        return os.path.join(package_folder, "lib")

    def _sign_ohos_elf(self, path):
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
            [
                signer,
                "sign",
                "-inFile",
                path,
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
            raise ConanException(f"signed consumer has invalid .codesign: {path}")
        os.chmod(temporary, (os.stat(path).st_mode & 0o777) | 0o055)
        os.replace(temporary, path)
