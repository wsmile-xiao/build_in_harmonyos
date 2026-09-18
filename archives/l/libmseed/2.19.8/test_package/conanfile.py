#!/usr/bin/env python3
"""Conan test_package for libmseed 2.19.8 — Conan L1 official test.

Consumer binary test_libmseed.c exercises 6 real libmseed API checks
(version, MSRecord/trace-group lifecycle, time round-trip, sample-size
lookup, encoding + sample-rate helpers). Upstream evidence built by
conanfile.py build() is re-emitted here so it survives Conan cache hits.
CI runs this automatically via `conan create` (which invokes test_package).

No CMakeToolchain: the profile compiler /data/service/hnp/bin/clang does
not exist on the preflight worker and CMake 4.4 has no Platform/HarmonyOS
module, so even the trivial project() fails compiler identification
(preflight 2026-09-16: test package CMake Error at CMakeLists.txt:2).
Compile the single test_libmseed.c directly with PATH clang
(dhcpoptinj/0.5.3 precedent).
"""

import json
import os
import shutil

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import can_run


class LibmseedTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build(self):
        dep = self.dependencies["libmseed"]
        includes = " ".join(
            '"-I%s"' % p for p in dep.cpp_info.includedirs)
        libdirs = " ".join(
            '"-L%s"' % p for p in dep.cpp_info.libdirs)
        libs = " ".join(
            "-l%s" % lib for lib in dep.cpp_info.libs)
        syslibs = " ".join(
            "-l%s" % lib for lib in dep.cpp_info.system_libs)
        cc = shutil.which("clang") or shutil.which("cc") or "clang"
        src = os.path.join(self.source_folder, "test_libmseed.c")
        out = os.path.join(self.build_folder, "test_libmseed")
        self.run(
            '%s -O2 "%s" -o "%s" %s %s %s %s'
            % (cc, src, out, includes, libdirs, libs, syslibs))

    def test(self):
        if not can_run(self):
            self.output.info("Cross-building: skip runtime execution")
            return
        # L0d: the consumer binary must run through Conan self.run so a
        # non-zero exit fails the package. The binary prints 6 TAP-style
        # `ok N` lines and exits 0 only when all 6 checks pass.
        test_binary = os.path.join(self.build_folder, "test_libmseed")
        if not os.path.isfile(test_binary):
            for root, _, files in os.walk(self.build_folder):
                if "test_libmseed" in files:
                    test_binary = os.path.join(root, "test_libmseed")
                    break
        if not os.path.isfile(test_binary):
            raise ConanException("test_libmseed binary not found after build")
        self.run('"%s"' % test_binary, env="conanrun")
        discovered = 6
        tp_result = {
            "executed": True,
            "passed": True,
            "command": "./test_libmseed (6 API checks)",
            "discovered": discovered,
            "passedCount": discovered,
        }
        print("HMBS_TEST_PACKAGE_RESULT=%s" % json.dumps(tp_result), flush=True)
        self.output.info("HMBS_TEST_PACKAGE_RESULT=%s" % json.dumps(tp_result))
        # Re-emit the upstream evidence persisted by build() into
        # <package>/res/upstream_test_result.json. test_package runs on every
        # preflight even when conan skips a cached build() ("Already
        # installed!"), so this guarantees HMBS_UPSTREAM_TEST_RESULT is
        # always present. Content is the real device-run JSON, validated here.
        dep = self.dependencies["libmseed"]
        result_path = os.path.join(dep.package_folder, "res", "upstream_test_result.json")
        if not os.path.isfile(result_path):
            raise ConanException(
                "upstream_test_result.json not found in package (%s) — "
                "upstream tests did not run during build(); refusing to pass "
                "silently" % result_path
            )
        with open(result_path, "r", encoding="utf-8") as handle:
            upstream = json.load(handle)
        for key in ("status", "framework", "command", "discovered",
                    "executed", "passed", "failed", "skipped"):
            if key not in upstream:
                raise ConanException(
                    "upstream_test_result.json missing key %r" % key)
        if not isinstance(upstream["discovered"], int) or upstream["discovered"] <= 0:
            raise ConanException(
                "upstream_test_result.json has invalid discovered=%r" % (
                    upstream.get("discovered"),))
        if upstream["executed"] < upstream["discovered"]:
            raise ConanException(
                "upstream_test_result.json executed < discovered (%r < %r)" % (
                    upstream.get("executed"), upstream.get("discovered")))
        marker_line = "HMBS_UPSTREAM_TEST_RESULT=%s" % json.dumps(
            upstream, ensure_ascii=False)
        print(marker_line, flush=True)
        self.output.info(marker_line)
