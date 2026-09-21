#!/usr/bin/env python3
"""Conan recipe for smtpping 1.1.4 — SMTP server delay/throughput measurement tool.

smtpping (Halon Security) runs a full SMTP transaction per probe
(banner/HELO/MAIL/RCPT/DATA/QUIT) and reports per-phase round-trip times,
like ping for SMTP. Pure C++ plus POSIX sockets; no third-party dependencies.

Key adaptation points:
  - Upstream's Resolver uses the glibc reentrant resolver API
    (res_ninit/res_nquery/res_nclose + a struct __res_state member). That API
    does not exist in the OHOS NDK headers (resolv.h declares only
    res_init/res_query/res_querydomain/res_search/res_mkquery/res_send plus
    dn_comp/dn_expand/dn_skipname) nor in OHOS libc. Patches 0001/0002 port
    Resolver to res_query() + the global h_errno. smtpping itself is
    single-threaded per process (parallelism is fork-based), so the
    process-global resolver state is safe here.
  - Upstream declares cmake_minimum_required(VERSION 2.8); CMake >= 4.0
    removed compatibility with policies older than 3.5. Upstream fixed this in
    v1.1.5 by requiring the 3.5 policy version (halon/smtpping PR #13), so the
    source stays untouched and the floor is set via
    CMAKE_POLICY_VERSION_MINIMUM in the toolchain.
  - Upstream links `resolv` only when CMAKE_SYSTEM_NAME is "Linux"; under
    OHOS (CMAKE_SYSTEM_NAME=OHOS) res_query() comes from libc.so, so no extra
    link library is required. `pthread` resolves to the NDK's libpthread.a.
  - Upstream ships no test suite (no tests/ directory, no
    enable_testing()/add_test()). test_package adds a consumer E2E: a mock
    SMTP server is built and the packaged binary is driven against it over
    loopback, plus CLI and negative-control assertions (see test.sh).
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import get, apply_conandata_patches, copy, export_conandata_patches


class SmtppingConan(ConanFile):
    name = "smtpping"
    version = "1.1.4"
    description = "SMTP ping — measures SMTP server delay, delay variation and throughput"
    license = "GPL-2.0-or-later"
    homepage = "https://github.com/halon/smtpping"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    topics = ("smtp", "benchmark", "network", "cli")

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # None. Every include is libc/libc++ (stdio/stdlib/getopt/signal/
        # sys/socket/arpa/inet/netdb/semaphore/sys/mman) plus pthread; DNS is
        # provided by libc (res_query) after patches 0001/0002.
        pass

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        # Upstream cmake_minimum_required(VERSION 2.8) is rejected by
        # CMake >= 4.0; keep the source pristine and raise the policy floor.
        tc.cache_variables["CMAKE_POLICY_VERSION_MINIMUM"] = "3.5"
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()
        # Upstream installs only the binary and man page; ship the GPL license.
        copy(self, "LICENSE", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = []
        self.cpp_info.includedirs = []
