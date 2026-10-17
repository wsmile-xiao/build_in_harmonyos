#!/usr/bin/env python3
"""Conan test_package — libcmis 0.6.3 consumer test.

Builds test_libcmis.cpp against the packaged libcmis (CMakeDeps +
CMakeToolchain), runs it on the native OHOS target and counts the
per-check "CHECK-OK:" lines for the HMBS_TEST_PACKAGE_RESULT
machine-evidence marker (exit-0-alone is not proof: 6 CHECK-OK lines
are required for a pass).

Upstream evidence: the main recipe runs the upstream `make check` suite
in build() and persists the real counts to res/hmbs_upstream.json; this
test() re-emits HMBS_UPSTREAM_TEST_RESULT from that file on every run
(cache-hit rounds skip the main build, the gate still needs the marker).
"""

import json
import os
import re
import subprocess
import tempfile

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import cross_building
from conan.tools.cmake import CMake, cmake_layout


# test_libcmis.cpp performs exactly 6 checks, each printing one
# "CHECK-OK: <name>" line on success.
CONSUMER_CHECK_COUNT = 6


class LibcmisTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain"

    def requirements(self):
        self.requires(self.tested_reference_str)
        # Public headers transitively include boost/curl/libxml2/openssl
        # (e.g. libcmis/property-type.hxx -> boost/date_time.hpp); Conan 2
        # CMakeDeps strips includes of purely-transitive deps on the
        # consumer side, so declare them explicitly here (same pins as the
        # main recipe) to force full *-data.cmake generation
        # (pokerstove/DRAFT-conan2-cmakedeps-transitive-include-strip
        # precedent; visible=True alone does not fix the include strip).
        self.requires("boost/1.90.0.4")
        self.requires("curl/8.15.0")
        self.requires("libxml2/2.15.3.1")
        self.requires("openssl/3.5.6.1")

    def layout(self):
        cmake_layout(self)

    def _ensure_writable_tmp(self):
        for key in ("HMBS_TMPDIR", "TMPDIR", "TMP", "TEMP"):
            candidate = os.environ.get(key)
            if candidate and candidate != "/tmp" and os.path.isdir(candidate):
                try:
                    fd, p = tempfile.mkstemp(dir=candidate)
                    os.close(fd)
                    os.unlink(p)
                    tmp = candidate
                    break
                except Exception:
                    continue
        else:
            tmp = None
        if not tmp:
            tmp = os.path.join(self.build_folder, "hmbs-tmp")
            os.makedirs(tmp, exist_ok=True)
        for key in ("TMPDIR", "TMP", "TEMP"):
            os.environ[key] = tmp
        return tmp

    def build(self):
        self._ensure_writable_tmp()
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def _emit_upstream_marker(self):
        dep = self.dependencies["libcmis"]
        jf = os.path.join(dep.package_folder, "res", "hmbs_upstream.json")
        if not os.path.isfile(jf):
            raise ConanException(
                "[libcmis] hmbs_upstream.json missing from package; "
                "upstream tests did not run in build()"
            )
        with open(jf, encoding="utf-8") as handle:
            up_result = json.load(handle)
        msg = "HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(up_result)
        print(msg, flush=True)
        self.output.info(msg)
        if up_result.get("status") != "passed":
            raise ConanException(
                "[libcmis] upstream tests not passed: %s"
                % json.dumps(up_result)
            )

    def test(self):
        if cross_building(self):
            self.output.info("cross-building: compile/link test completed")
            return
        self._ensure_writable_tmp()
        # Upstream evidence first so both markers exist even if the
        # consumer binary below fails.
        self._emit_upstream_marker()
        bin_path = os.path.join(self.cpp.build.bindirs[0], "test_libcmis")
        if not os.path.isfile(bin_path):
            raise ConanException("test binary missing: %s" % bin_path)
        logfile = os.path.join(self.build_folder, "test_package.log")
        # L0d gate requires a literal self.run() executing the real test
        # binary; output is tee'd so CHECK-OK lines are counted from real
        # output (exit-0 alone is not proof).
        self.run('"%s" > "%s" 2>&1' % (bin_path, logfile), env="conanrun",
                 ignore_errors=True)
        output = ""
        if os.path.isfile(logfile):
            with open(logfile, "r", encoding="utf-8", errors="replace") as f:
                output = f.read()
        self.output.info("test_libcmis output:\n" + output)
        ok_count = len(re.findall(r"CHECK-OK:", output))
        marker = {
            "executed": True,
            "passed": ok_count == CONSUMER_CHECK_COUNT,
            "command": bin_path,
            "discovered": CONSUMER_CHECK_COUNT,
            "passedCount": ok_count,
        }
        msg = "HMBS_TEST_PACKAGE_RESULT=" + json.dumps(marker)
        print(msg, flush=True)
        self.output.info(msg)
        if not marker["passed"]:
            raise ConanException(
                "consumer test failed: ok=%s/%s" % (ok_count, CONSUMER_CHECK_COUNT)
            )
        self.output.info("libcmis consumer test_package passed")
