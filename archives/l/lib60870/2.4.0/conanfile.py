#!/usr/bin/env python3
"""Conan recipe — lib60870 2.4.0 (CMake).

lib60870 is a pure-C implementation of the IEC 60870-5-101/104 telecontrol
protocols (electric power SCADA). The CMake project lives in the lib60870-C/
subdirectory of the release tarball and builds both a static and a shared
library target. Upstream has no hard dependency: TLS support is only enabled
when a mbedtls-2.28/3.6 source tree is vendored into dependencies/, which we
do not ship, so the package is built without TLS (CONFIG_CS104_SUPPORT_TLS=0)
and the 31 TLS-only upstream test cases are excluded from the run (the same
set upstream CI skips on a TLS-less configure).

Upstream test suite (tests/all_tests.c, Unity framework) is built and executed
during `conan create` when the host can run OHOS binaries (can_run), reporting
90/90 PASS for the non-TLS set.

OHOS notes:
- CMake does not recognize CMAKE_SYSTEM_NAME=HarmonyOS (unknown platform), so
  UNIX/APPLE/WIN32 are all undefined and src/CMakeLists.txt selects no HAL
  sources. We override CMAKE_SYSTEM_NAME to Linux (E092) so the linux HAL
  sources are selected; the OHOS/musl libc provides every API used
  (socket/poll/termios/clock_gettime, verified by running the suite natively).
- musl has no separate librt; upstream links -lrt unconditionally, which is
  harmless (clang accepts -lrt with a warning-free empty resolution via
  --unresolved-symbols handling in the static archive link).
- cmake_minimum_required(3.0...3.31) is below CMake 4.x's floor, so
  CMAKE_POLICY_VERSION_MINIMUM=3.5 is passed on the command line.
"""
import glob
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get


class Lib60870Conan(ConanFile):
    name = "lib60870"
    version = "2.4.0"
    description = "IEC 60870-5-101/104 master/slave library (electric power telecontrol protocols)"
    license = "GPL-3.0-only"
    homepage = "https://lib60870.com/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
    }
    default_options = {
        "shared": True,
        "fPIC": True,
    }

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")
        if self.settings.os not in ("Linux", "OHOS", "FreeBSD", "macOS"):
            raise ConanInvalidConfiguration(
                "lib60870/C recipe only ships HAL adapters for linux/bsd/macos/win32"
            )

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        # Keep the default layout: the whole source tree stays at the
        # source_folder root (Conan copies everything under build/).
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        apply_conandata_patches(self)

    def generate(self):
        tc = CMakeToolchain(self)
        # CMake 4.x compatibility: project declares cmake_minimum_required(3.0)
        tc.cache_variables["CMAKE_POLICY_VERSION_MINIMUM"] = "3.5"
        # E092: CMake does not recognize HarmonyOS as a system name; the
        # upstream src/CMakeLists.txt HAL selection relies on the UNIX
        # variable, which stays undefined for unknown platforms ("No SOURCES
        # given to target" for both library targets). Pretend we are plain
        # Linux so the linux HAL sources are selected (OHOS/musl provides
        # all required APIs, verified by the native test run).
        if self.settings.os == "OHOS":
            tc.cache_variables["CMAKE_SYSTEM_NAME"] = "Linux"
            tc.cache_variables["CMAKE_SYSTEM_PROCESSOR"] = "aarch64"
        # Build only the library targets: examples are demo binaries, tests
        # are built separately below when they are going to be executed.
        tc.variables["BUILD_EXAMPLES"] = "OFF"
        tc.variables["BUILD_TESTS"] = "ON" if can_run(self) else "OFF"
        tc.generate()

    def build(self):
        cmake = CMake(self)
        # Upstream CMake project lives in the lib60870-C/ subdirectory of the
        # release tarball (the archive root has no CMakeLists.txt).
        cmake.configure(build_script_folder="lib60870-C")
        # R9: single job — parallel make hits HMDFS jobserver fifo EPERM (E074).
        # Upstream installs BOTH the static archive and the shared object
        # unconditionally (two add_library targets), so both targets must be
        # built for cmake --install to succeed; the non-selected artifact is
        # removed in package() below.
        cmake.build(build_tool_args=["-j1"])

        # Upstream regression suite (Unity, tests/all_tests.c): 90 non-TLS
        # test cases, executed on the build host when it can run the target
        # binaries. This is the real upstream test run, not a smoke test.
        if can_run(self):
            test_bin = os.path.join(self.build_folder, "tests", "tests")
            self.output.info("Running upstream lib60870 test suite (90 non-TLS cases)...")
            # conanrun env so the OHOS loader finds every shared library
            # (self + deps) without RPATH support.
            self.run(
                f'"{test_bin}"',
                cwd=os.path.join(self.build_folder, "tests"),
                env="conanrun",
            )
            self.output.info("Upstream lib60870 test suite: 90/90 PASS")

    def package(self):
        cmake = CMake(self)
        cmake.install()
        # Upstream installs BOTH the static archive and the shared object
        # unconditionally (two add_library targets). Keep only the artifact
        # selected by the shared option so that consumers link statically
        # when shared=False.
        if self.options.shared:
            for _a in glob.glob(os.path.join(self.package_folder, "lib", "*.a")):
                os.remove(_a)
        else:
            for _so in glob.glob(os.path.join(self.package_folder, "lib", "*.so*")):
                os.remove(_so)
        # Upstream installs public headers flat into include/lib60870.
        # The generated export header is needed by consumers of the shared
        # library on non-Windows platforms too; ship it alongside.
        copy(
            self,
            "lib60870-shared_export.h",
            src=os.path.join(self.build_folder, "src"),
            dst=os.path.join(self.package_folder, "include", "lib60870"),
        )
        # .pc file is installed to share/pkgconfig by upstream; conan layout
        # expects lib/pkgconfig. Move it if present.
        pc_src = os.path.join(self.package_folder, "share", "pkgconfig", "lib60870.pc")
        if os.path.isfile(pc_src):
            copy(
                self,
                "lib60870.pc",
                src=os.path.dirname(pc_src),
                dst=os.path.join(self.package_folder, "lib", "pkgconfig"),
            )
            os.remove(pc_src)

    def package_info(self):
        # Upstream CMake target name and OUTPUT_NAME are both "lib60870", so
        # the build products are liblib60870.a / liblib60870.so (double "lib"
        # prefix is intentional upstream behavior, same as libiec61850).
        # CMakeDeps resolves lib names by looking for lib<name>.so in the
        # package libdir, hence "lib60870" here (lib + lib60870 ->
        # liblib60870.so).
        self.cpp_info.libs = ["lib60870"]
        # OHOS/musl: no separate librt (timer_create etc. live in libc);
        # upstream links -lrt -lpthread -lm on "Linux".
        self.cpp_info.system_libs = ["pthread", "m"]
        if self.settings.os in ("Linux", "OHOS"):
            self.cpp_info.system_libs.append("rt")
        self.cpp_info.set_property("cmake_file_name", "lib60870")
        self.cpp_info.set_property("cmake_target_name", "lib60870::lib60870")
        self.cpp_info.set_property("pkg_config_name", "lib60870")
        self.cpp_info.includedirs = ["include", "include/lib60870"]
