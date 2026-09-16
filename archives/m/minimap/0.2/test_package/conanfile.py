#!/usr/bin/env python3
"""Conan test_package for minimap 0.2.

Layer A: test_minimap.py runs the installed CLI (version/usage/direct
mapping/index dump+load).
Layer B: test_minimap_consumer.c is compiled against the installed
libminimap.a + headers (with the Conan zlib) and maps a query, proving the
library is usable by consumers.

Emits HMBS markers for CI preflight.
"""
import json
import os
import shlex
import sys

from conan import ConanFile
from conan.errors import ConanException


class MinimapTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def _bash(self):
        for candidate in (
            os.environ.get("CONFIG_SHELL"),
            "/storage/Users/currentUser/.harmonybrew/bin/bash",
            "/data/service/hnp/bin/bash",
            "/bin/bash",
        ):
            if candidate and os.path.isfile(candidate):
                return candidate
        return "bash"

    def _run_shell(self, command, env="conanrun"):
        if self.settings.os == "OHOS":
            return self.run(f"{shlex.quote(self._bash())} -c {shlex.quote(command)}",
                            ignore_errors=True, env=env)
        return self.run(command, ignore_errors=True, env=env)

    def test(self):
        dep = self.dependencies["minimap"]
        exe = os.path.join(dep.cpp_info.bindirs[0], "minimap")
        if not os.path.isfile(exe):
            raise ConanException(f"installed minimap not found at {exe}")

        here = os.path.dirname(os.path.abspath(__file__))
        workdir = os.environ.get("TMPDIR") or os.path.join(os.path.expanduser("~"), "tmp")
        os.makedirs(workdir, exist_ok=True)
        result_file = os.path.join(workdir, "minimap-harness-result.json")

        harness = os.path.join(here, "test_minimap.py")
        python = shlex.quote(sys.executable or "python3")
        rc = self._run_shell(f"{python} {shlex.quote(harness)} {shlex.quote(exe)} "
                             f"{shlex.quote(result_file)} {shlex.quote(workdir)}")
        summary = {}
        if os.path.isfile(result_file):
            with open(result_file, "r") as handle:
                summary = json.load(handle)
        passed = int(summary.get("passed", 0))
        total = int(summary.get("total", 0))
        failed = int(summary.get("failed", 1))

        consumer_ok = False
        consumer_src = os.path.join(here, "test_minimap_consumer.c")
        consumer_bin = os.path.join(workdir, "test_minimap_consumer")
        executables = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict) or {}
        cc = str(executables.get("c") or "cc")
        zlib = self.dependencies["zlib"]
        z_inc = zlib.cpp_info.includedirs[0]
        z_lib = zlib.cpp_info.libdirs[0]
        if zlib.package_folder:
            z_inc = os.path.join(zlib.package_folder, z_inc)
            z_lib = os.path.join(zlib.package_folder, z_lib)
        compile_cmd = " ".join([
            shlex.quote(cc), "-O2", "-I", shlex.quote(dep.cpp_info.includedirs[0]),
            "-I", shlex.quote(z_inc),
            shlex.quote(consumer_src),
            "-L", shlex.quote(dep.cpp_info.libdirs[0]), "-lminimap",
            "-L", shlex.quote(z_lib), "-lz", "-lm",
            "-o", shlex.quote(consumer_bin),
        ])
        # Compile with the build environment so the linker (lld) can load its
        # own shared libraries (e.g. libxml2.so.16 from the OHOS SDK) via the
        # profile buildenv LD_LIBRARY_PATH. Running the binary uses conanrun.
        rc_c = self._run_shell(compile_cmd, env="conanbuild")
        if rc_c == 0:
            target = os.path.join(workdir, "target.fa")
            query = os.path.join(workdir, "query.fa")
            rc_run = self._run_shell(
                f"{shlex.quote(consumer_bin)} {shlex.quote(target)} {shlex.quote(query)}")
            consumer_ok = (rc_run == 0)
        total += 1
        if consumer_ok:
            passed += 1
        else:
            failed += 1
            print("[FAIL] consumer: compile+link+run against installed libminimap.a")

        print("HMBS_TEST_PACKAGE_RESULT=" + json.dumps({
            "executed": True,
            "passed": (rc == 0 and failed == 0),
            "command": "test_minimap.py + test_minimap_consumer.c",
            "consumer_passed": passed,
            "consumer_total": total,
        }))
        print("HMBS_UPSTREAM_TEST_RESULT=" + json.dumps({
            "status": "skipped",
            "reason": "minimap 0.2 ships no tests/ and no make check target",
            "discovered": 0, "executed": 0, "passed": 0, "failed": 0, "skipped": 0,
        }))

        if rc != 0 or failed != 0:
            raise ConanException(f"minimap test failed (rc={rc}, failed={failed})")
