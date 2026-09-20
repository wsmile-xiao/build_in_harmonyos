#!/usr/bin/env python3
"""Conan test_package for cppdap 1.58.0a.

Consumer-level verification: build and run test_cppdap, which exercises the
public Session / protocol / io API. Emits HMBS_TEST_PACKAGE_RESULT with the
real check counters parsed from the test binary output.
"""
import json
import os
import re

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout


class CppdapTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        deps = CMakeDeps(self)
        deps.generate()
        tc = CMakeToolchain(self)
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        bindir = self.cpp.build.bindirs[0]
        exe = os.path.join(self.build_folder, bindir, "test_cppdap")
        if not os.path.isfile(exe):
            exe = os.path.join(bindir, "test_cppdap")
        if not os.path.isfile(exe):
            import glob
            hits = glob.glob(os.path.join(self.build_folder, "**", "test_cppdap*"), recursive=True)
            hits = [h for h in hits if os.path.isfile(h) and not h.endswith((".o", ".obj", ".cmake", ".make"))]
            for h in hits:
                if os.access(h, os.X_OK) or h.endswith(".exe"):
                    exe = h
                    break
            else:
                if hits:
                    exe = hits[0]
        logfile = os.path.join(self.build_folder, "test_package.log")
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        self.run(bash + " -c '" + exe + " > " + logfile + " 2>&1'", env="conanrun")
        with open(logfile, "r", encoding="utf-8", errors="replace") as f:
            out = f.read()
        tail = "\n".join(out.splitlines()[-10:])
        self.output.info("test_cppdap output tail:\n" + tail)
        m = re.search(r"(\d+)/(\d+) checks passed", out)
        if not m:
            raise ConanException("test_cppdap produced no checks-passed line - harness broken")
        passed = int(m.group(1))
        discovered = int(m.group(2))
        ok = passed == discovered and discovered > 0
        marker = {
            "executed": True,
            "passed": ok,
            "command": "./test_cppdap",
            "discovered": discovered,
            "passedCount": passed,
        }
        self.output.info("HMBS_TEST_PACKAGE_RESULT=" + json.dumps(marker, ensure_ascii=False))
        print("HMBS_TEST_PACKAGE_RESULT=" + json.dumps(marker, ensure_ascii=False))
        if not ok:
            raise ConanException("test_cppdap failed: %d/%d checks passed" % (passed, discovered))
        try:
            pkg_name = self.tested_reference_str.split("/")[0]
            dep = self.dependencies[pkg_name]
            summary_path = os.path.join(dep.package_folder, "res", "upstream_test_result.json")
            with open(summary_path, "r", encoding="utf-8") as f:
                upstream_marker = json.load(f)
            for _k in ("status", "framework", "command", "discovered", "executed", "passed", "failed", "skipped"):
                if _k not in upstream_marker:
                    raise ConanException("packaged upstream summary missing key: %s" % _k)
            if upstream_marker.get("discovered", 0) <= 0 or upstream_marker.get("executed", 0) <= 0:
                raise ConanException("packaged upstream summary has zero counts: %s" % upstream_marker)
            self.output.info("HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(upstream_marker, ensure_ascii=False))
            print("HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(upstream_marker, ensure_ascii=False))
            if upstream_marker.get("status") != "passed":
                raise ConanException("upstream cppdap tests did not pass: %s" % upstream_marker)
        except ConanException:
            raise
        except Exception as e:
            raise ConanException("cannot forward upstream evidence (missing res/upstream_test_result.json?): %s" % e)
