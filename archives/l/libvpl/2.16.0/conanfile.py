#!/usr/bin/env python3
"""Conan recipe — libvpl 2.16.0 (Intel Video Processing Library, oneVPL dispatcher).

Upstream project: CMake, MIT.  The dispatcher is a portable C++ library that
loads oneVPL / legacy MSDK runtime implementations at run time (dlopen) and
forwards the complete MFX* API to the selected runtime.

HarmonyOS adaptation notes
--------------------------
* ``libvpl/CMakeLists.txt`` guards the complete Linux dispatcher
  (``src/linux/mfxloader.cpp`` — MFXInit / MFXInitEx / MFXQueryVersion and the
  rest of the 1.x API — plus ``MFX_MODULES_DIR`` and the Threads lookup) behind
  ``if(UNIX)``.  CMake ships no ``Platform/HarmonyOS.cmake`` and on this device
  ``uname -s`` reports ``HarmonyOS``: leaving the system name to Conan's
  default (``HarmonyOS``, from ``os=OHOS``) or to native detection leaves
  ``UNIX`` undefined, so ``mfxloader.cpp`` never enters the build graph and the
  resulting ``libvpl.so`` exports only the seven 2.x loader entry points
  (MFXLoad / MFXCreateConfig / ...) instead of 59 symbols — the whole 1.x API
  disappears without a single compile or link error.  ``DT_SONAME`` is lost as
  well, because ``CMAKE_SHARED_LIBRARY_SONAME_<LANG>_FLAG`` is defined by
  ``Platform/Linux.cmake``.  Two things are *not* affected and must not be
  blamed on ``if(UNIX)``: the ``-Wl,--version-script`` link flag sits in the
  ``else()`` branch of ``if(WIN32)`` (it still applies; it merely ends up
  versioning only the seven surviving symbols), and the ``${CMAKE_DL_LIBS}``
  linkage is unconditional (``CMAKE_DL_LIBS`` falls back to
  ``Platform/GNU.cmake``, so ``-ldl`` is still passed).  The recipe selects the
  canonical platform name explicitly (``CMAKE_SYSTEM_NAME=OHOS``): the SDK
  ships ``Modules/Platform/OHOS.cmake``, which includes ``Platform/Linux``, so
  ``UNIX`` is set, the full dispatcher is compiled, ``DT_SONAME`` is emitted
  and the version script covers the whole API.  Same reasoning as
  archives/d/demumble and archives/d/dbus; no source patch is required.
* ``MFX_MODULES_DIR``, compiled into the dispatcher as the legacy MSDK runtime
  search directory, defaults to ``CMAKE_INSTALL_FULL_LIBDIR`` = ``<pkg>/lib``.
* No other platform branch is needed: the sources build unmodified with the
  OHOS SDK clang for aarch64.

Upstream tests
--------------
``libvpl/test/`` ships a self-contained GTest suite (googletest is vendored
under ``libvpl/test/ext/googletest``, nothing is downloaded at configure time)
plus three in-tree stub runtimes (``stub``, ``stub1x``, ``stub-nofn``) that let
the dispatcher be exercised end to end.  ``BUILD_TESTS=ON`` + ``ctest`` is the
upstream entry point (``script/test unit``); the suite is built and run in
``build()`` below.  The default run needs no Intel GPU: 707 of the 1014
executable tests pass against the stub runtime, 307 GPU / CPU-runtime /
legacy-accelerator tests skip because OHOS ships no Intel runtime, and 9
further cases are upstream ``DISABLED_``.
"""

import json
import os
import re
import subprocess

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get

required_conan_version = ">=2.0"

# OHOS SDK location used to resolve libc++_shared.so for the in-tree test
# binaries and stub runtimes (same convention as archives/c/cpu_features).
_OHOS_SDK_NATIVE = "/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native"


def _first_int(text, pattern, default=0):
    match = re.search(pattern, text)
    return int(match.group(1)) if match else default


class LibvplConan(ConanFile):
    name = "libvpl"
    version = "2.16.0"
    description = "Intel Video Processing Library (oneVPL) dispatcher"
    license = "MIT"
    homepage = "https://github.com/intel/libvpl"
    url = "https://github.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    topics = ("video", "media", "dispatcher", "onevpl", "intel")

    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"

    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": True, "fPIC": True}

    def config_options(self):
        if self.settings.os == "Windows":
            del self.options.fPIC

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def export_sources(self):
        export_conandata_patches(self)

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "libvpl is supported only on Linux/OHOS")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        if self.settings.os == "OHOS":
            # CMake ships no Platform/HarmonyOS.cmake, so leaving the system
            # name at Conan's default ("HarmonyOS") or letting CMake detect the
            # host ("HarmonyOS") leaves UNIX undefined and upstream drops the
            # whole Linux dispatcher (see the module docstring).  The SDK ships
            # Modules/Platform/OHOS.cmake (it includes Platform/Linux), so the
            # canonical platform name is selected explicitly.  On Linux the
            # host default is already the right one, so nothing is overridden.
            tc.variables["CMAKE_SYSTEM_NAME"] = "OHOS"
            tc.variables["CMAKE_SYSTEM_PROCESSOR"] = (
                "aarch64" if str(self.settings.arch) == "armv8"
                else str(self.settings.arch))
        tc.variables["CMAKE_INSTALL_LIBDIR"] = "lib"
        tc.variables["CMAKE_INSTALL_BINDIR"] = "bin"
        tc.variables["BUILD_SHARED_LIBS"] = bool(self.options.shared)
        # Upstream test suite (vendored googletest + in-tree stub runtimes).
        tc.variables["BUILD_TESTS"] = "ON"
        tc.variables["INSTALL_DEV"] = "ON"
        tc.variables["INSTALL_LIB"] = "ON"
        # Examples need real Intel hardware and are not packaged.
        tc.variables["INSTALL_EXAMPLES"] = "OFF"
        tc.variables["BUILD_EXAMPLES"] = "OFF"
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        # Bound the compile parallelism explicitly: Conan's default is
        # os.cpu_count() (20 here) while the container affinity is 8 and the
        # device MemFree is around 1 GB, so an unconstrained `conan create`
        # oversubscribes the shared machine. 2 jobs keeps the peak RSS well
        # inside the free memory; the same cap is used by the CI build.
        cmake.build(cli_args=["--parallel", "2"], build_tool_args=["-j2"])
        self._run_upstream_tests()

    def _runtime_env(self, build_dir):
        """Environment for the in-tree test binaries and stub runtimes."""
        env = dict(os.environ)
        sdk_native = os.environ.get("OHOS_SDK_NATIVE", _OHOS_SDK_NATIVE)
        sdk_lib = os.path.join(sdk_native, "llvm", "lib", "aarch64-linux-ohos")
        if not os.path.isdir(sdk_lib):
            sdk_lib = os.path.join(sdk_native, "llvm", "lib")
        parts = [build_dir]
        if os.path.isdir(sdk_lib):
            parts.append(sdk_lib)
        if env.get("LD_LIBRARY_PATH"):
            parts.append(env["LD_LIBRARY_PATH"])
        env["LD_LIBRARY_PATH"] = os.pathsep.join(parts)
        # The dispatcher resolves stub runtimes from this directory.
        env["ONEVPL_SEARCH_PATH"] = build_dir
        return env

    def _run_upstream_tests(self):
        """Run the upstream CTest suite and report the exact tally.

        Two runs are made on purpose:
          1. ``ctest`` — the upstream entry point (``script/test unit``), whose
             exit code is the hard gate;
          2. the single-process ``vpl-tests`` binary — the only source that
             separates PASSED from SKIPPED (CTest folds skipped tests into
             "passed").
        ``ctest -N`` provides the framework-registered total, which is larger
        than the literal ``TEST``/``TEST_F`` macro count because
        ``legacycpp-session-test.cpp`` is compiled twice (LEGACY_TEST_VER 1/2)
        and ``dispatcher_stub_propquery.cpp`` expands generator macros.
        """
        build_dir = self.build_folder
        env = self._runtime_env(build_dir)

        listing = subprocess.run(["ctest", "-N"], cwd=build_dir, env=env,
                                 capture_output=True, text=True, timeout=600)
        registered = _first_int(listing.stdout, r"Total Tests:\s*(\d+)")

        proc = subprocess.run(["ctest", "--output-on-failure", "-j", "2"],
                              cwd=build_dir, env=env, capture_output=True,
                              text=True, timeout=3600)
        tail = "\n".join(((proc.stdout or "") + (proc.stderr or "")).splitlines()[-15:])
        self.output.info("ctest (upstream script/test unit): exit=%d\n%s"
                         % (proc.returncode, tail))

        exe = os.path.join(build_dir, "vpl-tests")
        if not os.path.isfile(exe):
            raise ConanException("upstream test binary not found: %s" % exe)
        direct = subprocess.run([exe], cwd=build_dir, env=env,
                                capture_output=True, text=True, timeout=3600)
        text = (direct.stdout or "") + (direct.stderr or "")
        ran = _first_int(text, r"\[==========\] (\d+) tests from")
        passed = _first_int(text, r"\[  PASSED  \] (\d+) tests")
        skipped = _first_int(text, r"\[  SKIPPED \] (\d+) tests")
        failed = _first_int(text, r"\[  FAILED  \] (\d+) tests", direct.returncode)
        disabled = max(registered - ran, 0)

        marker = {
            "status": "passed" if failed == 0 and passed > 0 and proc.returncode == 0
                      else "failed",
            "framework": "gtest/ctest",
            "command": "ctest --output-on-failure -j 2",
            "source_declared_total": 860,
            "framework_registered_total": registered,
            "executed": ran,
            "passed": passed,
            "failed": failed,
            "skipped": skipped,
            "disabled_not_run": disabled,
            "note": ("registered=ctest -N (gtest_discover_tests enumeration); "
                     "source TEST/TEST_F literals=860, delta 163 from "
                     "legacycpp-session-test.cpp compiled twice (1x/2x) and the "
                     "TEST_PROPQUERY_* generator macros; 307 skips need an "
                     "Intel GPU/CPU runtime or vpl-inspect, absent on OHOS"),
        }
        self.output.info("HMBS_UPSTREAM_TEST_RESULT="
                         + json.dumps(marker, ensure_ascii=False))

        if proc.returncode != 0 or failed != 0 or passed == 0:
            raise ConanException(
                "upstream test suite failed (ctest exit=%d, gtest failed=%d, "
                "passed=%d)" % (proc.returncode, failed, passed))

    def package(self):
        cmake = CMake(self)
        cmake.install()
        copy(self, "LICENSE", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))
        copy(self, "third-party-programs.txt", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.libs = ["vpl"]
        self.cpp_info.set_property("cmake_file_name", "VPL")
        self.cpp_info.set_property("cmake_target_name", "VPL::dispatcher")
        self.cpp_info.set_property("pkg_config_name", "vpl")
        if self.settings.os in ("Linux", "OHOS"):
            # required when loading legacy MSDK runtimes (dlopen + pthread)
            self.cpp_info.system_libs = ["dl", "pthread"]
