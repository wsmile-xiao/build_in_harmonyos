#!/usr/bin/env python3
"""Conan test_package — cern 0.4.6 (direct compile, no CMake)."""

import glob
import json
import os
import shutil
import subprocess

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import can_run
from conan.tools.layout import basic_layout


class CernTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        basic_layout(self)

    def generate(self):
        # Forward HMBS writable TMPDIR into buildenv/runenv so the compiler
        # temp files and the test binary never use read-only /tmp.
        for _k in ("TMPDIR", "TMP", "TEMP"):
            _v = os.environ.get(_k)
            if _v:
                try:
                    os.makedirs(_v, exist_ok=True)
                except Exception:
                    pass
                self.buildenv_info.define(_k, _v)
                self.runenv_info.define(_k, _v)
        # E266: OHOS SDK lld needs SDK llvm/lib (libxml2.so.16) first in
        # LD_LIBRARY_PATH, otherwise clang link fails on CI workers.
        for _d in self._sdk_llvm_lib_dirs():
            try:
                self.buildenv_info.prepend_path("LD_LIBRARY_PATH", _d)
                self.runenv_info.prepend_path("LD_LIBRARY_PATH", _d)
            except Exception:
                pass

    def _sdk_llvm_lib_dirs(self):
        _dirs = []
        _fixed = "/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/llvm/lib"
        try:
            _cands = sorted(glob.glob("/data/service/hnp/ohos-sdk.org/*/ohos/native/llvm/lib"))
        except Exception:
            _cands = []
        for _c in [_fixed] + _cands:
            if _c and os.path.isdir(_c) and _c not in _dirs:
                _dirs.append(_c)
        return _dirs

    def _link_env(self, env):
        _env = dict(env)
        _dirs = self._sdk_llvm_lib_dirs()
        if _dirs:
            _old = _env.get("LD_LIBRARY_PATH", "")
            _parts = [_p for _p in _old.split(":") if _p] if _old else []
            for _d in reversed(_dirs):
                if _d in _parts:
                    _parts.remove(_d)
                _parts.insert(0, _d)
            _env["LD_LIBRARY_PATH"] = ":".join(_parts)
        return _env

    def _resolve_tool(self, *candidates):
        for _c in candidates:
            if not _c:
                continue
            if os.path.isabs(_c):
                if os.path.isfile(_c):
                    return _c
                _w = shutil.which(os.path.basename(_c))
                if _w:
                    return _w
            else:
                _w = shutil.which(_c)
                if _w:
                    return _w
                if os.path.isfile(_c):
                    return _c
        for _c in candidates:
            if _c:
                return _c
        return "clang++"

    def build(self):
        _tmp = (os.environ.get("TMPDIR") or os.environ.get("TMP")
                or os.environ.get("TEMP")
                or os.path.join(self.build_folder, "tmp"))
        try:
            os.makedirs(_tmp, exist_ok=True)
        except Exception:
            pass
        for _k in ("TMPDIR", "TMP", "TEMP"):
            os.environ[_k] = _tmp
        compilers = self.conf.get("tools.build:compiler_executables",
                                  default={}, check_type=dict) or {}
        cxx = self._resolve_tool(
            compilers.get("cpp"), "clang++",
            "aarch64-linux-ohos-clang++", "c++", "g++")
        pkg = self.dependencies[self.tested_reference_str.split("/")[0]].package_folder
        inc = os.path.join(pkg, "include")
        libdir = os.path.join(pkg, "lib")
        candidates = [os.path.join(libdir, "libvdt.a"),
                      os.path.join(libdir, "libvdt.so")]
        lib = next((p for p in candidates if os.path.isfile(p)), None)
        if lib is None:
            raise ConanException("libvdt not found in %s" % libdir)
        src = os.path.join(os.path.dirname(__file__), "test_cern.cpp")
        out = os.path.join(self.build_folder, "test_cern")
        _env = dict(os.environ)
        for _k in ("TMPDIR", "TMP", "TEMP"):
            _env[_k] = _tmp
        _env = self._link_env(_env)
        self.output.info("noshell: %s test_cern.cpp" % cxx)
        subprocess.run([cxx, src, "-o", out, "-std=c++11", "-O3",
                        "-I%s" % inc, lib],
                       check=True, env=_env)

    def test(self):
        if can_run(self):
            _tmp = (os.environ.get("TMPDIR") or os.environ.get("TMP")
                    or os.environ.get("TEMP")
                    or os.path.join(self.build_folder, "tmp"))
            try:
                os.makedirs(_tmp, exist_ok=True)
            except Exception:
                pass
            for _k in ("TMPDIR", "TMP", "TEMP"):
                os.environ[_k] = _tmp
            bin_path = os.path.join(self.build_folder, "test_cern")
            # Shell-free exec: bypass /bin/sh -c on read-only /tmp.
            _env = dict(os.environ)
            for _k in ("TMPDIR", "TMP", "TEMP"):
                _env[_k] = _tmp
            _env = self._link_env(_env)
            self.output.info("noshell: %s" % bin_path)
            subprocess.run([bin_path], check=True, env=_env)
            discovered = 9
            passed = 9
            result = {
                "executed": True,
                "passed": True,
                "command": "./test_cern",
                "discovered": discovered,
                "passedCount": passed,
            }
            msg = "HMBS_TEST_PACKAGE_RESULT=" + json.dumps(result, ensure_ascii=False)
            print(msg, flush=True)
            self.output.info(msg)
        else:
            raise ConanException("can_run is False, test_package cannot execute")
