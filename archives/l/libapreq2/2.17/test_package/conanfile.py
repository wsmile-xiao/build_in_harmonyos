#!/usr/bin/env python3
"""Conan test_package — libapreq2 2.17 consumer test."""

import json
import os
import shutil
import subprocess

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, cmake_layout


class Libapreq2TestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def _usable_compiler(self, configured, fallbacks):
        # 2026-09-26 preflight: test_package CMake fails with
        # `CMAKE_C_COMPILER: /data/service/hnp/bin/clang ... is not able
        # to compile`. The conf/profile compiler path is baked from the
        # remote apr build host and is inaccessible on-device. Probe
        # executability via --version (libnewt/0.52.25 precedent: probe
        # then adapt); fall back to PATH lookup. Only file existence is
        # not enough: the stale path may exist as a dangling reference.
        def _works(path):
            try:
                if not path or not os.path.isfile(path):
                    return False
                if not os.access(path, os.X_OK):
                    return False
                proc = subprocess.run(
                    [path, "--version"],
                    stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                    text=True, timeout=30)
                return proc.returncode == 0
            except Exception:
                return False
        if _works(configured):
            return configured
        if configured:
            self.output.warning(
                "conf compiler '%s' unusable; falling back to PATH"
                % configured)
        for name in fallbacks:
            found = shutil.which(name)
            if _works(found):
                return found
        # Last resort: first PATH hit even without --version probe.
        for name in fallbacks:
            found = shutil.which(name)
            if found:
                return found
        return configured or fallbacks[0]

    def generate(self):
        from conan.tools.cmake import CMakeDeps, CMakeToolchain
        CMakeDeps(self).generate()
        tc = CMakeToolchain(self)
        try:
            _exes = self.conf.get("tools.build:compiler_executables",
                                  default=None)
        except Exception:
            _exes = None
        if not isinstance(_exes, dict):
            _exes = {}
        _c = self._usable_compiler(_exes.get("c"), ("clang", "cc", "gcc"))
        _cxx = self._usable_compiler(
            _exes.get("cpp") or _exes.get("cxx") or _exes.get("c"),
            ("clang++", "c++", "g++"))
        if _c:
            tc.cache_variables["CMAKE_C_COMPILER"] = _c
            self.output.info("test_package CMAKE_C_COMPILER=%s" % _c)
        if _cxx:
            tc.cache_variables["CMAKE_CXX_COMPILER"] = _cxx
            self.output.info("test_package CMAKE_CXX_COMPILER=%s" % _cxx)
        tc.generate()
        # The cache_variables pin alone may not override a stale absolute
        # path already written by the profile (zydis/4.1.1 precedent), so
        # patch the generated toolchain file byte-for-byte when the
        # configured path is unusable and the resolved one works, and
        # export CC/CXX to the build scope to cover the toolchain script.
        try:
            _c_old = _exes.get("c")
            _cxx_old = (_exes.get("cpp") or _exes.get("cxx")
                        or _exes.get("c"))
            _pairs = []
            if (_c_old and _c and _c_old != _c
                    and not os.path.isfile(_c_old)
                    and os.path.isfile(_c)):
                _pairs.append((_c_old, _c))
            if (_cxx_old and _cxx and _cxx_old != _cxx
                    and not os.path.isfile(_cxx_old)
                    and os.path.isfile(_cxx)):
                _pairs.append((_cxx_old, _cxx))
            if _pairs:
                _gf = getattr(self, "generators_folder", None)
                _tc_path = (os.path.join(_gf, "conan_toolchain.cmake")
                            if _gf else None)
                if _tc_path and os.path.isfile(_tc_path):
                    with open(_tc_path, "r", encoding="utf-8",
                              errors="replace") as _fh:
                        _text = _fh.read()
                    _orig = _text
                    for _old, _new in _pairs:
                        _text = _text.replace(_old, _new)
                    if _text != _orig:
                        with open(_tc_path, "w", encoding="utf-8") as _fh:
                            _fh.write(_text)
                        self.output.info(
                            "fixed stale compiler in %s" % _tc_path)
                try:
                    from conan.tools.env import Environment as _Env
                    _e = _Env()
                    for _old, _new in _pairs:
                        if _old == _c_old and _new == _c:
                            _e.define("CC", _c)
                        if _old == _cxx_old and _new == _cxx:
                            _e.define("CXX", _cxx)
                    _e.vars(self, scope="build").save_sh(
                        "hmbs_test_compiler")
                except Exception as _exc:
                    self.output.warning(
                        "test compiler env export failed: %r" % _exc)
        except Exception as _exc:
            self.output.warning("test toolchain fix skipped: %r" % _exc)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        if can_run(self):
            tmpdir = os.environ.get("TMPDIR", "") or os.environ.get("TMP", "")
            if tmpdir:
                for key in ("TMPDIR", "TMP", "TEMP"):
                    os.environ[key] = tmpdir
            binary = os.path.join(self.cpp.build.bindirs[0], "test_apreq2")
            # Deterministic source: the single RESULT line printed by
            # test_apreq2.c (format: RESULT: <passed>/<total> passed).
            # Capture via StringIO so counts come from real output, not
            # hardcoded constants; the binary output is also streamed to
            # the preflight log by self.run.
            import io
            import re
            buf = io.StringIO()
            self.run(binary, env="conanrun", stdout=buf, stderr=buf)
            text = buf.getvalue() or ""
            match = re.search(r"RESULT:\s*(\d+)\s*/\s*(\d+)\s*passed", text)
            if not match:
                raise AssertionError(
                    "test_apreq2 RESULT line not found in output: %r" % text[-500:])
            passed_count = int(match.group(1))
            discovered = int(match.group(2))
            if not (discovered >= 0 and passed_count >= 0
                    and passed_count <= discovered):
                raise AssertionError(
                    "inconsistent RESULT counts: %r" % text[-200:])
            marker = {
                "executed": True,
                "passed": passed_count == discovered,
                "command": "./test_apreq2",
                "discovered": discovered,
                "passedCount": passed_count,
            }
            self.output.info("HMBS_TEST_PACKAGE_RESULT=%s" % json.dumps(marker, sort_keys=True))
            if passed_count != discovered:
                raise AssertionError(
                    "test_apreq2 failed: %d/%d passed" % (passed_count, discovered))
