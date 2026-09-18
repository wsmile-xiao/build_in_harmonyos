#!/usr/bin/env python3
"""Conan test_package — libg722 1_2_0 consumer test.

Builds test_g722.c against the packaged libg722 (CMakeDeps +
CMakeToolchain), runs it on the native OHOS target and counts the
per-check "CHECK-OK:" lines for the HMBS_TEST_PACKAGE_RESULT
machine-evidence marker (exit-0-alone is not proof: 9 CHECK-OK lines
are required for a pass).

Upstream evidence: the main recipe runs the full upstream CTest suite
(TestDynamic + TestStatic) in build() and persists the real result to
res/hmbs_upstream.json; this test_package re-emits that persisted
result on every run (cache-hit rounds skip the main build, the gate
still needs the marker).
"""

import json
import os
import subprocess

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import cross_building
from conan.tools.cmake import CMake, cmake_layout

# test_g722.c performs exactly 9 checks, each printing one
# "CHECK-OK: <name>" line on success.
CONSUMER_CHECK_COUNT = 9


class Libg722TestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def _ensure_writable_tmp(self):
        for key in ("TMPDIR", "TMP", "TEMP"):
            candidate = os.environ.get(key)
            if candidate and os.path.isdir(candidate):
                tmp = candidate
                break
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

    def test(self):
        if cross_building(self):
            self.output.info("cross-building: compile/link test completed")
            return
        self._ensure_writable_tmp()
        bin_path = os.path.join(self.cpp.build.bindirs[0], "test_g722")
        if not os.path.isfile(bin_path):
            raise ConanException("test binary missing: %s" % bin_path)
        proc = subprocess.run(
            [bin_path],
            env=dict(os.environ),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            timeout=300,
        )
        output = proc.stdout or ""
        self.output.info(output[-2000:])
        ok_count = output.count("CHECK-OK:")
        marker = {
            "executed": True,
            "passed": proc.returncode == 0 and ok_count == CONSUMER_CHECK_COUNT,
            "command": bin_path,
            "discovered": CONSUMER_CHECK_COUNT,
            "passedCount": ok_count,
        }
        line = "HMBS_TEST_PACKAGE_RESULT=" + json.dumps(marker, ensure_ascii=False)
        print(line, flush=True)
        self.output.info(line)
        if not marker["passed"]:
            raise ConanException(
                "consumer test failed: rc=%s ok=%s/%s"
                % (proc.returncode, ok_count, CONSUMER_CHECK_COUNT)
            )
        self.run(bin_path, env="conanrun")
        self._emit_upstream_marker()

    def _emit_upstream_marker(self):
        data = None
        try:
            pkg_name = self.tested_reference_str.split("/")[0]
        except Exception:
            pkg_name = "libg722"
        try:
            dep = self.dependencies[pkg_name]
            pkg_folder = getattr(dep, "package_folder", None)
            if pkg_folder:
                cand = os.path.join(pkg_folder, "res", "hmbs_upstream.json")
                if os.path.isfile(cand):
                    with open(cand, "r", encoding="utf-8") as handle:
                        data = json.load(handle)
        except Exception:
            data = None
        if isinstance(data, dict) and data.get("discovered"):
            line = "HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(data, ensure_ascii=False)
            print(line, flush=True)
            self.output.info(line)
        else:
            self.output.warning(
                "persisted hmbs_upstream.json missing; "
                "upstream evidence only available on fresh build"
            )
