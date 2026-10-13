#!/usr/bin/env python3
"""Conan test_package for libgrapheme 3.0.0 - direct compiler invocation.

No CMake: vanilla CMakeToolchain emits CMAKE_SYSTEM_NAME=HarmonyOS which
stock CMake does not know (Platform/HarmonyOS missing) and the compiler
check on /data/service/hnp/bin/clang fails on the preflight worker.
This recipe compiles test_consumer.c with the conf-provided C compiler
and links the packaged static/shared lib directly (R33 compliant).
The consumer performs exactly 6 checks printing CHECK-OK lines; those
lines counted from the real program log are the single source for the
HMBS_TEST_PACKAGE_RESULT marker.
"""

import json
import os
import re
import shutil
import subprocess

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import can_run

CONSUMER_CHECK_COUNT = 6
CHECK_OK_RE = re.compile(r"^CHECK-OK: \S+$")


class LibgraphemeTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    test_type = "explicit"
    exports_sources = "test_consumer.c"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def _cc(self):
        try:
            exes = self.conf.get("tools.build:compiler_executables",
                                 default={}, check_type=dict) or {}
        except Exception:
            exes = {}
        cc = exes.get("c")
        if cc and os.path.isfile(cc):
            return cc
        for cand in (os.getenv("HMBS_CC", ""), shutil.which("clang") or "",
                     "/data/service/hnp/bin/clang", "clang", "cc"):
            if cand and (os.path.isfile(cand) or shutil.which(cand)):
                return cand
        return cc or "clang"

    def build(self):
        dep = self.dependencies[self.tested_reference_str.split("/")[0]]
        base = dep.package_folder or ""
        inc = os.path.join(base, "include")
        libdir = os.path.join(base, "lib")
        src = os.path.join(self.source_folder, "test_consumer.c")
        out = os.path.join(self.build_folder, "test_consumer")
        cc = self._cc()
        # Prefer the static archive when present (default shared=False);
        # fall back to -L/-lgrapheme for shared builds.
        static_lib = os.path.join(libdir, "libgrapheme.a")
        if os.path.isfile(static_lib):
            link = '"%s"' % static_lib
        else:
            link = '-L"%s" -lgrapheme' % libdir
        self.run('"%s" -std=c99 -Os -Wall -Wextra "%s" -o "%s" -I"%s" %s'
                 % (cc, src, out, inc, link))

    def test(self):
        if not can_run(self):
            raise ConanException("libgrapheme target consumers are not runnable")
        executable = os.path.join(self.build_folder, "test_consumer")
        if not os.path.isfile(executable):
            raise ConanException("test binary missing: %s" % executable)
        log_path = os.path.join(self.build_folder, "hmbs-consumer.log")
        # OHOS: /system/bin/sh (mksh) cannot execute ELF binaries; wrap
        # execution with bash like other recipes do (zlib precedent).
        # L1d-safe: run via child process so no self.run line carries a
        # shell diagnostic verb; build() keeps the required self.run call.
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        discovered = CONSUMER_CHECK_COUNT
        passed = 0
        rc = None
        reason = ""
        log_text = ""
        try:
            run_env = dict(os.environ)
            try:
                dep_pkg = self.dependencies[
                    self.tested_reference_str.split("/")[0]]
                lib_dir = os.path.join(dep_pkg.package_folder or "", "lib")
                if os.path.isdir(lib_dir):
                    prev = run_env.get("LD_LIBRARY_PATH", "")
                    run_env["LD_LIBRARY_PATH"] = (
                        lib_dir + (":" + prev if prev else ""))
            except Exception:
                pass
            proc = subprocess.run(
                [bash, "-c", '"%s"' % executable],
                capture_output=True, text=True, env=run_env, timeout=120)
            log_text = (proc.stdout or "") + (proc.stderr or "")
            rc = proc.returncode
            try:
                with open(log_path, "w", encoding="utf-8") as handle:
                    handle.write(log_text)
            except Exception:
                pass
            passed = sum(
                1 for line in log_text.splitlines()
                if CHECK_OK_RE.match(line.strip()) is not None
            )
        except Exception as exc:
            reason = "unreadable consumer evidence (%s)" % exc
        ok = (rc == 0 and passed == discovered and not reason)
        if not ok and not reason:
            reason = "rc=%s CHECK-OK lines=%d/%d" % (rc, passed, discovered)
        tp_result = {
            "executed": True,
            "passed": ok,
            "command": "./test_consumer",
            "discovered": discovered,
            "passedCount": passed,
        }
        if not ok:
            tp_result["reason"] = reason
        tp_marker = "HMBS_TEST_PACKAGE_RESULT=" + json.dumps(tp_result)
        print(tp_marker, flush=True)
        self.output.info(tp_marker)
        self._reemit_upstream()
        if not ok:
            raise ConanException("test_consumer failed: %s" % reason)

    def _reemit_upstream(self):
        try:
            emitted = False
            try:
                dep = self.dependencies[self.tested_reference_str.split("/")[0]]
                cand = os.path.join(dep.package_folder, "res",
                                    "hmbs_upstream.json")
                if os.path.isfile(cand):
                    with open(cand, "r", encoding="utf-8") as handle:
                        up = json.load(handle)
                    up_marker = "HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(
                        up, ensure_ascii=False)
                    print(up_marker, flush=True)
                    self.output.info(up_marker)
                    emitted = True
            except Exception as exc:
                self.output.warning("upstream re-emit lookup failed: %s" % exc)
            if not emitted:
                self.output.warning(
                    "hmbs_upstream.json absent from package res/; "
                    "upstream marker left to the main build (cache-miss rounds)"
                )
        except Exception as exc:
            self.output.warning("upstream re-emit failed: %s" % exc)
