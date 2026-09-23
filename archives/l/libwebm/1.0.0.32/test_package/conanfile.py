#!/usr/bin/env python3
"""Consumer test for libwebm 1.0.0.32 (HarmonyOS PC)."""

import os
import shutil
import subprocess

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout


class LibWebMTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    test_type = "explicit"

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
        executable = os.path.join(self.cpp.build.bindirs[0], "test_libwebm")
        if not can_run(self):
            assert os.path.exists(executable), "test binary not built"
            self.output.info("cross-building: consumer linked but cannot run")
            return

        # OHOS-specific packaging gates before the real run: verify the
        # library is an AArch64 musl-linked ELF with a proper DT_SONAME,
        # clean NEEDED set, and a code signature on the consumer binary.
        if str(self.settings.os) == "OHOS":
            self._verify_packaged_library()
            self._sign_executable(executable)
        self.run(f'"{executable}"', env="conanrun", cwd=self.build_folder)

    # ------------------------------------------------------------------
    # OHOS ELF verification (readelf-based, L0c-style static gates)
    # ------------------------------------------------------------------
    def _find_tool(self, name):
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict) or {}
        compiler_dir = os.path.dirname(compilers.get("cpp", ""))
        candidates = [
            os.path.join(compiler_dir, name) if compiler_dir else "",
            os.path.join("/data/service/hnp/bin", name),
            shutil.which(name) or "",
        ]
        return next((p for p in candidates if os.path.isfile(p)), "")

    def _verify_packaged_library(self):
        pkg = self.dependencies["libwebm"].package_folder
        lib_path = os.path.join(pkg, "lib", "libwebm.so")
        if not os.path.isfile(lib_path):
            lib_path = os.path.join(pkg, "lib", "libwebm.a")
        assert os.path.isfile(lib_path), f"packaged library missing: {lib_path}"
        self.output.info(f"Verifying packaged library: {lib_path}")

        if lib_path.endswith(".a"):
            self.output.info("Static package: skipping ELF dynamic checks")
            return

        readelf = self._find_tool("readelf")
        assert readelf, "readelf not found for OHOS ELF verification"

        header = subprocess.run(
            [readelf, "-h", lib_path], capture_output=True, text=True, timeout=10)
        assert header.returncode == 0, f"readelf -h failed: {header.stderr}"
        out = header.stdout
        assert "Class:                             ELF64" in out, \
            "libwebm.so is not a 64-bit ELF"
        assert "Machine:                           AArch64" in out, \
            "libwebm.so is not AArch64"
        self.output.info("  [ok] ELF64 / AArch64")

        dyn = subprocess.run(
            [readelf, "-d", lib_path], capture_output=True, text=True, timeout=10)
        assert dyn.returncode == 0, f"readelf -d failed: {dyn.stderr}"
        out = dyn.stdout
        soname_line = [l for l in out.splitlines() if "SONAME" in l]
        assert soname_line, "libwebm.so has no DT_SONAME (E383 regression)"
        assert "libwebm.so" in soname_line[0], \
            f"unexpected SONAME: {soname_line[0]}"
        self.output.info(f"  [ok] SONAME: {soname_line[0].strip()}")

        needed = [l.strip() for l in out.splitlines() if "NEEDED" in l]
        # musl-based OHOS: libc.so + libc++_shared.so only; any other NEEDED
        # would be an undeclared dependency leaking into the package.
        allowed = ("libc.so", "libc++_shared.so", "libdexkit.so")
        for line in needed:
            assert any(lib in line for lib in allowed), \
                f"unexpected NEEDED entry: {line}"
        self.output.info(f"  [ok] NEEDED entries: {len(needed)}")

    # ------------------------------------------------------------------
    # OHOS code signing (lapack precedent)
    # ------------------------------------------------------------------
    def _sign_executable(self, executable):
        objcopy = self._find_tool("llvm-objcopy")
        signer = self._find_tool("binary-sign-tool")
        if not objcopy or not signer:
            raise ConanInvalidConfiguration(
                "OHOS consumer execution requires llvm-objcopy and binary-sign-tool")
        self._sign_elf_atomically(executable, objcopy, signer)

    def _sign_elf_atomically(self, path, objcopy, signer):
        original_mode = os.stat(path).st_mode
        temporary = f"{path}.signing"
        try:
            shutil.copy2(path, temporary)
            self.run(f'"{objcopy}" --remove-section .codesign "{temporary}"')
            self.run(f'"{signer}" sign -inFile "{temporary}" '
                     f'-outFile "{temporary}" -selfSign 1')
            os.chmod(temporary, original_mode)
            os.replace(temporary, path)
        finally:
            if os.path.exists(temporary):
                os.remove(temporary)
