#!/usr/bin/env python3
"""Conan test_package for l2tpns 2.5.0 — OHOS compile gate + artifact tests.

l2tpns upstream ships no test suite (see test_package/MANIFEST.yml audit:
no check/test target, test/ holds load-simulation tools needing a real
LNS/LAC topology, upstream CI only runs `make install` + a daemon-start
version probe). This test_package therefore adds the run's mandatory new
OHOS-specific cases and re-emits the HMBS_UPSTREAM_TEST_RESULT no_tests
marker every run.

Executed on the OHOS device (authoritative CI, ohos-aarch64):

  1. Gate: the packaged daemon binary actually executes on OHOS via its
     argument-parsing usage path — `l2tpns --version` hits an invalid
     option char, prints usage and exits 0 BEFORE any daemon init, so this
     proves OHOS dynamic loading/executability without root, without
     /dev/net/tun and without kernel L2TP support (device reality:
     /proc/net/protocols has no l2tp entry and /proc/net/genetlink does not
     exist, so the kernel L2TP interface is unavailable; /dev/ppp exists
     but is root-only 660; /dev/net is present yet not traversable, so tun
     node availability is unproven — runtime degradation is expected and
     recorded, never asserted away by starting the daemon).
  2. test_l2tpns (C): static artifact assertions — embedded VERSION 2.5.0
     (upstream ci-test.sh's core assertion, downgraded to a binary scan),
     epoll API referenced (the run's -DHAVE_EPOLL Makefile patch branch is
     effective), no libdl.so dependency (musl -ldl removal effective),
     all 8 CLI plugins delivered as ELF shared objects, nsctl is ELF.
  3. Informational only: `nsctl --version` exit code is recorded but not
     asserted — nsctl needs a live l2tpns control endpoint on localhost,
     which the usage-path gate deliberately never starts.
"""

import json
import os
import shutil

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, cmake_layout
from conan.tools.files import replace_in_file


class L2tpnsTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeToolchain", "CMakeDeps"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def _usable_compiler(self, key, fallbacks):
        # Mirror the main recipe: profile conf may point at a stale
        # /data/service/hnp/bin/clang that no longer exists on preflight;
        # HMBS prepends the real tool dirs to PATH, so prefer an absolute
        # conf path only when it exists, else fall back to PATH lookup.
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict) or {}
        cand = compilers.get(key)
        if cand and os.path.isabs(str(cand)) and os.path.isfile(str(cand)):
            return str(cand)
        for name in fallbacks:
            found = shutil.which(name)
            if found and os.path.isfile(found):
                return found
        if cand and os.path.isfile(str(cand)):
            return str(cand)
        return fallbacks[0]

    def build(self):
        # The generated conan_toolchain.cmake can embed a stale
        # CMAKE_C_COMPILER (/data/service/hnp/bin/clang). Override it with
        # a usable compiler resolved via PATH so test_package configures
        # (same mitigation as libcli's test_package).
        cc = self._usable_compiler("c", ["clang", "cc"])
        cxx = self._usable_compiler("cpp", ["clang++", "c++", "g++"])
        self.output.info("test_package CC={} CXX={}".format(cc, cxx))
        toolchain = os.path.join(self.generators_folder, "conan_toolchain.cmake")
        if os.path.isfile(toolchain):
            for stale in ("/data/service/hnp/bin/clang",
                          "/data/service/hnp/bin/clang++"):
                try:
                    replace_in_file(self, toolchain, stale,
                                    cc if "++" not in stale else cxx)
                except Exception:
                    pass
        cmake = CMake(self)
        cmake.configure(variables={"CMAKE_C_COMPILER": cc,
                                   "CMAKE_CXX_COMPILER": cxx})
        cmake.build()

    def test(self):
        if not can_run(self):
            self.output.info("cross-building: build verified, runtime test skipped")
            return

        pkg_folder = str(self.dependencies["l2tpns"].package_folder)
        bindir = os.path.join(pkg_folder, "bin")
        daemon = os.path.join(bindir, "l2tpns")
        nsctl = os.path.join(bindir, "nsctl")
        checker = os.path.join(self.cpp.build.bindir, "test_l2tpns")

        # Gate 1 (OHOS executability, usage path): getopt stops on the first
        # invalid option char ("--version" -> 'e' after 'v'), prints usage
        # and main() returns 0 before any daemon initialization. A non-zero
        # exit here fails the test automatically.
        self.run('"{}" --version'.format(daemon))

        # Gate 2 (OHOS-specific static artifact assertions in C).
        self.run('"{}" "{}"'.format(checker, pkg_folder))

        # Informational: nsctl needs a live l2tpns control endpoint; without
        # a daemon (deliberately never started here — it needs root, TUN
        # and the kernel L2TP genetlink, none of which the device offers
        # to this process) it exits non-zero.
        # Record the outcome without failing the run.
        rc = self.run('"{}" --version'.format(nsctl), ignore_errors=True)
        self.output.info(
            "nsctl --version rc={} (informational; expected non-zero without "
            "a running l2tpns control endpoint)".format(rc))

        marker = {
            "executed": True,
            "passed": True,
            "command": checker,
            "discovered": 6,
            "passedCount": 6,
            "notes": "1 usage-path exec gate (l2tpns --version, exit 0) + "
                     "5 C artifact assertions (VERSION string, epoll "
                     "referenced, no libdl.so, 8 ELF plugins, nsctl ELF)",
        }
        self.output.info("HMBS_TEST_PACKAGE_RESULT=" + json.dumps(marker))

        # Upstream audit (MANIFEST.yml): genuinely no test suite.
        upstream_marker = {
            "status": "no_tests",
            "framework": "make",
            "command": "make all -j1",
            "discovered": 0,
            "executed": 0,
            "passed": 0,
            "failed": 0,
            "skipped": 0,
            "reason": "l2tpns 2.5.0 upstream has no test suite: root Makefile "
                      "has no check/test target; .gitlab-ci.yml only runs "
                      "scripts/ci-test.sh (make install + daemon-start "
                      "version probe needing root/TUN/kernel L2TP); test/ "
                      "holds standalone load-simulation tools (bounce, "
                      "generateload, radius) with their own Makefile that the "
                      "root build never recurses into and which require a "
                      "real LNS/LAC topology",
        }
        self.output.info("HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(upstream_marker))
