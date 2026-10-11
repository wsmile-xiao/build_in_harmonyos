#!/usr/bin/env python3
"""Conan recipe for indi-fishcamp 1.1 — INDI Starfish CCD driver.

indi-fishcamp is an INDI driver for the Fishcamp Engineering Starfish CMOS
autoguiding camera. It talks to the camera over USB via libfishcamp (the
vendor USB protocol library) and publishes exposure, gain, cooler state and
camera info as INDI properties; a simulation mode emulates the camera without
hardware.

Adaptation notes (see manifest.yaml for the full record):

  * E092 — CMake does not know the HarmonyOS platform, so CMAKE_SYSTEM_NAME is
    forced to Linux and CMAKE_SYSTEM_PROCESSOR is pinned to aarch64 (same
    workaround proven for libindi/2.2.2.1 and indi-gpsnmea in this repo).
  * CMAKE_FIND_PACKAGE_PREFER_CONFIG=OFF — Conan's CMakeToolchain defaults to
    ON, which shadows the Find*.cmake modules vendored in
    indi-fishcamp/cmake_modules/ (FindINDI / FindFISHCAMP / FindCFITSIO) and
    would make CMake hunt for upstream INDI/FISHCAMP/CFITSIO CONFIG packages
    that do not exist for OHOS.
  * FindINDI.cmake version-detection regex is backported from upstream
    indi-3rdparty master (patch 0001, byte-identical to the indi-gpsnmea 0001
    patch): INDI >= 2.0 writes `#define INDI_VERSION "2.2.2"` with quotes,
    which the 1.1-era regex cannot match, so find_package(INDI REQUIRED)
    aborts with "failed to detect INDI version".
  * The Starfish driver targets the INDI 1.x C-struct API. Patch 0002 ports
    the base-class member TemperatureNP (a class in INDI 2.x) to the
    setState/apply/getState/operator[]/getValue/setValue API and registers the
    capture format the INDI 2.x CCD base class requires — line-for-line
    identical to the upstream official v2.2.4 port of this driver. The
    driver's own members (GainNP/CoolerNP/CamInfoTP) are still C structs in
    2.2 and keep .s/.value unchanged.
  * Patch 0003: C++17 (INDI 2.x base-class headers use std::any), libusb-1.0
    on the link line (libfishcamp.a is built against libusb; the 1.1 tree has
    no FindUSB1 wiring for this driver), and INDI_DATA_DIR redirected to this
    package's share/indi (the vendored FindINDI reports the libindi package's
    data dir, which would install the device xml into the wrong package).

The only executable artifact is bin/indi_fishcamp_ccd (the driver) plus the
device descriptor share/indi/indi_fishcamp.xml. The driver links
libindidriver/libindiAlignmentDriver (libindi/2.2.2.1), libfishcamp.a,
libcfitsio.a, libusb-1.0.so, zlib and libm.
"""
import os
import textwrap

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.cmake.toolchain.blocks import Block
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get


class PreferConfigOffBlock(Block):
    """Force CMAKE_FIND_PACKAGE_PREFER_CONFIG=OFF so the vendored FindINDI /
    FindFISHCAMP / FindCFITSIO modules win over non-existent upstream CONFIG
    packages (the block runs last, overriding the toolchain's default ON)."""
    template = textwrap.dedent("""\
        set(CMAKE_FIND_PACKAGE_PREFER_CONFIG OFF)
    """)


class IndiFishcampConan(ConanFile):
    name = "indi-fishcamp"
    version = "1.1"
    description = "INDI Starfish CCD driver — Fishcamp Starfish CMOS autoguider camera over USB (libfishcamp)"
    license = "LGPL-2.1-or-later"
    homepage = "https://github.com/indilib/indi-3rdparty"
    url = "https://github.com/indilib/indi-3rdparty"
    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    exports_sources = "patches/*"

    # R32: only Linux-family targets are supported.
    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"indi-fishcamp is only supported on Linux/OHOS, not {self.settings.os}")

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # Real build-time and runtime dependencies, per upstream CMakeLists.txt:
        # find_package(INDI REQUIRED) / find_package(FISHCAMP REQUIRED) /
        # find_package(CFITSIO REQUIRED) / find_package(ZLIB REQUIRED); libusb
        # is the runtime dependency of libfishcamp.a (patch 0003 adds it to the
        # link line).
        self.requires("libindi/2.2.2.1")
        self.requires("libfishcamp/1.2")
        self.requires("cfitsio/4.6.4")
        self.requires("zlib/1.3.1.1")
        self.requires("libusb/1.0.27")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        # E092: CMake has no HarmonyOS platform; drive the Linux path instead.
        tc.variables["CMAKE_SYSTEM_NAME"] = "Linux"
        tc.variables["CMAKE_SYSTEM_PROCESSOR"] = "aarch64"

        # fishcamp_common.h (pulled in by fishcamp.h, compiled into the driver)
        # includes <libusb.h> with the bare name, so the leaf directory that
        # holds libusb.h itself must be on the search path. The libusb package
        # keeps it in include/libusb-1.0/, i.e. includedirs[0] is the leaf.
        # No embedded quotes: Conan wraps this value in a CMake quoted string,
        # so inner quotes would terminate it early and CMake would drop the
        # flag (same pattern as the libnova include-root fix in indi-gpsnmea).
        usb_inc = self.dependencies["libusb"].cpp_info.includedirs[0]
        tc.extra_cflags.append(f"-I{usb_inc}")
        tc.extra_cxxflags.append(f"-I{usb_inc}")

        # Make the vendored Find*.cmake modules win over CONFIG lookups.
        tc.blocks["prefer_config_off"] = PreferConfigOffBlock
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        # Upstream CMakeLists.txt declares cmake_minimum_required(VERSION 3.0)
        # and CMake >= 4.0 removed compatibility with anything below 3.5. It
        # MUST be passed as a real -D cache variable (see indi-gpsnmea
        # conanfile for why tc.variables is not enough here).
        cmake.configure(cli_args=["-DCMAKE_POLICY_VERSION_MINIMUM=3.5"])
        # R9: conservative parallelism; tools.build:jobs can raise it.
        jobs = self.conf.get("tools.build:jobs", default=2)
        cmake.build(cli_args=[f"-j{jobs}"])

    def package(self):
        cmake = CMake(self)
        cmake.install()
        # The Debian orig tarball ships no LICENSE file (the driver headers
        # declare GPLv2.1+; nothing to copy).

    def package_info(self):
        # Application package: the only artifacts are the driver executable and
        # the INDI device descriptor.
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.resdirs = ["share"]
