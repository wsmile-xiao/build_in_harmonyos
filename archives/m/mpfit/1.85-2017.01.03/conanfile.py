#!/usr/bin/env python3
"""Conan recipe for mpfit 1.85-2017.01.03 — Makefile build system.

mpfit is MINPACK-1 Levenberg-Marquardt least-squares fitting library in C
(Craig Markwardt, Argonne MINPACK-1 port). Upstream C implementation
(cmpfit) ships mpfit.c/mpfit.h + Makefile building libmpfit.a and the
upstream test binary testmpfit (5 driver fits). This recipe builds the
static library and runs the upstream test suite in build().

Version mapping (honest): task directory version 1.85-2017.01.03 is the
Debian/IDL snapshot version. The C source packaged here is the upstream
MINPACK C implementation at MPFIT_VERSION 1.5 (vendored copy of the
wisc.edu cmpfit distribution, same mpfit.c/mpfit.h). Official upstream:
https://pages.physics.wisc.edu/~craigm/idl/cmpfit.html
(wisc.edu single-host is unreachable from some networks, so this recipe
uses a GitHub-hosted vendored copy with verified sha256; official URL
kept in notes.md for traceability).
Build: make -j1 in cmpfit/ subdir (R9). Upstream test: ./testmpfit.
"""

import json
import os
import re
import shutil
import subprocess

from conan import ConanFile
from conan.tools.files import copy, export_conandata_patches, get
from conan.tools.layout import basic_layout


class MpfitConan(ConanFile):
    name = "mpfit"
    version = "1.85-2017.01.03"
    description = "MINPACK-1 Levenberg-Marquardt least-squares fitting library in C."
    license = "BSD-2-Clause"
    homepage = "https://pages.physics.wisc.edu/~craigm/idl/cmpfit.html"
    url = ""
    topics = ("mpfit", "minpack", "least-squares", "fitting")

    package_type = "library"
    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}

    def config_options(self):
        if self.settings.os == "Windows":
            del self.options.fPIC

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def _resolve_tool(self, key, fallbacks):
        """conf path wins only if the file exists, else PATH lookup."""
        try:
            compilers = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)
        except Exception:
            compilers = {}
        cand = (compilers or {}).get(key)
        if cand and os.path.isfile(cand):
            return cand
        for fb in fallbacks:
            w = shutil.which(fb)
            if w:
                if cand:
                    self.output.info("compiler fallback: conf %s=%s missing, using %s" % (key, cand, w))
                return w
        if cand:
            return cand
        return fallbacks[0]

    def build(self):
        src_cmpfit = os.path.join(self.source_folder, "cmpfit")
        if not os.path.isfile(os.path.join(src_cmpfit, "mpfit.c")):
            raise RuntimeError("mpfit.c missing in cmpfit/ subdir: %s" % src_cmpfit)
        # R33 + existence fallback: conf path wins only if the file exists,
        # otherwise fall back to PATH lookup (profile may pin a stale path).
        cc = self._resolve_tool("c", ["clang", "cc"])
        ar = self._resolve_tool("ar", ["llvm-ar", "ar"])
        ranlib = self._resolve_tool("ranlib", ["llvm-ranlib", "ranlib"])
        # R9: -j1 only.
        cflags = ""
        if self.options.get_safe("fPIC"):
            cflags = "-fPIC"
        self.run("make CC={cc} AR={ar} RANLIB={ranlib} CFLAGS=\"{cflags}\" -j1".format(
            cc=cc, ar=ar, ranlib=ranlib, cflags=cflags),
                 cwd=src_cmpfit)
        if self.options.shared:
            # Upstream Makefile only builds static; link shared lib explicitly.
            self.run("{cc} -shared -o libmpfit.so mpfit.o -lm".format(cc=cc),
                     cwd=src_cmpfit)
        self._run_upstream_tests(src_cmpfit)

    def _run_upstream_tests(self, src_cmpfit):
        """Run ./testmpfit and emit HMBS_UPSTREAM_TEST_RESULT marker.

        Deterministic counting (single source, no string-count arithmetic):
        each driver prints one line '*** test<name> status = <N>'.
        executed = number of such lines; passed = lines with 1<=N<=8
        (MP_OK_* / MP_MAXITER / MP_FTOL / MP_XTOL / MP_GTOL are success).
        Toybox lesson: also require CHI-SQUARE output present and non-empty,
        otherwise harness is silently skipping.
        """
        discovered = 5  # testlinfit/testquadfit/testquadfix/testgaussfit/testgaussfix
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        exe = os.path.join(src_cmpfit, "testmpfit")
        if not os.path.isfile(exe):
            raise RuntimeError("upstream test binary missing: %s" % exe)
        if os.path.getsize(exe) == 0:
            raise RuntimeError("upstream test binary is empty: %s" % exe)
        proc = subprocess.run(
            [bash, "-c", "./testmpfit"],
            cwd=src_cmpfit,
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            text=True, timeout=600)
        output = proc.stdout or ""
        self.output.info("testmpfit exit=%d bytes=%d" % (proc.returncode, len(output)))
        # Print raw output tail for CI log evidence (keep bounded).
        for line in output.splitlines()[:60]:
            self.output.info("[testmpfit] " + line)
        if not output.strip():
            self._emit_upstream("failed", discovered, 0, 0, proc.returncode, output)
            raise RuntimeError("upstream test produced empty output")
        if "CHI-SQUARE" not in output:
            self._emit_upstream("failed", discovered, 0, 0, proc.returncode, output)
            raise RuntimeError("upstream test output missing CHI-SQUARE (harness may be skipping)")
        status_lines = re.findall(r"^\*\*\* (\w+) status = (-?\d+)", output, re.M)
        executed = len(status_lines)
        passed = sum(1 for _name, code in status_lines if 1 <= int(code) <= 8)
        failed = executed - passed
        if executed != discovered:
            self._emit_upstream("failed", discovered, executed, passed, proc.returncode, output,
                                gaps=[{"count": abs(discovered - executed), "category": "test_failure",
                                       "detail": "expected %d driver status lines, got %d" % (discovered, executed),
                                       "evidence": "testmpfit output status-line count mismatch"}])
            raise RuntimeError("upstream test count mismatch: expected %d got %d" % (discovered, executed))
        status = "passed" if (proc.returncode == 0 and failed == 0 and executed == passed) else "failed"
        self._emit_upstream(status, discovered, executed, passed, proc.returncode, output)
        if status != "passed":
            raise RuntimeError("upstream tests failed: executed=%d passed=%d failed=%d" % (executed, passed, failed))

    def _emit_upstream(self, status, discovered, executed, passed, returncode, output, gaps=None):
        failed = executed - passed
        marker = {
            "status": status,
            "framework": "makefile",
            "command": "make -j1 && ./testmpfit",
            "discovered": discovered,
            "executed": executed,
            "passed": passed,
            "failed": failed,
            "skipped": 0,
        }
        if gaps:
            marker["gaps"] = gaps
        self.output.info("HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(marker, ensure_ascii=False))

    def package(self):
        src_cmpfit = os.path.join(self.source_folder, "cmpfit")
        copy(self, "mpfit.h", src=src_cmpfit, dst=os.path.join(self.package_folder, "include"))
        if self.options.shared:
            copy(self, "libmpfit.so", src=src_cmpfit, dst=os.path.join(self.package_folder, "lib"))
        else:
            copy(self, "libmpfit.a", src=src_cmpfit, dst=os.path.join(self.package_folder, "lib"))
        copy(self, "DISCLAIMER", src=src_cmpfit, dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.libs = ["mpfit"]
        if str(self.settings.os) in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["m"]
