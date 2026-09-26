#!/usr/bin/env python3
"""Conan test_package for pbcopper 2.3.0.

Consumer-level verification: build and run test_pbcopper, which exercises
the public Interval / Cigar / Utility / LibraryInfo API. Emits
HMBS_TEST_PACKAGE_RESULT with the real check counters parsed from the test
binary output, and re-emits the packaged HMBS_UPSTREAM_TEST_RESULT summary.
"""

import json
import os
import re

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import can_run
from conan.tools.cmake import CMake, cmake_layout


class PbcopperTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "CMakeDeps", "CMakeToolchain", "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        if not can_run(self):
            self.output.info(
                "Cross build: pbcopper consumer was built; run it on the "
                "HarmonyOS PC target."
            )
            return
        bindir = self.cpp.build.bindirs[0]
        exe = os.path.join(self.build_folder, bindir, "test_pbcopper")
        if not os.path.isfile(exe):
            import glob

            hits = glob.glob(
                os.path.join(self.build_folder, "**", "test_pbcopper*"),
                recursive=True,
            )
            hits = [
                h
                for h in hits
                if os.path.isfile(h)
                and not h.endswith((".o", ".obj", ".cmake", ".make"))
            ]
            for h in hits:
                if os.access(h, os.X_OK) or h.endswith(".exe"):
                    exe = h
                    break
            else:
                if hits:
                    exe = hits[0]
        logfile = os.path.join(self.build_folder, "test_package.log")
        self.run('"%s" > "%s" 2>&1' % (exe, logfile), env="conanrun")
        with open(logfile, "r", encoding="utf-8", errors="replace") as handle:
            out = handle.read()
        tail = "\n".join(out.splitlines()[-12:])
        self.output.info("test_pbcopper output tail:\n" + tail)
        m = re.search(r"(\d+)/(\d+) checks passed", out)
        if not m:
            raise ConanException(
                "test_pbcopper produced no checks-passed line - harness broken"
            )
        passed = int(m.group(1))
        discovered = int(m.group(2))
        ok = passed == discovered and discovered == 8
        marker = {
            "executed": True,
            "passed": ok,
            "command": "./test_pbcopper",
            "discovered": discovered,
            "passedCount": passed,
        }
        self.output.info(
            "HMBS_TEST_PACKAGE_RESULT=" + json.dumps(marker, ensure_ascii=False)
        )
        print("HMBS_TEST_PACKAGE_RESULT=" + json.dumps(marker, ensure_ascii=False))
        if not ok:
            raise ConanException(
                "test_pbcopper failed: %d/%d checks passed (expected 8/8)"
                % (passed, discovered)
            )
        # Re-emit the packaged upstream summary (cppdap precedent).
        try:
            dep = self.dependencies["pbcopper"]
            summary_path = os.path.join(
                dep.package_folder, "res", "upstream_test_result.json"
            )
            with open(summary_path, "r", encoding="utf-8") as handle:
                upstream_marker = json.load(handle)
            for key in (
                "status",
                "framework",
                "command",
                "discovered",
                "executed",
                "passed",
                "failed",
                "skipped",
            ):
                if key not in upstream_marker:
                    raise ConanException(
                        "packaged upstream summary missing key: %s" % key
                    )
            self.output.info(
                "HMBS_UPSTREAM_TEST_RESULT="
                + json.dumps(upstream_marker, ensure_ascii=False)
            )
            print(
                "HMBS_UPSTREAM_TEST_RESULT="
                + json.dumps(upstream_marker, ensure_ascii=False)
            )
        except ConanException:
            raise
        except Exception as exc:
            self.output.warning(
                "pbcopper: packaged upstream summary unavailable (%s)" % exc
            )
