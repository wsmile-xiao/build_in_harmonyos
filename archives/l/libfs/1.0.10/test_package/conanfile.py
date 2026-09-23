#!/usr/bin/env python3
"""Installed-package tests for libFS 1.0.10 (public API + OHOS artifact)."""

import os
import shutil
import subprocess

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout


TEST_EXECUTABLES = ("libfs_api_contract",)
SONAME = "libFS.so.6"
EXPORTED_SYMBOLS = ("FSOpenServer", "FSServerName", "FSMalloc", "FSFree")


class LibfsTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    test_type = "explicit"
    exports_sources = "CMakeLists.txt", "*.c"

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
            raise ConanException("libfs target consumers are not runnable")
        dependency = self.dependencies["libfs"]
        on_ohos = str(self.settings.os) == "OHOS"
        readelf = self._readelf() if on_ohos else None
        if on_ohos:
            if dependency.options.shared:
                self._check_ohos_shared_library(readelf, dependency)
            else:
                self._check_ohos_static_archive(readelf, dependency)
        for name in TEST_EXECUTABLES:
            executable = os.path.join(self.cpp.build.bindir, name)
            if not os.path.isfile(executable):
                raise ConanException(f"consumer binary was not built: {executable}")
            if on_ohos:
                self._check_ohos_executable(readelf, executable, name, dependency)
                self._sign_ohos_elf(readelf, executable)
            self.run(f'"{executable}"', env="conanrun")

    # ------------------------------------------------------------------
    # HarmonyOS-specific artifact contract
    # ------------------------------------------------------------------

    def _check_ohos_shared_library(self, readelf, dependency):
        library = self._locate_library(dependency, "libFS.so")
        header = self._readelf_output(readelf, ["-h", library])
        self._require(self._field(header, "Class:") == "ELF64",
                      f"{library} is not an ELF64 object")
        self._require(self._field(header, "Machine:") == "AArch64",
                      f"{library} is not an AArch64 object")
        self._require(self._field(header, "Type:").startswith("DYN"),
                      f"{library} is not a shared object")
        sonames, needed, search_paths = self._dynamic_entries(readelf, library)
        self._require(sonames == [SONAME],
                      f"{library} has unexpected SONAME entries: {sonames}")
        self._require("libc.so" in needed,
                      f"{library} does not declare the musl libc dependency: {needed}")
        for entry in needed:
            self._require(bool(entry) and "/" not in entry and not entry.startswith("."),
                          f"{library} has a path-like NEEDED entry: {entry}")
        self._require(not search_paths,
                      f"{library} embeds host RPATH/RUNPATH entries: {search_paths}")
        symbols = self._readelf_output(readelf, ["--dyn-syms", library])
        for symbol in EXPORTED_SYMBOLS:
            self._require(self._defines_symbol(symbols, symbol),
                          f"{library} does not export {symbol}")

    def _check_ohos_static_archive(self, readelf, dependency):
        archive = self._locate_library(dependency, "libFS.a")
        header = self._readelf_output(readelf, ["-h", archive])
        classes = [line for line in header.splitlines() if "Class:" in line]
        machines = [line for line in header.splitlines() if "Machine:" in line]
        self._require(bool(classes) and all("ELF64" in line for line in classes),
                      "libFS.a has members that are not ELF64")
        self._require(bool(machines) and all("AArch64" in line for line in machines),
                      "libFS.a has members that are not AArch64")
        symbols = self._readelf_output(readelf, ["-s", archive])
        for symbol in EXPORTED_SYMBOLS:
            self._require(self._defines_symbol(symbols, symbol),
                          f"libFS.a does not define {symbol}")

    def _check_ohos_executable(self, readelf, executable, name, dependency):
        header = self._readelf_output(readelf, ["-h", executable])
        self._require(self._field(header, "Class:") == "ELF64",
                      f"{name} is not an ELF64 executable")
        self._require(self._field(header, "Machine:") == "AArch64",
                      f"{name} is not an AArch64 executable")
        if dependency.options.shared:
            _, needed, _ = self._dynamic_entries(readelf, executable)
            self._require(SONAME in needed,
                          f"{name} is not dynamically linked against {SONAME}: {needed}")

    def _sign_ohos_elf(self, readelf, path):
        signer = shutil.which("binary-sign-tool") or (
            "/data/service/hnp/bin/binary-sign-tool"
        )
        if not os.path.isfile(signer):
            raise ConanException("required OHOS signing tool is missing")
        temporary = f"{path}.signed"
        subprocess.run(
            [signer, "sign", "-inFile", path, "-outFile", temporary, "-selfSign", "1"],
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

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _locate_library(self, dependency, filename):
        for libdir in dependency.cpp_info.libdirs:
            candidate = os.path.join(libdir, filename)
            if os.path.isfile(candidate):
                return candidate
        raise ConanException(f"installed libfs package does not provide {filename}")

    @staticmethod
    def _readelf():
        for candidate in (
            shutil.which("llvm-readelf"),
            shutil.which("readelf"),
            "/data/service/hnp/bin/llvm-readelf",
        ):
            if candidate and os.path.isfile(candidate):
                return candidate
        raise ConanException("no readelf tool is available for the ELF checks")

    @staticmethod
    def _readelf_output(readelf, arguments):
        return subprocess.run(
            [readelf, *arguments],
            check=True,
            capture_output=True,
            text=True,
            timeout=60,
        ).stdout

    def _dynamic_entries(self, readelf, path):
        output = self._readelf_output(readelf, ["-d", path])
        sonames, needed, search_paths = [], [], []
        for line in output.splitlines():
            if "(SONAME)" in line:
                sonames.append(self._bracket_value(line))
            elif "(NEEDED)" in line:
                needed.append(self._bracket_value(line))
            elif "(RPATH)" in line or "(RUNPATH)" in line:
                search_paths.append(self._bracket_value(line))
        return sonames, needed, search_paths

    @staticmethod
    def _bracket_value(line):
        start = line.find("[")
        end = line.find("]", start)
        if start < 0 or end < 0:
            return None
        return line[start + 1:end]

    @staticmethod
    def _field(output, label):
        for line in output.splitlines():
            stripped = line.strip()
            if stripped.startswith(label):
                return stripped[len(label):].strip()
        return None

    @staticmethod
    def _defines_symbol(symbols, name):
        for line in symbols.splitlines():
            tokens = line.split()
            if name in tokens and "UND" not in tokens:
                return True
        return False

    @staticmethod
    def _require(condition, message):
        if not condition:
            raise ConanException(message)
