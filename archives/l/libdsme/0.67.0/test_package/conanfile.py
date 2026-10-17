#!/usr/bin/env python3
"""Installed-package tests for libdsme 0.67.0.

Runs the consumer binary (test.c) built against the installed package and,
on OHOS, verifies the target artifact contract of all three installed
libraries: ELF64 AArch64 DYN objects with the upstream SONAMEs, bare
DT_NEEDED entries (including the musl libc, and GLib for libdsme.so.0), no
DT_RPATH/DT_RUNPATH entries, and the exported dsmesock/dsmemsg/dsme entry
points.
"""

import os
import shutil
import subprocess

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout


LIBRARIES = (
    "libdsme.so.0",
    "libdsme_dbus_if.so.0",
    "libthermalmanager_dbus_if.so.0",
)
EXPORTED_SYMBOLS = (
    "dsmesock_connect",
    "dsmesock_init",
    "dsmesock_receive",
    "dsmesock_send",
    "dsmesock_send_with_extra",
    "dsmesock_broadcast",
    "dsmesock_close",
    "dsmesock_getucred",
    "dsmemsg_new",
    "dsmemsg_id",
    "dsmemsg_name",
    "dsme_snooze_timeout_in_seconds",
)


class LibdsmeTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    test_type = "explicit"
    exports_sources = "CMakeLists.txt", "test.c"

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
            raise ConanException("libdsme target consumers are not runnable")
        dependency = self.dependencies["libdsme"]
        if str(self.settings.os) == "OHOS":
            self._check_ohos_libraries(dependency)
        executable = os.path.join(self.cpp.build.bindir, "libdsme_consumer")
        if not os.path.isfile(executable):
            raise ConanException(f"consumer binary was not built: {executable}")
        self.run(f'"{executable}"', env="conanrun")

    # ------------------------------------------------------------------
    # HarmonyOS-specific artifact contract
    # ------------------------------------------------------------------

    def _check_ohos_libraries(self, dependency):
        readelf = self._readelf()
        for soname in LIBRARIES:
            library = self._locate_library(dependency, soname)
            header = self._readelf_output(readelf, ["-h", library])
            self._require(self._field(header, "Class:") == "ELF64",
                          f"{soname} is not an ELF64 object")
            self._require(self._field(header, "Machine:") == "AArch64",
                          f"{soname} is not an AArch64 object")
            self._require(self._field(header, "Type:").startswith("DYN"),
                          f"{soname} is not a shared object")
            sonames, needed, search_paths = self._dynamic_entries(readelf, library)
            self._require(sonames == [soname],
                          f"{soname} has unexpected SONAME entries: {sonames}")
            if soname == "libdsme.so.0":
                # Only the dsmesock library calls into libc/GLib; the two
                # D-Bus interface modules export data and legitimately have
                # no DT_NEEDED entries at all.
                self._require("libc.so" in needed,
                              f"{soname} does not declare the musl libc dependency: {needed}")
            for entry in needed:
                self._require(bool(entry) and "/" not in entry
                              and not entry.startswith("."),
                              f"{soname} has a path-like NEEDED entry: {entry}")
            self._require(not search_paths,
                          f"{soname} embeds host RPATH/RUNPATH entries: {search_paths}")

        dsme = self._locate_library(dependency, "libdsme.so.0")
        _, needed, _ = self._dynamic_entries(readelf, dsme)
        self._require("libglib-2.0.so.0" in needed,
                      f"libdsme.so.0 is not linked against GLib: {needed}")
        symbols = self._readelf_output(readelf, ["--dyn-syms", dsme])
        for symbol in EXPORTED_SYMBOLS:
            self._require(self._defines_symbol(symbols, symbol),
                          f"libdsme.so.0 does not export {symbol}")

    # ------------------------------------------------------------------
    # helpers
    # ------------------------------------------------------------------

    def _locate_library(self, dependency, filename):
        for libdir in dependency.cpp_info.libdirs:
            candidate = os.path.join(libdir, filename)
            if os.path.isfile(candidate):
                return candidate
        raise ConanException(f"installed libdsme package does not provide {filename}")

    @staticmethod
    def _readelf():
        for candidate in (
            shutil.which("llvm-readelf"),
            shutil.which("readelf"),
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
