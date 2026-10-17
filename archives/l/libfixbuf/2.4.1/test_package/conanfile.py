#!/usr/bin/env python3
"""Conan test_package - libfixbuf 2.4.1.

Builds test_libfixbuf.c against the packaged library (R34: real
fbInfoModel/fbSession/fbTemplate API calls, no network) and re-emits
the result as HMBS machine evidence. Counters are parsed from the
test binary output, never hardcoded. Upstream 2.4.1 ships zero test
suites (audited, see MANIFEST.yml), so the upstream marker is the
honest no_tests/0 result.

OHOS note (2026-09-19 preflight): CMake's project() compiler check
fails on the worker (`System is unknown to cmake, Platform/HarmonyOS`
+ `CMAKE_C_COMPILER: /data/service/hnp/bin/clang` broken). The test
is a single TU, so compile it directly with the conf-provided C
compiler (gumbo-parser/0.10.1 test_package precedent), bypassing CMake
entirely. No test logic is skipped; the same 5 assertions run.
"""
import json
import os
import re
import shlex
import subprocess

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.build import can_run
from conan.tools.layout import basic_layout

_RESULT_RE = re.compile(r"FIXBUF_TEST assertions=(\d+) failures=(\d+)")


class TestPackageConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        basic_layout(self)

    def _build_type_flags(self):
        return {
            "Debug": ["-O0", "-g"],
            "Release": ["-O2"],
            "RelWithDebInfo": ["-O2", "-g"],
            "MinSizeRel": ["-Os"],
        }.get(str(self.settings.build_type), ["-O2"])

    def _collect_flags(self):
        includes, libdirs, libs, defines = [], [], [], []

        def _add_unique(seq, item):
            if item and item not in seq:
                seq.append(item)

        try:
            host_deps = self.dependencies.host.values()
        except Exception:
            host_deps = []
        for dep in host_deps:
            try:
                infos = [dep.cpp_info]
                try:
                    infos.extend(dep.cpp_info.components.values())
                except Exception:
                    pass
            except Exception:
                continue
            for info in infos:
                try:
                    for d in getattr(info, "includedirs", []):
                        _add_unique(includes, d)
                except Exception:
                    pass
                try:
                    for d in getattr(info, "libdirs", []):
                        _add_unique(libdirs, d)
                except Exception:
                    pass
                try:
                    for lib in getattr(info, "libs", []):
                        _add_unique(libs, lib)
                except Exception:
                    pass
                try:
                    for lib in getattr(info, "system_libs", []):
                        _add_unique(libs, lib)
                except Exception:
                    pass
                try:
                    for dv in getattr(info, "defines", []):
                        _add_unique(defines, dv)
                except Exception:
                    pass
        return includes, libdirs, libs, defines

    def _select_cc(self):
        """Probe ordered candidates, return first executable CC.

        2026-09-19 round 6: conf c is /data/service/hnp/bin/clang but the
        shell reports it `inaccessible or not found` (exit 127), the same
        fingerprint the main recipe fixed in its eleventh round via
        _hmbs_cc_probe. Blindly trusting conf therefore repeats the
        failure; probe conf c / env CC / OHOS SDK clang / PATH clang with
        `--version` (no shell) and use the first that executes.
        """
        import glob as _gg

        try:
            _conf = self.conf.get("tools.build:compiler_executables",
                                  default={}) or {}
        except Exception:
            _conf = {}
        _sdk_clang = None
        try:
            _bins = _gg.glob(
                "/data/service/hnp/ohos-sdk*/ohos/native/llvm/bin/clang")
            if _bins and os.path.isfile(_bins[0]):
                _sdk_clang = _bins[0]
        except Exception:
            pass
        _cands = []
        for _c in (_conf.get("c"), os.environ.get("CC"),
                   _sdk_clang, "clang"):
            if _c and _c not in _cands:
                _cands.append(_c)

        def _works(cmd):
            try:
                _p = subprocess.run(cmd.split() + ["--version"],
                                    capture_output=True, text=True,
                                    timeout=30)
                return _p.returncode == 0
            except Exception:
                return False

        for _c in _cands:
            if _works(_c):
                try:
                    self.output.info("TEST_CC_SELECT | cc=%s" % _c)
                except Exception:
                    pass
                return _c
        raise ConanInvalidConfiguration(
            "no accessible C compiler among: %s" % ", ".join(_cands))

    def build(self):
        cc = self._select_cc()
        includes, libdirs, libs, defines = self._collect_flags()
        src = os.path.join(self.source_folder, "test_libfixbuf.c")
        out = os.path.join(self.build_folder, "test_libfixbuf")
        cmd = (
            [cc]
            + self._build_type_flags()
            + [("-I" + d) for d in includes if os.path.isdir(d)]
            + [("-D" + d) for d in defines]
            + [src, "-o", out]
            + [("-L" + d) for d in libdirs if os.path.isdir(d)]
            + [("-l" + lib) for lib in libs]
        )
        self.output.info("TEST_CC | " + " ".join(shlex.quote(c) for c in cmd))
        self.run(" ".join(shlex.quote(c) for c in cmd))

    def test(self):
        if not can_run(self):
            raise ConanException("can_run is False: native OHOS run expected")
        exe = os.path.join(self.build_folder, "test_libfixbuf")
        # L0d needs an explicit self.run(); self.run(stdout=True) returns
        # None on some Conan 2.x builds, so capture via subprocess for
        # parsing (c4log precedent) while keeping self.run as the gate.
        self.run(exe, env="conanrun")
        proc = subprocess.run([exe], capture_output=True, text=True, timeout=60)
        text = (proc.stdout or "") + (proc.stderr or "")
        print(text)
        if proc.returncode != 0:
            raise ConanException(f"test_libfixbuf exit {proc.returncode}")
        match = _RESULT_RE.search(text)
        if not match:
            raise ConanException("test_libfixbuf did not print FIXBUF_TEST summary")
        discovered = int(match.group(1))
        failures = int(match.group(2))
        if discovered <= 0:
            raise ConanException("test_libfixbuf reported zero assertions")
        passed_count = discovered - failures
        tp_result = {
            "executed": True,
            "passed": failures == 0,
            "command": exe,
            "discovered": discovered,
            "passedCount": passed_count,
        }
        print("HMBS_TEST_PACKAGE_RESULT=" + json.dumps(tp_result))
        ut_result = {
            "status": "no_tests",
            "framework": "autotools",
            "command": "make check",
            "discovered": 0,
            "executed": 0,
            "passed": 0,
            "failed": 0,
            "skipped": 0,
            "reason": (
                "libfixbuf-2.4.1.tar.gz audited (sha256 "
                "8c535d48120b08df1731de709f2dbd2ba8bce568ad64cac34826102caf594d84): "
                "no tests/ or test/ directory and no *test* source files anywhere "
                "in the tree; Makefile.am/SUBDIRS only src+include with no TESTS, "
                "check_PROGRAMS or check-local targets; configure.ac has no test "
                "macros; make check is automake's default empty target, so zero "
                "upstream cases exist to run"
            ),
        }
        print("HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(ut_result))
        if failures != 0:
            raise ConanException("test_libfixbuf reported failures")
