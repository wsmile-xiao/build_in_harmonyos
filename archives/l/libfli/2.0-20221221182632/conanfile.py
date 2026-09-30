#!/usr/bin/env python3
"""Conan recipe for libfli 2.0-20221221182632 — Finger Lakes Instrument (FLI)
camera / filter-wheel control library, shipped as a subproject of the INDI
3rdparty monorepo.

Adaptation notes (see notes.md for the full record):

  * E092 — CMake does not know the HarmonyOS platform, so CMAKE_SYSTEM_NAME is
    forced to Linux (same workaround already proven for libindi/2.2.2.1 in this
    repo). CMAKE_SYSTEM_PROCESSOR is pinned to aarch64 so the toolchain shim
    and the CMake test compiler agree on the target triple.
  * CMAKE_FIND_PACKAGE_PREFER_CONFIG=OFF — Conan's CMakeToolchain sets this to
    ON by default, which shadows the Find*.cmake modules vendored in
    libfli/cmake_modules/ (FindUSB1.cmake / FindINDI.cmake) and would make CMake
    hunt for upstream libusb-1.0/INDI CONFIG packages that do not exist for OHOS.
    Same block as libindi/2.2.2.1.
  * libusb include path — unix/libusb/libfli-usb-sys.c includes
    <libusb-1.0/libusb.h> (prefixed with the API-version directory), while
    FindUSB1.cmake only reports the parent include dir via USB1_INCLUDE_DIRS,
    which the upstream CMakeLists.txt never adds to the include path (upstream
    relies on the system /usr/include). The Conan libusb package keeps the same
    libusb-1.0/ layout, so the include root has to be injected explicitly or the
    build dies with "'libusb-1.0/libusb.h' file not found".
  * UDEVRULES_INSTALL_DIR is redirected into the package folder: the upstream
    default is the absolute path /lib/udev/rules.d, which is not writable in the
    CI sandbox. The 99-fli.rules file is still installed, just under the private
    prefix (R49 — never write into a shared system prefix).
  * FindINDI.cmake version-detection regex is backported from upstream
    indi-3rdparty master (patch 0001). INDI >= 2.0 writes
    `#define INDI_VERSION "2.2.2"` with quotes, which the 2022-era regex in this
    snapshot cannot match, so find_package(INDI REQUIRED) aborted with
    "failed to detect INDI version". The backport is byte-identical to what
    upstream master now ships, uses no platform macro, and is not OHOS-specific.

libfli itself needs INDI only for its headers (indimacros.h, included by
libfli.c / libfli-camera-usb.c) — it never links an INDI library. INDI is still
declared as a requirement so downstream consumers get a consistent include path.
"""
import os
import textwrap

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.cmake.toolchain.blocks import Block
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get


class PreferConfigOffBlock(Block):
    """Force CMAKE_FIND_PACKAGE_PREFER_CONFIG=OFF so the vendored FindUSB1 /
    FindINDI modules win over non-existent upstream CONFIG packages (the block
    runs last, overriding the toolchain's default ON)."""
    template = textwrap.dedent("""\
        set(CMAKE_FIND_PACKAGE_PREFER_CONFIG OFF)
    """)


class LibfliConan(ConanFile):
    name = "libfli"
    version = "2.0-20221221182632"
    description = "Finger Lakes Instrument (FLI) camera and filter wheel control library (INDI 3rdparty)"
    license = "BSD-3-Clause"
    homepage = "https://github.com/indilib/indi-3rdparty"
    url = "https://github.com/indilib/indi-3rdparty"
    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    # R26: default static. The shared build links libusb-1.0 dynamically, which
    # is what upstream does, but a static libfli.a keeps consumers free of an
    # implicit shared-object dependency; shared=True still produces the real
    # libfli.so.2 with the upstream VERSION/SOVERSION properties.
    default_options = {"shared": False}

    exports_sources = "patches/*"

    # R32: only Linux-family targets are supported.
    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"libfli is only supported on Linux/OHOS, not {self.settings.os}")

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # Real build-time and runtime dependencies, per upstream CMakeLists.txt:
        # find_package(USB1 REQUIRED) / find_package(INDI REQUIRED).
        self.requires("libusb/1.0.27")
        self.requires("libindi/2.2.2.1")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        # E092: CMake has no HarmonyOS platform; drive the Linux path instead.
        tc.variables["CMAKE_SYSTEM_NAME"] = "Linux"
        tc.variables["CMAKE_SYSTEM_PROCESSOR"] = "aarch64"
        tc.variables["BUILD_SHARED_LIBS"] = "ON" if self.options.shared else "OFF"
        # CMAKE_POSITION_INDEPENDENT_CODE=ON — the default package is a static
        # libfli.a, and on HarmonyOS/OpenHarmony a static library is almost
        # always absorbed into a downstream shared object. Without PIC the
        # archive is unusable for that: linking it with
        #   clang -shared -Wl,--whole-archive libfli.a -Wl,--no-whole-archive
        # aborts with
        #   ld.lld: error: relocation R_AARCH64_ADR_PREL_PG_HI21 cannot be used
        #   against symbol 'devices'; recompile with -fPIC
        # (reproduced on the packaged artifact before this flag was added; see
        # notes.md "制品缺陷：libfli.a 非 PIC"). CMake leaves
        # POSITION_INDEPENDENT_CODE off for static targets by default, so this
        # has to be requested explicitly. Costs only a few KB of .a size.
        tc.variables["CMAKE_POSITION_INDEPENDENT_CODE"] = "ON"

        # unix/libusb/libfli-usb-sys.c includes <libusb-1.0/libusb.h>; upstream
        # gets that from the system /usr/include and never wires USB1_INCLUDE_DIRS
        # into the include path. The Conan libusb package keeps the same
        # include/libusb-1.0/libusb.h layout, and the toolchain only adds the
        # leaf directory (include/libusb-1.0) to CMAKE_INCLUDE_PATH — which does
        # not satisfy the version-prefixed include. Inject the include ROOT
        # (the directory that contains the libusb-1.0/ subdirectory) instead.
        usb_inc = self.dependencies["libusb"].cpp_info.includedirs[0]
        if os.path.basename(usb_inc) == "libusb-1.0":
            usb_inc = os.path.dirname(usb_inc)
        # No embedded quotes: Conan wraps this value in a CMake quoted string, so
        # inner quotes would terminate it early and CMake would drop the flag.
        tc.extra_cflags.append(f"-I{usb_inc}")

        # Upstream default is the absolute /lib/udev/rules.d — not writable in the
        # CI sandbox. Keep installing 99-fli.rules, but inside the private prefix.
        tc.variables["UDEVRULES_INSTALL_DIR"] = "lib/udev/rules.d"

        # Make the vendored Find*.cmake modules win over CONFIG lookups.
        tc.blocks["prefer_config_off"] = PreferConfigOffBlock
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        # Upstream CMakeLists.txt declares cmake_minimum_required(VERSION 3.0) and
        # CMake >= 4.0 removed compatibility with anything below 3.5, aborting with
        # "Compatibility with CMake < 3.5 has been removed from CMake" before any
        # project logic runs. It is a plain CMake-version issue, not an OHOS one
        # (it reproduces on any host with CMake >= 4).
        #
        # It MUST be passed as a real -D cache variable, exactly as CMake's own
        # error message suggests. Setting it through tc.variables is NOT enough:
        # CMakeToolchain writes those into conan_toolchain.cmake, which CMake
        # evaluates in its internal "system" scope while loading the toolchain
        # file; a normal variable set there does not survive into the project
        # directory scope, so cmake_minimum_required() still sees no value and
        # aborts (observed on CI #63837). Command-line -D creates a cache entry,
        # which does survive.
        cmake.configure(cli_args=["-DCMAKE_POLICY_VERSION_MINIMUM=3.5"])
        # R9: conservative parallelism; tools.build:jobs can raise it.
        jobs = self.conf.get("tools.build:jobs", default=2)
        cmake.build(cli_args=[f"-j{jobs}"])

    def package(self):
        cmake = CMake(self)
        cmake.install()
        copy(self, "LICENSE.BSD", self.source_folder,
             os.path.join(self.package_folder, "licenses"), keep_path=False)

    def package_info(self):
        # Upstream target name is "fli"; the built artifact is libfli.so.2 /
        # libfli.a, so the Conan lib name is "fli".
        self.cpp_info.libs = ["fli"]
        self.cpp_info.system_libs = ["m", "pthread"]
        # libfli is pure C but the upstream CMakeLists declares the project as
        # CXX as well, so the C++ driver objects (none today) would need the OHOS
        # libc++ runtime; keep it linked for the OHOS target to stay future-proof.
        if str(self.settings.os) == "OHOS":
            self.cpp_info.system_libs.extend(["c++", "c++abi"])
        self.cpp_info.set_property("cmake_file_name", "libfli")
        self.cpp_info.set_property("cmake_target_name", "libfli::libfli")
        # Both are transitive requirements for consumers. Referencing them in the
        # repo-standard form makes CMakeDeps propagate the conan-provided
        # libusb-1.0 / libindi imported targets to the consumer's build.
        self.cpp_info.requires = ["libusb::libusb", "libindi::libindi"]
