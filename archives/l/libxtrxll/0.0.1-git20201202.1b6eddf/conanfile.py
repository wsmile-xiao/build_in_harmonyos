#!/usr/bin/env python3
"""Conan recipe for libxtrxll 0.0.1-git20201202.1b6eddf.

Upstream: myriadrf/libxtrxll (formerly xtrx-sdr/libxtrxll)
          commit 1b6eddfbedc700efb6f7e3c3594e43ac6ff29ea4 (2020-12-02)

Low-level XTRX hardware abstraction library: the user-space client that talks
to the XTRX SDR board through the FPGA PCIe core (or through a USB3380 bridge).

Build system: CMake.  The upstream tree ships hand-written CMakeLists.txt files
(there is no Autotools / Meson and no `configure`), so a plain CMake build is
used.  Two transport plugins live in sub-directories:

  * mod_pcie/      — PCIe transport   (opendir("/sys/class/xtrx/"), /dev/xtrx*)
  * mod_usb3380/   — USB3380 transport (needs the external libusb3380 package)

HarmonyOS (OHOS) adaptation is entirely recipe-level; **no source patch is
required** (R1 parameter minimisation / R8 "source modification: four don'ts"):

  * `cmake_minimum_required(VERSION 2.8)` in the top-level CMakeLists.txt is
    rejected by CMake >= 4 ("Compatibility with CMake < 3.5 has been
    removed").  `CMAKE_POLICY_VERSION_MINIMUM=3.5` is injected as a **cache**
    variable so it is present before the first `project()` call and re-read
    after `cmake_minimum_required()` (a plain variable would not survive into
    CMakeCache.txt and would not lift the floor).  Same approach as
    archives/a/airspyhf/1.6.8 and archives/a/airspy/1.0.10.

  * The transport plugins are compiled as STATIC libraries by default
    (`option(XTRXLL_STATIC ... ON)`) and archived into `libxtrxll.so`.  Upstream
    adds `-fPIC` to those static plugin targets only when
    `CMAKE_SYSTEM_NAME MATCHES "Linux"`; on HarmonyOS CMakeToolchain reports
    `CMAKE_SYSTEM_NAME=HarmonyOS`, so the plugin objects would be non-PIC and
    the link into the shared library would fail with
    "relocation R_AARCH64_... cannot be used against ...".
    `CMAKE_POSITION_INDEPENDENT_CODE=ON` fixes every target in the tree without
    touching the upstream sources.

  * USB3380 transport requires the external `libusb3380` package (a separate
    XTRX project).  It is absent both from this repository and from the OHOS
    Conan remote, so the optional plugin is disabled with `ENABLE_USB3380=OFF`.
    The PCIe transport and the full common low-level API (`xtrxll_open`,
    `xtrxll_discovery`, `xtrxll_set_param`, LMS7 SPI, DMA, MMCM, flash and the
    logging subsystem) are unaffected.
"""

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import (apply_conandata_patches, copy,
                               export_conandata_patches, get, rm)

import os


class LibxtrxllConan(ConanFile):
    name = "libxtrxll"
    version = "0.0.1-git20201202.1b6eddf"
    description = ("Low-level XTRX hardware abstraction library (XTRX SDR "
                   "project): user-space client for the XTRX PCIe/USB3380 "
                   "transports")
    license = "LGPL-2.1"
    homepage = "https://github.com/myriadrf/libxtrxll"
    url = "https://github.com/myriadrf/libxtrxll"

    package_type = "library"

    settings = "os", "arch", "compiler", "build_type"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
    }
    default_options = {
        # Upstream builds `add_library(xtrxll SHARED ...)` unconditionally.
        "shared": True,
        # HarmonyOS default; also required by the static plugin objects that are
        # archived into the shared library.
        "fPIC": True,
    }

    def config_options(self):
        if self.settings.os == "Windows":
            del self.options.fPIC

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def export_sources(self):
        # No patches are needed for this package (see conandata.yml), but the
        # standard export clause is kept so that conandata.yml-declared patches
        # are carried into the build when they are added in the future.
        export_conandata_patches(self)

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)

        # CMake 4.x: upstream declares cmake_minimum_required(VERSION 2.8),
        # which is below the removed-compatibility floor.  Must be a *cache*
        # variable so it is set before project() and re-read afterwards.
        tc.cache_variables["CMAKE_POLICY_VERSION_MINIMUM"] = "3.5"

        # E092: CMake ships no "HarmonyOS" platform module.  Conan maps
        # os=OHOS to CMAKE_SYSTEM_NAME=HarmonyOS, which CMake reports as
        # "System is unknown to cmake"; Platform/HarmonyOS.cmake is therefore
        # never loaded and CMAKE_SHARED_LIBRARY_SONAME_C_FLAG stays unset.
        # Consequence: libxtrxll.so is linked WITHOUT a DT_SONAME and the
        # upstream `set_target_properties(... VERSION ... SOVERSION ...)` is
        # ignored (no libxtrxll.so.0 / .so.0.0.1, no symlink chain), which the
        # CI L5a SONAME quality gate rejects.  Aliasing the system name to
        # Linux restores the full Unix/Linux platform semantics (same approach
        # as archives/a/airspyhf/1.6.8 and archives/a/airspy/1.0.10).
        if self.settings.os == "OHOS":
            tc.cache_variables["CMAKE_SYSTEM_NAME"] = "Linux"
            tc.cache_variables["CMAKE_SYSTEM_PROCESSOR"] = "aarch64"

        # The plugins are STATIC by default and are linked into libxtrxll.so.
        # With CMAKE_SYSTEM_NAME=Linux upstream adds -fPIC itself, but the
        # global switch is kept so the link is correct regardless of the
        # platform-detection branch that is taken.
        tc.variables["CMAKE_POSITION_INDEPENDENT_CODE"] = "ON"

        # libusb3380 is not available (not in this repository, not in the OHOS
        # Conan remote) -> disable the optional USB3380 transport plugin.
        tc.cache_variables["ENABLE_USB3380"] = "OFF"

        # Keep the "static plugin linkage" upstream default (XTRXLL_STATIC=ON):
        # the PCIe plugin is compiled into libxtrxll.so instead of being loaded
        # through dlopen("libxtrxll_pcie.so.0"), which avoids an RPATH-dependent
        # runtime lookup inside consumers.
        tc.cache_variables["XTRXLL_STATIC"] = "ON"
        tc.cache_variables["ENABLE_PCIE"] = "ON"

        if self.settings.os in ("Linux", "OHOS"):
            # Informational only; the upstream tree does not use LIB_SUFFIX.
            tc.cache_variables["LIB_SUFFIX"] = ""

        tc.generate()

    def build(self):
        apply_conandata_patches(self)  # no-op: this package carries no patches
        cmake = CMake(self)
        cmake.configure()
        cmake.build()
        # NOTE (R51): the two upstream programs under tests/ (test_xtrxll,
        # test_xtrxflash) are built by this step (add_subdirectory(tests) is
        # unconditional upstream).  They are NOT test runners: they are
        # getopt-driven interactive hardware tools with no assertions, they are
        # not registered with ctest (no enable_testing()/add_test() anywhere in
        # the tree) and they require a physical XTRX board (they open
        # /sys/class/xtrx/ and /dev/xtrx*).  Running them on a device-less
        # machine is meaningless, so they are not executed here; the census is
        # recorded in test_package/MANIFEST.yml and notes.md, and runnable
        # consumer-level assertions live in test_package/.

    def package(self):
        cmake = CMake(self)
        cmake.install()

        copy(self, "LICENSE", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))
        # Upstream's CMake install exports no .la files; drop any that a future
        # libtool-based build could add (repository-wide hygiene rule).
        for pattern in ("*.la", "*.dylib"):
            rm(self, pattern, os.path.join(self.package_folder, "lib"))

    def package_info(self):
        self.cpp_info.libs = ["xtrxll"]
        if self.settings.os in ("Linux", "OHOS"):
            # Upstream links SYSTEM_LIBS = rt dl pthread for Linux-like targets.
            # On OHOS (musl/bionic) these live in the base C library, so no
            # explicit system_libs entry is needed.
            pass
        # The upstream test utilities are installed into <lib>/xtrxll and are
        # deliberately NOT advertised as package tools: this is a library
        # package (R38), so no bindirs / commands.json.
