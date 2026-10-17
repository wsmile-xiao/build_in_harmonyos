#!/usr/bin/env python3
"""Conan test_package for mapcode 2.5.7.

Two layers of verification, both executed for real:

1. ``test_mapcode`` — a C consumer that links ``mapcode::mapcode`` and asserts
   the behaviour of the installed library API (encode / decode / territory
   lookup / accuracy bounds).
2. ``mapcode`` — the packaged command line tool, driven through a real
   encode + decode round trip on the OpenHarmony target.
"""
import os
import platform
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import cross_building
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout

_NATIVE_MACHINES = ("aarch64", "arm64")

# Reference coordinate: Amsterdam, used for both the library and the CLI checks.
_REF_LAT = 52.3702
_REF_LON = 4.8952
_TOLERANCE = 0.05


class MapcodeTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def _emulation_needed(self):
        """True when the test binaries cannot run on this build machine.

        `cross_building()` reports False for this project because the OHOS
        profile is supplied as both -pr:h and -pr:b, so Conan sees identical
        host and build settings. The build machine CPU is the reliable signal.
        """
        return cross_building(self) or platform.machine().lower() not in _NATIVE_MACHINES

    def _run_target(self, command, **kwargs):
        if self._emulation_needed():
            qemu = shutil.which("qemu-aarch64")
            if not qemu:
                raise ConanInvalidConfiguration(
                    "qemu-aarch64 is required to execute OpenHarmony binaries on this host"
                )
            command = f'"{qemu}" {command}'
        self.run(command, **kwargs)

    def generate(self):
        tc = CMakeToolchain(self)
        if self.settings.os == "OHOS":
            # Link the consumer test statically: the OpenHarmony sysroot only
            # ships a static libm, and a static binary runs under qemu-user
            # without a device root filesystem.
            tc.extra_exelinkflags.append("-static")
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        # 1. Library API consumer test.
        api_test = os.path.join(self.cpp.build.bindirs[0], "test_mapcode")
        self._run_target(f'"{api_test}"', env="conanrun")

        # 2. Command line tool: encode a coordinate, then decode it back.
        # In a test_package, self.package_folder points at the test package, so
        # the dependency's own package folder has to be resolved explicitly.
        dependency = self.dependencies[self.tested_reference_str]
        cli = os.path.join(dependency.package_folder,
                           dependency.cpp_info.bindirs[0], "mapcode")
        if not os.path.isfile(cli):
            raise ConanInvalidConfiguration(f"packaged command not found: {cli}")

        encoded = os.path.join(self.build_folder, "cli_encode.txt")
        self._run_target(
            f'"{cli}" -e {_REF_LAT} {_REF_LON} NLD > "{encoded}"', env="conanrun"
        )
        with open(encoded, encoding="utf-8") as handle:
            candidates = [line.strip() for line in handle if line.strip()]
        if not candidates:
            raise ConanInvalidConfiguration("mapcode -e produced no output")
        if not all(item.startswith("NLD ") for item in candidates):
            raise ConanInvalidConfiguration(
                f"mapcode -e returned an unexpected territory prefix: {candidates}"
            )
        proper = candidates[0].split(" ", 1)[1]

        decoded = os.path.join(self.build_folder, "cli_decode.txt")
        self._run_target(f'"{cli}" -d NLD {proper} > "{decoded}"', env="conanrun")
        with open(decoded, encoding="utf-8") as handle:
            coordinates = handle.read().split()
        if len(coordinates) < 2:
            raise ConanInvalidConfiguration(
                f"mapcode -d returned no coordinate: {coordinates}"
            )
        lat = float(coordinates[0])
        lon = float(coordinates[1])
        if abs(lat - _REF_LAT) > _TOLERANCE or abs(lon - _REF_LON) > _TOLERANCE:
            raise ConanInvalidConfiguration(
                f"mapcode round trip drifted too far: {lat} {lon}"
            )
        print(f"mapcode CLI round trip OK: {candidates[0]} -> {lat} {lon}")
