#!/usr/bin/env python3
"""Conan recipe for handy 0.2.0 — a concise C++11 network library.

handy (yedf/handy) is a header-plus-source C++11 event-driven network
library: epoll-based EventBase loop, TCP/UDP servers and clients, timers,
thread pool, HTTP codec, an ini-style Conf parser, a built-in stat server
and a slice/status/port layer.  Upstream is zero-dependency apart from
pthreads — the CMakeLists.txt only does find_package(Threads REQUIRED).

Upstream ships two build paths:

* CMakeLists.txt — builds libhandy_s.a (BUILD_HANDY_STATIC_LIBRARY=ON by
  default) or libhandy.so, and installs headers to include/handy/.  This
  recipe uses this path for the packaged library.  CMAKE_HOST_UNIX is true
  on HarmonyOS so the OS_LINUX branch is selected (correct: the poller and
  port_posix both use Linux APIs).
* Makefile — a leveldb-style shell-driven Makefile (./build_config detects
  the OS) which additionally links the upstream test harness
  `handy_test` (test/*.ut.cc aggregated by test/ut.cc main +
  RunAllTests).  The packaged library does not need this path, but the
  recipe uses it to run upstream's own registered tests as a hard gate
  (see _run_upstream_tests).

musl (OHOS) differences handled by patches/0001:

* glibc defines DEFFILEMODE in <sys/stat.h>; musl does not.  handy's
  Logger::setFileName and its logfile reopen path call open(...,
  DEFFILEMODE).  The patch defines DEFFILEMODE from POSIX mode bits when
  the macro is missing, guarded by #ifndef so glibc builds are untouched.

Upstream registered tests (N=11, counted with grep '^TEST(' test/*.ut.cc):

* conf.ut.cc    : allFiles (parses test/files/*.ini fixtures)
* handy.ut.cc   : Ip4Addr, EventBase, Timer, TcpServer1, kevent
* tcpcli.ut.cc  : tcpcli
* threads.ut.cc : ThreadPool, SafeQueue
* util.ut.cc    : static_func, ExitCaller

The harness prints `==== PASSED <n> tests`; a failing ASSERT aborts the
process before the summary line.  The recipe therefore greps for the
summary and requires n == 11.  Ip4Addr resolves "www.baidu.com" and
tcpcli connects to www.baidu.com:80/81 plus localhost:10000 — these need
outbound network, which the OHOS worker has (the local run of this exact
suite passed 11/11 on-device; CI evidence is attached in the PR body).
"""

import os
import shlex
import subprocess

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.env import Environment, VirtualRunEnv
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches

UPSTREAM_TEST_COUNT = 11


class HandyConan(ConanFile):
    name = "handy"
    version = "0.2.0"
    description = "Concise C++11 network library (event loop, TCP/UDP, HTTP, threads)"
    license = "BSD-2-Clause"
    homepage = "https://github.com/yedf/handy"
    url = "https://github.com/yedf/handy"
    package_type = "library"

    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}

    def export_sources(self):
        export_conandata_patches(self)

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"handy is adapted for Linux and OHOS, not {self.settings.os}"
            )

    def layout(self):
        cmake_layout(self)

    def source(self):
        from conan.tools.files import get
        get(self, **self.conan_data["sources"][str(self.version)], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.cache_variables["CMAKE_POLICY_VERSION_MINIMUM"] = "3.5"
        # handy 0.2.0 predates cmake 3.5+ policy handling; keep the static
        # library path (upstream default) unless shared was requested.
        tc.variables["BUILD_HANDY_STATIC_LIBRARY"] = not bool(self.options.shared)
        tc.variables["BUILD_HANDY_SHARED_LIBRARY"] = bool(self.options.shared)
        tc.variables["BUILD_HANDY_EXAMPLES"] = False
        if not self.options.shared:
            tc.variables["CMAKE_POSITION_INDEPENDENT_CODE"] = bool(self.options.fPIC)
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()
        self._run_upstream_tests()

    def package(self):
        cmake = CMake(self)
        cmake.install()
        copy(self, "LICENSE", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"), keep_path=False)

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "handy")
        self.cpp_info.set_property("cmake_target_name", "handy::handy")
        self.cpp_info.libs = ["handy_s" if not self.options.shared else "handy"]
        if str(self.settings.os) in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["pthread"]

    # ── upstream test harness (Makefile path) ──────────────────────────

    def _run_upstream_tests(self):
        if not can_run(self):
            self.output.warning(
                "Cannot execute target binaries on this build host; "
                "upstream handy_test must run on a native OHOS worker."
            )
            return
        test_bin = os.path.join(self.source_folder, "handy_test")
        if not os.path.isfile(test_bin):
            # The CMake path does not build the test binary; drive the
            # upstream Makefile in the source tree to produce it.
            self._build_upstream_test_via_makefile()
        if str(self.settings.os) == "OHOS":
            self._sign_upstream_test_binary()
        env = os.environ.copy()
        env["LD_LIBRARY_PATH"] = "/system/lib64:" + env.get("LD_LIBRARY_PATH", "")
        # upstream conf.ut.cc's allFiles reads test/files/*.ini relative to cwd
        output = subprocess.run(
            [test_bin],
            cwd=self.source_folder,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            errors="replace",
            env=env,
        )
        combined = output.stdout or ""
        self.output.info(f"handy_test output tail: {combined[-2000:]}")
        if output.returncode != 0:
            raise ConanException(
                f"handy_test exited with {output.returncode}: {combined[-1500:]}"
            )
        passed = None
        for line in combined.splitlines():
            if "PASSED" in line and "tests" in line:
                try:
                    passed = int(line.strip().split()[2])
                except (IndexError, ValueError):
                    passed = None
        if passed != UPSTREAM_TEST_COUNT:
            raise ConanException(
                f"handy_test reported {passed} passed tests, "
                f"expected {UPSTREAM_TEST_COUNT}"
            )
        self.output.info(f"upstream handy_test: {passed}/{UPSTREAM_TEST_COUNT} PASSED")

    def _build_upstream_test_via_makefile(self):
        shell = "/data/service/hnp/bin/bash"
        if not os.path.isfile(shell):
            shell = "bash"
        compilers = self.conf.get("tools.build:compiler_executables",
                                  default={}, check_type=dict) or {}
        cc = compilers.get("c", "clang")
        cxx = compilers.get("cpp", "clang++")
        make_cmd = (
            f"cd {shlex.quote(self.source_folder)} && "
            f"CC={shlex.quote(cc)} CXX={shlex.quote(cxx)} TARGET_OS=Linux "
            f"make handy_test -j2"
        )
        self.run(make_cmd)

    def _sign_upstream_test_binary(self):
        """Sign an ELF so the OHOS loader accepts it (kernel enforces codesign)."""
        objcopy = "/data/service/hnp/bin/llvm-objcopy"
        signer = "/data/service/hnp/bin/binary-sign-tool"
        target = os.path.join(self.source_folder, "handy_test")
        if not os.path.isfile(target):
            return
        for tool in (objcopy, signer):
            if not os.path.isfile(tool):
                self.output.warning(f"missing signing tool {tool}; skipping sign")
                return
        self.run(shlex.join([objcopy, "--remove-section", ".codesign", target]))
        self.run(shlex.join([signer, "sign", "-inFile", target,
                             "-outFile", target, "-selfSign", "1"]))
