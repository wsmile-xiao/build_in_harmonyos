#!/usr/bin/env python3
"""Installed-package consumer tests for libsz 1.1.6."""

import glob
import json
import os
import re
import shutil
import subprocess

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout


TEST_EXECUTABLES = ("test_sz_roundtrip", "test_aec_roundtrip")


class LibszTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    test_type = "explicit"
    exports_sources = "CMakeLists.txt", "*.c"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        CMakeDeps(self).generate()
        # Same buildenv scoping as the main recipe: writable tmp root
        # plus SDK linker runtime path for the consumer configure.
        tmp = (os.environ.get("TMPDIR") or os.environ.get("TMP")
               or os.environ.get("TEMP") or "")
        if not tmp or not os.path.isdir(tmp):
            tmp = os.path.join(self.build_folder, "hmbs-tmp")
        try:
            os.makedirs(tmp, exist_ok=True)
        except Exception:
            pass
        for var in ("TMPDIR", "TMP", "TEMP"):
            os.environ[var] = tmp
            try:
                self.buildenv_info.define(var, tmp)
            except Exception:
                pass
        try:
            comp = self.conf.get(
                "tools.build:compiler_executables", default={},
                check_type=dict) or {}
            cc = comp.get("c", "")
            if cc and os.path.isfile(cc):
                res = subprocess.check_output(
                    [cc, "-print-resource-dir"],
                    stderr=subprocess.DEVNULL, text=True,
                    timeout=60).strip()
                if res:
                    libdir = os.path.dirname(os.path.dirname(res))
                    if os.path.isfile(
                            os.path.join(libdir, "libxml2.so.16")):
                        self.buildenv_info.prepend_path(
                            "LD_LIBRARY_PATH", libdir)
        except Exception as exc:
            self.output.warning(
                "test_package SDK libdir lookup failed: {!r}".format(exc))
        tc = CMakeToolchain(self)
        if self.settings.os == "OHOS":
            # Same system mapping as the main recipe (zxc/function2
            # precedent): the consumer project() runs the same compiler
            # detection, so it needs the same Linux/aarch64 mapping and
            # CMake 4.x policy floor. No try-compile bypass.
            tc.variables["CMAKE_SYSTEM_NAME"] = "Linux"
            tc.variables["CMAKE_SYSTEM_PROCESSOR"] = "aarch64"
            tc.variables["CMAKE_POLICY_VERSION_MINIMUM"] = "3.5"
        tc.generate()

    def build(self):
        # Same verified-compiler rewrite as the main recipe: CMake
        # reads conan_toolchain.cmake, so force the probed executables
        # there and on the configure command line.
        tmp = (os.environ.get("TMPDIR") or os.environ.get("TMP")
               or os.environ.get("TEMP") or "")
        run_env = dict(os.environ)
        if tmp:
            run_env["TMPDIR"] = tmp
            run_env["TMP"] = tmp
            run_env["TEMP"] = tmp

        def _runs(cand):
            try:
                proc = subprocess.run(
                    [cand, "--version"], stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT, text=True, timeout=60,
                    env=run_env)
                out = (proc.stdout or "").lower()
                return proc.returncode == 0 and (
                    "clang" in out or "version" in out)
            except Exception:
                return False

        try:
            comp = self.conf.get(
                "tools.build:compiler_executables", default={},
                check_type=dict) or {}
        except Exception:
            comp = {}
        conf_c = comp.get("c", "") or ""
        c_cands = [c for c in (
            shutil.which("clang"), conf_c,
            (shutil.which(os.path.basename(conf_c)) if conf_c else ""),
            "clang") if c]
        cc = next((c for c in c_cands if _runs(c)), conf_c or "clang")
        self.output.info("test_package verified CC=%s" % cc)
        tc_file = os.path.join(
            self.build_folder, "build", "Release", "generators",
            "conan_toolchain.cmake")
        if not os.path.isfile(tc_file):
            hits = glob.glob(os.path.join(
                self.build_folder, "**", "conan_toolchain.cmake"),
                recursive=True)
            tc_file = hits[0] if hits else ""
        if tc_file and os.path.isfile(tc_file):
            try:
                with open(tc_file, "r", encoding="utf-8") as fh:
                    content = fh.read()
                orig = content
                content, n = re.subn(
                    r'set\(\s*CMAKE_C_COMPILER\b[^)]*\)',
                    'set(CMAKE_C_COMPILER "%s")' % cc, content, count=1)
                if n == 0:
                    content += '\nset(CMAKE_C_COMPILER "%s")\n' % cc
                if content != orig:
                    with open(tc_file, "w", encoding="utf-8",
                               newline="\n") as fh:
                        fh.write(content)
                    self.output.info(
                        "test_package rewrote CC=%s in %s" % (cc, tc_file))
            except Exception as exc:
                self.output.warning("test_package rewrite failed: %r" % exc)
        cmake = CMake(self)
        cmake.configure(variables={"CMAKE_C_COMPILER": cc})
        cmake.build()

    def test(self):
        if not can_run(self):
            raise ConanException("libsz test_package consumers cannot run here")
        for name in TEST_EXECUTABLES:
            executable = os.path.join(self.cpp.build.bindirs[0], name)
            if not os.path.isfile(executable):
                raise ConanException(f"test executable missing: {executable}")
            # self.run raises on a non-zero exit, so the marker below is
            # only emitted when the consumer really passed: each program
            # prints one LIBSZ_TEST ... PASS line and returns non-zero on
            # any failed internal check.
            self.run(f'"{executable}"', env="conanrun")
        marker = {
            "executed": True,
            "passed": True,
            "command": "test_sz_roundtrip && test_aec_roundtrip",
            "discovered": 2,
            "passedCount": 2,
        }
        _msg = ("HMBS_TEST_PACKAGE_RESULT="
                + json.dumps(marker, ensure_ascii=False))
        # Dual-channel emit: HMBS scrapes raw stdout.
        print(_msg, flush=True)
        self.output.info(_msg)
        # Cache-hit re-emit: when Conan reuses the main-package binary,
        # build() is skipped and its HMBS_UPSTREAM_TEST_RESULT never
        # prints. Re-print the persisted real result (written by build()
        # into package res/hmbs_upstream.json) every run so the evidence
        # gate sees it. Counts are the real in-build ctest numbers.
        try:
            _upstream = None
            _pkg_name = (self.tested_reference_str.split("/")[0]
                         if "/" in self.tested_reference_str else "libsz")
            try:
                _dep = self.dependencies[_pkg_name]
                _pf = getattr(_dep, "package_folder", None)
                if _pf:
                    _cand = os.path.join(_pf, "res", "hmbs_upstream.json")
                    if os.path.isfile(_cand):
                        with open(_cand, "r", encoding="utf-8") as _fh:
                            _upstream = json.load(_fh)
            except Exception:
                _upstream = None
            if isinstance(_upstream, dict) and _upstream.get("discovered"):
                _umsg = ("HMBS_UPSTREAM_TEST_RESULT="
                         + json.dumps(_upstream, ensure_ascii=False))
                print(_umsg, flush=True)
                self.output.info(_umsg)
            else:
                self.output.warning(
                    "persisted hmbs_upstream.json missing; "
                    "upstream evidence only available on fresh build")
                raise ConanException(
                    "persisted hmbs_upstream.json missing in package res/; "
                    "need fresh build with upstream ctest")
        except Exception as _e:
            from conan.errors import ConanException as _CE
            if isinstance(_e, _CE):
                raise
            self.output.warning("upstream re-emit failed: %r" % (_e,))
