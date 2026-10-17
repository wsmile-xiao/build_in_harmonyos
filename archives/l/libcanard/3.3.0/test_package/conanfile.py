#!/usr/bin/env python3
"""Conan test_package for libcanard 3.3.0.

Consumer test (TAP-style binary with 16 checks covering version macros,
instance init, TX push/peek/pop, RX subscribe/query/unsubscribe and the
acceptance filter helpers). The binary output is parsed for "ok" lines;
the counts feed HMBS_TEST_PACKAGE_RESULT. The upstream ctest result
persisted by the main recipe (res/upstream_test_result.json) is re-emitted
so the evidence survives package cache hits.
"""
import json
import os
import subprocess

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, cmake_layout

N_CHECKS = 16


class LibcanardTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeToolchain", "CMakeDeps"

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
            return
        # Mirror the main recipe: never rely on system /tmp (read-only on the
        # true machine). Prefer injected TMPDIR/TMP/TEMP, else use build folder.
        tmpdir = os.environ.get("TMPDIR") or os.environ.get("TMP") or os.environ.get("TEMP")
        if not (tmpdir and os.path.isdir(tmpdir) and os.access(tmpdir, os.W_OK)):
            tmpdir = os.path.join(self.build_folder, ".hmbs-tmp")
            try:
                os.makedirs(tmpdir, exist_ok=True)
            except Exception:
                pass
            for var in ("TMPDIR", "TMP", "TEMP"):
                os.environ[var] = tmpdir
        binary = os.path.join(self.cpp.build.bindir, "test_libcanard")
        if not os.path.isfile(binary):
            raise RuntimeError(f"test binary missing: {binary}")
        # L0d gate: real execution of the consumer test binary.
        self.run(binary, env="conanrun")
        env = dict(os.environ)
        dep = self.dependencies["libcanard"]
        libdir = os.path.join(dep.package_folder, "lib")
        if os.path.isdir(libdir):
            prev = env.get("LD_LIBRARY_PATH")
            env["LD_LIBRARY_PATH"] = libdir + (os.pathsep + prev if prev else "")
        proc = subprocess.run(
            [binary],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            timeout=300,
            env=env,
        )
        output = proc.stdout or ""
        self.output.info(output)
        passed_count = sum(
            1 for line in output.splitlines() if line.startswith("ok ")
        )
        has_failure = any(
            line.startswith("not ok ") for line in output.splitlines()
        )
        command = "test_libcanard (16 TAP checks: version/init/TX/RX/filters)"
        marker = {
            "executed": True,
            "passed": proc.returncode == 0 and passed_count == N_CHECKS and not has_failure,
            "command": command,
            "discovered": N_CHECKS,
            "passedCount": passed_count,
        }
        # Re-emit the upstream suite result persisted by the main recipe.
        res_json = os.path.join(dep.package_folder, "res", "upstream_test_result.json")
        if not os.path.isfile(res_json):
            raise RuntimeError("upstream_test_result.json missing from package res/")
        with open(res_json, "r", encoding="utf-8") as fh:
            upstream = json.load(fh)
        self.output.info("HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(upstream))
        if (upstream.get("status") != "passed"
                or int(upstream.get("discovered", 0)) <= 0
                or int(upstream.get("executed", 0)) != int(upstream.get("discovered", 0))
                or int(upstream.get("passed", 0)) != int(upstream.get("discovered", 0))):
            raise RuntimeError(f"upstream result invalid: {upstream}")
        self.output.info("HMBS_TEST_PACKAGE_RESULT=" + json.dumps(marker))
        print("HMBS_TEST_PACKAGE_RESULT=" + json.dumps(marker))
        if not marker["passed"]:
            raise RuntimeError(
                f"test_package failed: {passed_count}/{N_CHECKS} checks passed"
            )
