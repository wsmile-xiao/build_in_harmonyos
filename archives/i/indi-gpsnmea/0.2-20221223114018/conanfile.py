#!/usr/bin/env python3
"""Conan recipe for indi-gpsnmea 0.2-20221223114018 — INDI GPS NMEA driver.

indi-gpsnmea is an INDI driver that connects to a GPS receiver over TCP/IP
(default 192.168.1.1:50000) and parses NMEA 0183 sentences (RMC/GGA/GSA/ZDA)
with the minmea parser that the driver vendors in-tree (minmea.c/h, WTFPL).
It publishes GPS location (lat/lon/elevation), fix status and UTC time as INDI
properties, and can sync the system clock from the receiver time.

Adaptation notes (see manifest.yaml for the full record):

  * E092 — CMake does not know the HarmonyOS platform, so CMAKE_SYSTEM_NAME is
    forced to Linux and CMAKE_SYSTEM_PROCESSOR is pinned to aarch64 (same
    workaround proven for libindi/2.2.2.1 and libfli in this repo).
  * CMAKE_FIND_PACKAGE_PREFER_CONFIG=OFF — Conan's CMakeToolchain defaults to
    ON, which shadows the Find*.cmake modules vendored in
    indi-gpsnmea/cmake_modules/ (FindINDI.cmake / FindNova.cmake) and would
    make CMake hunt for upstream INDI/Nova CONFIG packages that do not exist
    for OHOS. Same block as libfli/2.0-20221221182632.
  * FindINDI.cmake version-detection regex is backported from upstream
    indi-3rdparty master (patch 0001, byte-identical to the libfli 0001
    patch): INDI >= 2.0 writes `#define INDI_VERSION "2.2.2"` with quotes,
    which the 2022-era regex in this snapshot cannot match, so
    find_package(INDI REQUIRED) aborts with "failed to detect INDI version".

The only executable artifact is bin/indi_gpsnmea (the driver). It links
libindidriver/libindiclient (from libindi/2.2.2.1), libnova (the driver
#include's <libnova/julian_day.h> and <libnova/sidereal_time.h>) and pthread.
The vendored minmea is compiled straight into the driver (upstream CMakeLists:
add_executable(indi_gpsnmea gpsnmea_driver.cpp minmea.c)).
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
    FindNova modules win over non-existent upstream CONFIG packages (the block
    runs last, overriding the toolchain's default ON)."""
    template = textwrap.dedent("""\
        set(CMAKE_FIND_PACKAGE_PREFER_CONFIG OFF)
    """)


class IndiGpsnmeaConan(ConanFile):
    name = "indi-gpsnmea"
    version = "0.2-20221223114018"
    description = "INDI GPS NMEA driver — TCP/IP NMEA 0183 GPS receiver (minmea parser)"
    license = "GPL-2.0-or-later"
    homepage = "https://github.com/indilib/indi-3rdparty"
    url = "https://github.com/indilib/indi-3rdparty"
    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    exports_sources = "patches/*"

    # R32: only Linux-family targets are supported.
    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"indi-gpsnmea is only supported on Linux/OHOS, not {self.settings.os}")

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # Real build-time and runtime dependencies, per upstream CMakeLists.txt:
        # find_package(INDI REQUIRED) / find_package(Nova REQUIRED) /
        # find_package(ZLIB REQUIRED).
        self.requires("libindi/2.2.2.1")
        self.requires("libnova/0.16")
        self.requires("zlib/1.3.1.1")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        # E092: CMake has no HarmonyOS platform; drive the Linux path instead.
        tc.variables["CMAKE_SYSTEM_NAME"] = "Linux"
        tc.variables["CMAKE_SYSTEM_PROCESSOR"] = "aarch64"

        # The vendored FindNova.cmake locates the libnova package but reports
        # NOVA_INCLUDE_DIR as the *leaf* directory (include/libnova), while the
        # driver includes headers with the libnova/ prefix (<libnova/julian_day.h>).
        # Upstream relies on a system libnova whose include root is on the default
        # search path; the Conan package keeps the same include/libnova/ layout,
        # so the include ROOT has to be injected explicitly (same pattern as the
        # libusb-1.0 include fix in libfli/2.0-20221221182632).
        nova_inc = self.dependencies["libnova"].cpp_info.includedirs[0]
        if os.path.basename(nova_inc) == "libnova":
            nova_inc = os.path.dirname(nova_inc)
        # No embedded quotes: Conan wraps this value in a CMake quoted string, so
        # inner quotes would terminate it early and CMake would drop the flag.
        tc.extra_cflags.append(f"-I{nova_inc}")
        tc.extra_cxxflags.append(f"-I{nova_inc}")

        # Make the vendored Find*.cmake modules win over CONFIG lookups.
        tc.blocks["prefer_config_off"] = PreferConfigOffBlock
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        # Upstream CMakeLists.txt declares cmake_minimum_required(VERSION 3.0)
        # and CMake >= 4.0 removed compatibility with anything below 3.5. It
        # MUST be passed as a real -D cache variable (see libfli conanfile for
        # why tc.variables is not enough here).
        cmake.configure(cli_args=["-DCMAKE_POLICY_VERSION_MINIMUM=3.5"])
        # R9: conservative parallelism; tools.build:jobs can raise it.
        jobs = self.conf.get("tools.build:jobs", default=2)
        cmake.build(cli_args=[f"-j{jobs}"])

    def package(self):
        cmake = CMake(self)
        cmake.install()
        # The Debian orig tarball ships no LICENSE file (the driver headers
        # declare GPLv2+; the vendored minmea is WTFPL) — nothing to copy.

    def package_info(self):
        # Application package: the only artifact is the driver executable.
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.resdirs = ["share"]
