#!/usr/bin/env python3
"""open62541 1.5.7 — OPC UA stack (CMake) for HarmonyOS aarch64.

Upstream: https://github.com/open62541/open62541 (tag v1.5.7, MPL-2.0).

The recipe builds the official CMake project with the upstream unit test
suite enabled (UA_BUILD_UNIT_TESTS=ON) so that `conan create` builds the
library and runs the full upstream `ctest` suite in the build phase.  No
source patches; the OHOS adaptation is purely at the toolchain /
dependency-wiring level (see generate()):

* CMake has no OHOS/HarmonyOS platform module.  The OHOS sysroot uses the
  POSIX/Linux layout (usr/include, usr/lib/aarch64-linux-ohos) and the
  clang driver already defaults to the aarch64-unknown-linux-ohos target
  with the OHOS sysroot, so the Linux platform module is a faithful
  mapping (same approach as the other OHOS CMake packages in this repo).
* The build-time test dependencies (Check framework, libpcap for the
  network-replay tests) are build-context tool_requires.  Their
  include/lib paths are injected explicitly because the OHOS pkg-config
  data (.pc files) is not trustworthy and the bare `-lpcap` / `-lsubunit`
  link items are not resolvable from the OHOS sysroot.
"""
import glob
import os
import shutil

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.env import Environment
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches


class Open62541Conan(ConanFile):
    name = "open62541"
    version = "1.5.7"
    description = "OPC UA stack - open source C implementation (MPL-2.0)"
    license = "MPL-2.0"
    homepage = "https://open62541.org"
    url = "https://github.com/open62541/open62541"
    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def build_requirements(self):
        # tests/CMakeLists.txt resolves the Check framework via
        # tools/cmake/FindCheck.cmake (pkg-config first, FIND_PATH /
        # FIND_LIBRARY fallback).
        self.tool_requires("check/0.15.2")
        # testing_networklayers_pcap.c + tests/network_replay are enabled
        # by upstream for CMAKE_SYSTEM_NAME=Linux 64-bit and link bare
        # `-lpcap` (offline pcap replay only, no live capture).
        self.tool_requires("libpcap/1.10.6")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        toolchain = CMakeToolchain(self)
        # CMake has no OHOS/HarmonyOS platform module; map to the Linux
        # platform module (see module docstring).
        if self.settings.os in ("Linux", "OHOS"):
            toolchain.cache_variables["CMAKE_SYSTEM_NAME"] = "Linux"
            toolchain.cache_variables["CMAKE_SYSTEM_PROCESSOR"] = (
                "aarch64" if str(self.settings.arch) == "armv8" else str(self.settings.arch)
            )
        # Build the upstream unit test suite and run it (ctest) in build().
        toolchain.variables["UA_BUILD_UNIT_TESTS"] = True
        # Keep the default no-encryption / no-tools / no-examples variant.
        toolchain.variables["UA_ENABLE_ENCRYPTION"] = False
        toolchain.variables["UA_BUILD_EXAMPLES"] = False
        toolchain.variables["UA_BUILD_TOOLS"] = False

        check = self.dependencies.build["check"]
        pcap = self.dependencies.build["libpcap"]
        check_info = check.cpp_info.aggregated_components()
        pcap_info = pcap.cpp_info.aggregated_components()
        check_inc = str(check_info.includedir)
        check_lib = str(check_info.libdir)
        pcap_inc = str(pcap_info.includedir)
        pcap_lib = str(pcap_info.libdir)

        # The test suite links `subunit` (LIBS in tests/CMakeLists.txt) but
        # never references a subunit_* symbol (the check suites are driven
        # by srunner/ck_run_tests), so an empty archive satisfies the link
        # line where libsubunit is absent from the OHOS sysroot.
        stub_dir = os.path.join(self.generators_folder, "subunit-stub")
        os.makedirs(stub_dir, exist_ok=True)
        # ar magic, zero members: a valid empty archive.
        with open(os.path.join(stub_dir, "libsubunit.a"), "wb") as f:
            f.write(b"!<arch>\n")

        # OHOS adaptation wiring:
        # - _UAPI_LINUX_SOCKET_H: the OHOS sysroot defines sockaddr_storage
        #   in both sys/socket.h and the kernel linux/socket.h (which has
        #   no cross-guard); pre-defining the kernel guard makes the
        #   kernel copy a no-op for every translation unit.
        # - check.h / pcap.h are #included directly by test plugin sources
        #   that do not consume CHECK_INCLUDE_DIRS, so they go on the
        #   global compile line.
        # - bare -lpcap / -lsubunit on the executable link line need the
        #   -L search paths; CMAKE_EXE_LINKER_FLAGS precede the library
        #   list, so these apply to every test binary.
        # - CMAKE_{INCLUDE,LIBRARY}_PATH feed FindCheck.cmake's
        #   FIND_PATH / FIND_LIBRARY fallback in case the (stale)
        #   pkg-config data is unreachable.
        toolchain.cache_variables["CMAKE_C_FLAGS"] = (
            f"-D_UAPI_LINUX_SOCKET_H -I{check_inc} -I{pcap_inc}"
        )
        toolchain.cache_variables["CMAKE_EXE_LINKER_FLAGS"] = (
            f"-L{check_lib} -L{pcap_lib} -L{stub_dir}"
        )
        toolchain.cache_variables["CMAKE_INCLUDE_PATH"] = f"{check_inc};{pcap_inc}"
        toolchain.cache_variables["CMAKE_LIBRARY_PATH"] = f"{check_lib};{pcap_lib}"
        # `find_package(Check REQUIRED)` in the real conan flow resolves the
        # check *package's* own check-config.cmake (config mode: the toolchain's
        # CMAKE_FIND_PACKAGE_PREFER_CONFIG=ON + the check pkg root on
        # CMAKE_PREFIX_PATH). That file only defines the imported targets
        # check::check / check::checkShared and never sets CHECK_LIBRARIES, so
        # upstream `set(LIBS ${CHECK_LIBRARIES} ...)` links an empty check library
        # and every test binary fails with `undefined symbol: tcase_create`.
        #
        # The fix is mode-independent: pre-seed the two classic FindCheck cache
        # variables that upstream consumes. CHECK_LIBRARIES=-lcheck resolves via
        # the -L<check lib> already on CMAKE_EXE_LINKER_FLAGS; CHECK_INCLUDE_DIRS
        # is redundant with the -I<check inc> on CMAKE_C_FLAGS but kept for
        # include_directories() correctness. This works in BOTH config and module
        # mode (a plain cache set( ) in FindCheck is a no-op over an existing
        # cache value), so it is robust to conan reusing a build folder or to a
        # stale case-sensitive Check_DIR hint.
        toolchain.cache_variables["CHECK_LIBRARIES"] = "-lcheck"
        toolchain.cache_variables["CHECK_INCLUDE_DIRS"] = check_inc
        # Belt-and-braces: also steer find_package(Check) to the project's own
        # tools/cmake/FindCheck.cmake (sets the same variables) in case the check
        # pkg root is NOT on the prefix path.
        toolchain.cache_variables["CMAKE_FIND_PACKAGE_PREFER_CONFIG"] = "OFF"
        toolchain.generate()

        # Check's parent/child IPC creates its comms temp file via
        # $TEMP -> P_tmpdir (/tmp); a read-only /tmp (erofs) breaks every
        # suite before the first assertion.  Point TEMP at the writable
        # build tree.  The suites must run SERIALLY: every server-based
        # suite binds the same fixed default port 4840 (UA_ServerConfig_setDefault),
        # so CTEST_PARALLEL_LEVEL>1 makes them collide (Address in use /
        # Broken pipe / spurious SEGFAULT) — observed with 16-way parallel
        # on the OHOS worker.  Serial keeps the fixed-port suites isolated.
        env = Environment()
        env.define("TEMP", self.generators_folder)
        env.define("CTEST_PARALLEL_LEVEL", "1")
        # check_pubsub_connection_ethernet opens a raw AF_PACKET ETH socket
        # on a real NIC (ETHERNET_INTERFACE).  The OHOS worker has no
        # ethernet interface and no raw-socket capability (/sys/class/net
        # not accessible, no `ip` tool), so every ETH recv channel open
        # fails with "Could not find the interface" — a genuine platform
        # block.  Upstream ships the official SKIP_ETHERNET env skip
        # (ethernet_config.h / main() returns EXIT_SUCCESS), which keeps
        # the suite honest and the W3 gate green; the ledger records this
        # case as not-run/platform-blocked with its recovery condition.
        env.define("SKIP_ETHERNET", "1")
        env.vars(self).save_script("open62541_check_temp")

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()
        self._stage_network_replay_fixtures()
        # Upstream official tests: ctest suite built with UA_BUILD_UNIT_TESTS=ON
        cmake.test()

    def _stage_network_replay_fixtures(self):
        # check_network_replay resolves its .pcap fixtures relative to its own
        # executable directory (readlink /proc/self/exe + chdir) via
        # ../../../tests/network_replay/*.pcap — an in-tree-build assumption
        # (exe at <root>/bin/tests, fixtures at <root>/tests).  Under conan's
        # out-of-source build the binary sits at <build_folder>/bin/tests, so
        # that relative path lands at <build_folder>/../tests/network_replay.
        # Stage the upstream fixtures there; otherwise pcap_open_offline()
        # returns NULL and the test dereferences the resulting NULL
        # connection manager (segfault).
        src = os.path.join(self.source_folder, "tests", "network_replay")
        dst = os.path.normpath(os.path.join(self.build_folder, "..", "tests", "network_replay"))
        os.makedirs(dst, exist_ok=True)
        for pcap in sorted(glob.glob(os.path.join(src, "*.pcap"))):
            shutil.copy2(pcap, dst)

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "open62541")
        self.cpp_info.set_property("cmake_target_name", "open62541::open62541")
        self.cpp_info.libs = ["open62541"]
        self.cpp_info.system_libs = ["m", "rt"]
