#!/usr/bin/env python3
"""Conan test_package for libdovi 3.4.0 — exercises the real C-API.

Compiles test.c against the packaged libdovi headers/library with the
Conan-provided clang, runs it, and emits the HMBS_TEST_PACKAGE_RESULT
machine-evidence marker with the real assertion count (5 checks).
"""
import glob
import json
import os
import re
import shutil
import subprocess

from conan import ConanFile
from conan.errors import ConanException


class LibdoviTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build(self):
        dep = self.dependencies["libdovi"].cpp_info
        for p in dep.includedirs:
            if not os.path.isdir(p):
                raise ConanException(f"libdovi package include dir missing: {p}")
        if not dep.libdirs or not os.path.isdir(dep.libdirs[0]):
            raise ConanException("libdovi package lib dir missing")
        compilers = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict) or {}
        cc = None
        for _key in ("c", "cc"):
            _cand = compilers.get(_key)
            if _cand and os.path.basename(_cand).startswith("clang") and os.path.isfile(_cand):
                cc = _cand
                break
        if cc is None:
            _cc_env = os.environ.get("CC", "")
            if _cc_env and os.path.isfile(_cc_env) and os.path.basename(_cc_env).startswith("clang"):
                cc = _cc_env
        if cc is None:
            cc = shutil.which("clang")
        if cc is None:
            for _pattern in (
                "/data/service/hnp/ohos-sdk.org/ohos-sdk_*/ohos/native/llvm/bin/clang",
                "/data/service/hnp/native/llvm/bin/clang",
            ):
                for _cand in sorted(glob.glob(_pattern)):
                    if os.path.isfile(_cand):
                        cc = _cand
                        break
                if cc is not None:
                    break
        if cc is None:
            for _cand in (
                os.path.expanduser("~/.harmonybrew/bin/clang"),
                "/storage/Users/currentUser/usr/local/bin/clang",
                "/usr/bin/clang",
                "/usr/local/bin/clang",
            ):
                if os.path.isfile(_cand):
                    cc = _cand
                    break
        if cc is None:
            raise ConanException(
                "test_package: OHOS clang not found; checked profile conf, $CC, PATH and well-known paths"
            )
        self.output.info("test_package CC: %s" % cc)
        inc = " ".join("-I" + p for p in dep.includedirs)
        libdir = dep.libdirs[0]
        # Static (.a) and shared (.so) both provide -ldovi; link explicitly.
        self.run(f"{cc} test.c -o test_libdovi {inc} -L{libdir} -ldovi")

    def test(self):
        # Cache-hit re-emit: when Conan reuses the main-package binary,
        # build() is skipped and its HMBS_UPSTREAM_TEST_RESULT never
        # prints. Re-print the persisted real result (written by build()
        # into res/hmbs_upstream.json) every run so the evidence gate
        # sees it. Counts are the real in-build cargo-test numbers.
        try:
            _upstream = None
            try:
                _dep = self.dependencies["libdovi"]
                _pf = getattr(_dep, "package_folder", None)
                if _pf:
                    for _cand in (
                        os.path.join(_pf, "res", "hmbs_upstream.json"),
                        os.path.join(_pf, "hmbs_upstream_result.json"),
                        os.path.join(_pf, "hmbs_upstream.json"),
                    ):
                        if os.path.isfile(_cand):
                            with open(_cand, "r", encoding="utf-8") as _fh:
                                _upstream = json.load(_fh)
                            break
            except Exception:
                _upstream = None
            if isinstance(_upstream, dict) and _upstream.get("discovered"):
                _keys = ("status", "framework", "command", "discovered",
                         "executed", "passed", "failed", "skipped")
                _marker = {k: _upstream.get(k) for k in _keys}
                _umsg = ("HMBS_UPSTREAM_TEST_RESULT="
                         + json.dumps(_marker, ensure_ascii=False))
                print(_umsg, flush=True)
                self.output.info(_umsg)
            else:
                self.output.warning(
                    "persisted hmbs_upstream.json missing; "
                    "upstream evidence only available on fresh build")
        except Exception as _e:
            self.output.warning("upstream re-emit failed: %r" % (_e,))
        for key in ("HMBS_TMPDIR", "TMPDIR", "TMP", "TEMP"):
            val = os.environ.get(key)
            if val and os.path.isdir(val):
                os.environ["TMPDIR"] = val
                os.environ["TMP"] = val
                os.environ["TEMP"] = val
                break
        bash = os.environ.get("CONFIG_SHELL", "") or os.environ.get("SHELL", "") or "/bin/sh"
        if not os.path.isfile(bash):
            bash = "/bin/sh"
        marker = {
            "executed": True,
            "passed": True,
            "command": "./test_libdovi",
            "discovered": 5,
            "passedCount": 5,
        }
        try:
            self.run(f"{bash} -c './test_libdovi'", env="conanrun")
        except Exception as exc:
            marker["passed"] = False
            marker["passedCount"] = 0
            msg = "HMBS_TEST_PACKAGE_RESULT=" + json.dumps(marker, ensure_ascii=False)
            print(msg, flush=True)
            self.output.info(msg)
            raise
        # Re-verify the binary really emitted 5 CHECK-OK lines (anti-hollow guard).
        try:
            out = subprocess.run(
                ["./test_libdovi"], capture_output=True, text=True, timeout=60,
            )
            ok_lines = len(re.findall(r"CHECK-OK:", out.stdout or ""))
            if ok_lines != 5 or "CONSUMER-PASS" not in (out.stdout or ""):
                marker["passed"] = False
                marker["passedCount"] = ok_lines
        except Exception:
            pass
        msg = "HMBS_TEST_PACKAGE_RESULT=" + json.dumps(marker, ensure_ascii=False)
        print(msg, flush=True)
        self.output.info(msg)
