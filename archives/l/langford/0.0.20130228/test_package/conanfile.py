#!/usr/bin/env python3
"""Conan test_package for langford 0.0.20130228.

Layer A: test_langford.sh runs the four installed userspace tools (usage and
         error paths only -- the board hardware is not present).
Layer B: test_spi.cpp is compiled and linked against the installed
         liblangford_spi.a + headers, proving the packaged library is usable.

Emits HMBS markers for CI preflight.
"""
import json
import os
import shlex
import sys

from conan import ConanFile
from conan.errors import ConanException


class LangfordTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"

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
        dep = self.dependencies[self.tested_reference_str]
        pkg = dep.package_folder
        bindir = os.path.join(pkg, "bin")
        util = os.path.join(bindir, "langford_util")
        adc = os.path.join(bindir, "langford_adc_util")
        fsynth = os.path.join(bindir, "langford_rf_fsynth")
        vga = os.path.join(bindir, "langford_rx_rf_bb_vga")
        for path in (util, adc, fsynth, vga):
            if not os.path.isfile(path):
                raise ConanException("installed program not found: %s" % path)

        here = os.path.dirname(os.path.abspath(__file__))
        workdir = os.environ.get("TMPDIR") or os.path.join(os.path.expanduser("~"), "tmp")
        os.makedirs(workdir, exist_ok=True)

        script = os.path.join(here, "test_langford.sh")
        rc = self._run_shell(
            'LANG_UTIL=%s ADC_UTIL=%s FSYNTH=%s VGA=%s TMPDIR=%s sh %s'
            % (shlex.quote(util), shlex.quote(adc), shlex.quote(fsynth),
               shlex.quote(vga), shlex.quote(workdir), shlex.quote(script)))

        # Layer B: consumer linking liblangford_spi.a
        consumer_ok = False
        executables = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict) or {}
        cxx = str(executables.get("cpp") or "c++")
        consumer_src = os.path.join(here, "test_spi.cpp")
        consumer_bin = os.path.join(workdir, "test_langford_spi")
        compile_cmd = " ".join([
            shlex.quote(cxx), "-std=gnu++98", "-O2",
            "-I", shlex.quote(os.path.join(pkg, "include")),
            shlex.quote(consumer_src),
            "-L", shlex.quote(os.path.join(pkg, "lib")), "-llangford_spi",
            "-o", shlex.quote(consumer_bin),
        ])
        rc_c = self._run_shell(compile_cmd, env="conanbuild")
        if rc_c == 0:
            rc_run = self._run_shell(shlex.quote(consumer_bin))
            consumer_ok = (rc_run == 0)

        print("HMBS_TEST_PACKAGE_RESULT=" + json.dumps({
            "executed": True,
            "passed": (rc == 0 and consumer_ok),
            "command": "test_langford.sh + test_spi.cpp",
            "consumer_passed": (16 + 1) if consumer_ok else 0,
            "consumer_total": 16 + 1,
        }))
        print("HMBS_UPSTREAM_TEST_RESULT=" + json.dumps({
            "status": "skipped",
            "reason": "langford ships no tests/ and no make check target",
            "discovered": 0, "executed": 0, "passed": 0, "failed": 0, "skipped": 0,
        }))

        if rc != 0 or not consumer_ok:
            raise ConanException(
                "langford test failed (shell rc=%s, consumer_ok=%s)" % (rc, consumer_ok))
