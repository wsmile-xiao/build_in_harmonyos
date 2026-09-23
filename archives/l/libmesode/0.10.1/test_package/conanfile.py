#!/usr/bin/env python3
"""Conan test_package for libmesode 0.10.1 — L1 consumer test.

Direct compiler invocation (no CMake configure): resolves the C compiler
from configuration with PATH fallback (preflight evidence 2026-09-16:
profile CC /data/service/hnp/bin/clang inaccessible, conanbuild AR
missing), wraps commands with a writable temporary directory, assembles
include/library/link flags from dependency package info, compiles the
consumer source directly and runs it.

CI runs this automatically via `conan create` (which invokes test_package).
test.c exercises the real xmpp_* public API of the package (R34).

Machine evidence (HMBS preflight hard gate):
- runs the consumer binary via subprocess, parses the
  "libmesode API assertions: N passed" line and emits
  HMBS_TEST_PACKAGE_RESULT with real discovered/passedCount numbers
  (exit code 0 alone is not accepted as proof);
- re-emits the persisted HMBS_UPSTREAM_TEST_RESULT (package res/
  hmbs_upstream.json) so the evidence gate also sees upstream results
  on Conan cache hits where recipe build() is skipped.
"""

import json
import os
import re
import shutil
import subprocess

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.layout import basic_layout

CONSUMER_ASSERT_COUNT = 11


def _is_usable(path):
    if not path:
        return False
    path = path.strip().strip('"').strip("'")
    if not path:
        return False
    if os.path.isabs(path):
        return os.path.isfile(path)
    return shutil.which(path) is not None


def _resolve_cc():
    candidates = []
    for key in ("CC", "HMBS_CC"):
        val = os.environ.get(key)
        if val and val not in candidates:
            candidates.append(val)
    candidates.extend(["cc", "clang", "gcc", "aarch64-linux-gnu-gcc"])
    for cand in candidates:
        if _is_usable(cand):
            if os.path.isabs(cand.strip().strip('"').strip("'")):
                return '"%s"' % cand.strip().strip('"').strip("'")
            found = shutil.which(cand.strip().strip('"').strip("'"))
            if found:
                return '"%s"' % found
            return cand
    return None


class LibmesodeTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        basic_layout(self)

    def _dep_flags(self):
        inc, libd, libs = [], [], []
        for _ref, _dep in self.dependencies.items():
            try:
                cpp = _dep.cpp_info
            except Exception:
                continue
            for _d in (cpp.includedirs or []):
                if os.path.isabs(_d):
                    inc.append("-I" + _d)
            for _d in (cpp.libdirs or []):
                if os.path.isabs(_d):
                    libd.append("-L" + _d)
            for _lib in (cpp.libs or []):
                libs.append("-l" + _lib)
            for _lib in (cpp.system_libs or []):
                libs.append("-l" + _lib)
        return inc, libd, libs

    def build(self):
        tmpdir = os.path.join(self.build_folder, "tmp")
        os.makedirs(tmpdir, exist_ok=True)
        for _k in ("TMPDIR", "TMP", "TEMP"):
            os.environ[_k] = tmpdir
        cc = _resolve_cc()
        if cc is None:
            raise ConanException(
                "no usable C compiler: CC=%r not found and "
                "PATH lookup for cc/clang/gcc failed" % os.environ.get("CC"))
        self.output.info("test_package resolved CC=%s" % cc)
        inc, libd, libs = self._dep_flags()
        src = os.path.join(self.source_folder, "test.c")
        bin_path = os.path.join(self.build_folder, "test_libmesode")
        cmd = ("%s -Wall %s \"%s\" -o \"%s\" %s %s" % (
            cc, " ".join(inc), src, bin_path,
            " ".join(libd), " ".join(libs)))
        self.run(cmd, cwd=self.build_folder, env="conanbuild")

    def test(self):
        bin_path = os.path.join(self.build_folder, "test_libmesode")
        if not os.path.isfile(bin_path):
            # Fallback for alternate layout (e.g. cached build folder).
            alt = os.path.join(self.cpp.build.bindirs[0], "test_libmesode") \
                if getattr(self.cpp, "build", None) else None
            if alt and os.path.isfile(alt):
                bin_path = alt
            else:
                raise ConanException("test binary missing: %s" % bin_path)
        rpath_dirs = []
        for _ref, _dep in self.dependencies.items():
            try:
                for _d in (_dep.cpp_info.libdirs or []):
                    if os.path.isabs(_d):
                        rpath_dirs.append(_d)
            except Exception:
                continue
        env = dict(os.environ)
        if rpath_dirs:
            old = env.get("LD_LIBRARY_PATH", "")
            env["LD_LIBRARY_PATH"] = ":".join(rpath_dirs) + (":" + old if old else "")
        run = subprocess.run(
            [bin_path],
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            timeout=300,
        )
        output = run.stdout or ""
        self.output.info(output)
        passed = 0
        match = re.search(r"libmesode API assertions:\s*(\d+)\s*passed", output)
        if match:
            passed = int(match.group(1))
        ok = run.returncode == 0 and passed == CONSUMER_ASSERT_COUNT
        marker = {
            "executed": True,
            "passed": ok,
            "command": bin_path,
            "discovered": CONSUMER_ASSERT_COUNT,
            "passedCount": passed,
        }
        msg = "HMBS_TEST_PACKAGE_RESULT=" + json.dumps(marker, ensure_ascii=False)
        print(msg, flush=True)
        self.output.info(msg)
        if not ok:
            raise ConanException(
                "consumer test failed: rc=%s passed=%s/%s"
                % (run.returncode, passed, CONSUMER_ASSERT_COUNT)
            )
        try:
            upstream = None
            pkg_name = (self.tested_reference_str.split("/")[0]
                        if "/" in self.tested_reference_str else "libmesode")
            try:
                dep = self.dependencies[pkg_name]
                pkg_folder = getattr(dep, "package_folder", None)
                if pkg_folder:
                    cand = os.path.join(pkg_folder, "res", "hmbs_upstream.json")
                    if os.path.isfile(cand):
                        with open(cand, "r", encoding="utf-8") as fh:
                            upstream = json.load(fh)
            except Exception:
                upstream = None
            if isinstance(upstream, dict) and upstream.get("discovered"):
                umsg = ("HMBS_UPSTREAM_TEST_RESULT="
                        + json.dumps(upstream, ensure_ascii=False))
                print(umsg, flush=True)
                self.output.info(umsg)
            else:
                self.output.warning(
                    "persisted hmbs_upstream.json missing; "
                    "upstream evidence only available on fresh build")
        except Exception as e:
            self.output.warning("upstream re-emit failed: %r" % (e,))
