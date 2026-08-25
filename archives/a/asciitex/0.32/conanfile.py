#!/usr/bin/env python3
"""Conan recipe for asciitex 0.32 — ASCII equation renderer.

Converts LaTeX math expressions to ASCII art. Pure C, self-contained,
no external dependencies. CMake build system, C11 standard.

R32: OS check uses in ("Linux", "OHOS")
R33: Uses CMakeToolchain for compiler/flags — no hardcoded paths or shell vars
R34: test_package executes the asciitex binary
"""
import os
import glob
import shutil

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class AsciitexConan(ConanFile):
    name = "asciitex"
    version = "0.32"
    description = "ASCII equation renderer — converts LaTeX math to ASCII art"
    license = "GPL-2.0"
    homepage = "http://asciitex.sourceforge.net/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        # CMakeLists.txt uses cmake_minimum_required(VERSION 3.0) which
        # fails with CMake >= 4.0. Must be a cache variable so it appears
        # on the cmake command line (needed before cmake_minimum_required()).
        tc.cache_variables["CMAKE_POLICY_VERSION_MINIMUM"] = "3.5"
        # Disable upstream POST_BUILD commands that execute the binary during
        # build — OHOS requires ELF signing before execution. Tests are run
        # manually in build() after signing (see _run_upstream_tests).
        tc.cache_variables["DISABLE_TESTING"] = True
        # R32: On OHOS the default lld linker may have broken dependencies.
        # Fall back to GNU ld from PATH if available.
        if self.settings.os == "OHOS":
            ld_path = shutil.which("ld")
            if ld_path:
                tc.cache_variables["CMAKE_EXE_LINKER_FLAGS"] = f"-fuse-ld={ld_path}"
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        # R32: Support both Linux and OHOS
        if self.settings.os not in ("Linux", "OHOS"):
            raise Exception(f"Unsupported OS: {self.settings.os}")

        cmake = CMake(self)
        cmake.configure()
        cmake.build()

        # OHOS requires ELF signing before binary can be executed.
        # Sign the binary so upstream tests can run.
        binary = os.path.join(self.build_folder, "asciitex")
        sign_tool = os.environ.get("SIGN_TOOL") or shutil.which("binary-sign-tool")
        if sign_tool and os.path.exists(sign_tool) and os.path.exists(binary):
            self.run(f'"{sign_tool}" sign -inFile "{binary}" '
                     f'-outFile "{binary}" -selfSign 1')

        # Run upstream tests: for each examples/*.tex, run asciitex and
        # compare output with the expected examples/*.txt (R7: 安全弹窗).
        self._run_upstream_tests(binary)

    def _run_upstream_tests(self, binary):
        """Run the 17 upstream .tex → .txt comparison tests manually.

        The upstream CMakeLists.txt defines these as POST_BUILD commands +
        CTest tests, but POST_BUILD executes the binary during build which
        fails on OHOS (unsigned ELF). We run them here after signing.
        """
        examples_dir = os.path.join(self.source_folder, "examples")
        tex_files = sorted(glob.glob(os.path.join(examples_dir, "*.tex")))
        passed = 0
        failed = 0
        for tex_file in tex_files:
            expected_file = tex_file.replace(".tex", ".txt")
            if not os.path.exists(expected_file):
                continue
            name = os.path.basename(tex_file).replace(".tex", "")
            output_file = os.path.join(self.build_folder, f"{name}.txt")
            try:
                self.run(f'"{binary}" -f "{tex_file}" > "{output_file}"',
                         cwd=self.build_folder)
                with open(output_file, "r") as f:
                    actual = f.read()
                with open(expected_file, "r") as f:
                    expected = f.read()
                if actual == expected:
                    passed += 1
                    self.output.info(f"  Test {name}: PASS")
                else:
                    failed += 1
                    self.output.warning(f"  Test {name}: FAIL (output mismatch)")
            except Exception as e:
                failed += 1
                self.output.warning(f"  Test {name}: FAIL ({e})")
        total = passed + failed
        self.output.info(f"Upstream tests: {passed}/{total} passed")
        if failed > 0:
            raise Exception(f"Upstream tests failed: {failed}/{total}")

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
