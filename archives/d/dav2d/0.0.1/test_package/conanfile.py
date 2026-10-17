#!/usr/bin/env python3
"""Conan test_package — dav2d 0.0.1 (Conan L1 consumer test).

Builds test_package.c against the packaged libdav2d, runs the real
decoder lifecycle (version/defaults/open/flush/close + negative case),
parses the true assertion counters from the binary output into
HMBS_TEST_PACKAGE_RESULT, then re-emits the upstream verdict persisted
by build() (res/upstream_test_result.json) as HMBS_UPSTREAM_TEST_RESULT
so evidence survives Conan cache hits.
"""
import json
import os
import re
import shlex

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import can_run
from conan.tools.files import chdir


class Dav2dTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build(self):
        dep = self.dependencies["dav2d"].cpp_info
        compilers = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict) or {}
        cc = compilers.get("c") or os.environ.get("CC", "cc")
        # Respect the HMBS-injected writable TMPDIR/TMP/TEMP (true-device
        # /tmp is read-only). Only fall back to a source-local tmp dir when
        # the platform did not inject one; never clobber a writable value
        # with a blind overwrite.
        for _key in ("TMPDIR", "TMP", "TEMP"):
            _val = os.environ.get(_key)
            if _val and os.path.isdir(_val):
                continue
            _fb = os.path.join(self.source_folder, "tmp")
            os.makedirs(_fb, exist_ok=True)
            os.environ[_key] = _fb
        cc = self._compiler_command(cc)
        includes = " ".join(shlex.quote("-I%s" % path) for path in dep.includedirs)
        libdirs = " ".join(shlex.quote("-L%s" % path) for path in dep.libdirs)
        libs = " ".join("-l%s" % lib for lib in dep.libs + dep.system_libs)
        rpath = " ".join(shlex.quote("-Wl,-rpath,%s" % path) for path in dep.libdirs)
        with chdir(self, self.source_folder):
            self.run("%s -std=gnu99 test_package.c -o test_package %s %s %s %s -ldl"
                     % (cc, includes, libdirs, libs, rpath))

    def test(self):
        if not can_run(self):
            self.output.info("cross-building: compile+link only")
            return
        exe_name = "test_package.exe" if self.settings.os == "Windows" else "test_package"
        exe = os.path.join(self.source_folder, exe_name)
        log = os.path.join(self.build_folder, "test_package.log")
        rc = self.run("'%s' > '%s' 2>&1" % (exe, log), env="conanrun", ignore_errors=True)
        with open(log, encoding="utf-8", errors="replace") as handle:
            out = handle.read()
        print(out, end="" if out.endswith("\n") else "\n")
        marker = self._parse_consumer_result(out, rc, exe)
        print("HMBS_TEST_PACKAGE_RESULT=" + json.dumps(marker), flush=True)
        if not (marker["executed"] and marker["passed"]):
            raise ConanException(
                "[dav2d] test_package consumer test failed: %s" % json.dumps(marker))

        dep = self.dependencies["dav2d"]
        up_file = os.path.join(dep.package_folder, "res", "upstream_test_result.json")
        if not os.path.isfile(up_file):
            raise ConanException(
                "[dav2d] upstream_test_result.json missing from package; "
                "upstream tests did not run in build()")
        with open(up_file, encoding="utf-8") as handle:
            up_result = json.load(handle)
        print("HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(up_result), flush=True)
        if up_result.get("status") != "passed":
            raise ConanException(
                "[dav2d] upstream tests not passed: %s" % json.dumps(up_result))

    @staticmethod
    def _parse_consumer_result(out, rc, exe):
        """Parse the real assertion counters from the test binary output.

        The binary prints one [ok]/[FAIL] line per assertion plus a final
        'dav2d 0.0.1: P/P assertions passed' tally; both sources must agree
        before the run counts as passed (exit 0 alone is not enough).
        """
        tally = re.search(r"dav2d 0\.0\.1:\s*(\d+)/(\d+)\s+assertions passed", out)
        oks = len(re.findall(r"^\[ok\]", out, re.M))
        fails = len(re.findall(r"^\[FAIL\]", out, re.M))
        if tally:
            passed_count, discovered = int(tally.group(1)), int(tally.group(2))
        else:
            passed_count, discovered = oks, oks + fails
        ok = (rc == 0 and tally is not None and fails == 0
              and discovered > 0 and passed_count == discovered
              and oks == discovered)
        return {
            "executed": True,
            "passed": ok,
            "command": exe,
            "discovered": discovered,
            "passedCount": passed_count,
        }

    def _compiler_command(self, compiler):
        if str(self.settings.os) == "OHOS" and self._is_shell_script(compiler):
            shell = os.environ.get("CONFIG_SHELL") or os.environ.get("SHELL") or "/bin/sh"
            return "{} {}".format(shlex.quote(shell), shlex.quote(compiler))
        return shlex.quote(compiler)

    @staticmethod
    def _is_shell_script(path):
        try:
            with open(path, "rb") as handle:
                return handle.read(32).startswith(b"#!")
        except OSError:
            return False
