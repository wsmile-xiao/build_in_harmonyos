#!/usr/bin/env python3
"""Conan test_package for cld2 0.0.0-git20150806 — Conan L1 consumer test.

Builds test_cld2 with CMake (CMakeDeps + CMakeToolchain, R33 compliant)
and runs English/French language detection against the packaged library.
"""

import json
import os
import shutil
import subprocess

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.env import VirtualRunEnv
from conan.tools.files import replace_in_file


class Cld2TestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        # readonly_tmp: /tmp is read-only on HarmonyOS. Forward the
        # HMBS-injected writable TMPDIR/TMP/TEMP into buildenv+runenv so
        # CMake configure/build temp files and the ctest/test_bin children
        # spawned in test() never fall back to /tmp.
        for _k in ("TMPDIR", "TMP", "TEMP"):
            _v = os.environ.get(_k)
            if _v:
                try:
                    os.makedirs(_v, exist_ok=True)
                except Exception:
                    pass
                self.buildenv_info.define(_k, _v)
                self.runenv_info.define(_k, _v)
        # Stale-toolchain guard (repo convention, cf. libXext test_package):
        # profile pins /data/service/hnp/bin/clang(++), but that file may
        # not exist on the current worker. CMakeToolchain copies the conf
        # path verbatim into conan_toolchain.cmake, so CMake then fails
        # its compiler check. Resolve to an existing binary (conf path only
        # when isfile, otherwise PATH lookup which hmbs prepends) and force
        # it via cache variables + post-generate toolchain patch.
        CMakeDeps(self).generate()
        tc = CMakeToolchain(self)
        if str(self.settings.get_safe("os")) == "OHOS":
            tc.cache_variables["CMAKE_C_COMPILER"] = self._compiler_executable(
                "c", "clang"
            )
            tc.cache_variables["CMAKE_CXX_COMPILER"] = self._compiler_executable(
                "cpp", "clang++"
            )
        tc.generate()
        if str(self.settings.get_safe("os")) == "OHOS":
            self._patch_cmake_toolchain_compilers()
        VirtualRunEnv(self).generate()

    def build(self):
        # readonly_tmp: keep CMake/temp files off read-only /tmp.
        _tmp = (os.environ.get("TMPDIR") or os.environ.get("TMP")
                or os.environ.get("TEMP")
                or os.path.join(self.build_folder, "tmp"))
        try:
            os.makedirs(_tmp, exist_ok=True)
        except Exception:
            pass
        for _k in ("TMPDIR", "TMP", "TEMP"):
            os.environ[_k] = _tmp
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def _run_noshell(self, args):
        # readonly_tmp: shell-free exec, bypassing /bin/sh -c entirely so
        # dash never creates /tmp/sh*.tmp temp files for this step. This
        # covers the last remaining in-recipe shell invocation in the cld2
        # contribution (the main recipe was de-shelled in an earlier round;
        # test_package's direct binary run was the remaining gap).
        # Semantics preserved: env starts from os.environ (TMPDIR already
        # asserted writable above) plus dependency lib dirs appended to
        # LD_LIBRARY_PATH (a superset of what the former conanrun env gave
        # the loader on Linux); check=True keeps any non-zero exit fatal;
        # the test binary itself prints HMBS_TEST_PACKAGE_RESULT on every
        # invocation, so the machine marker is unchanged.
        _env = dict(os.environ)
        _libpaths = []
        try:
            for _dep in self.dependencies.values():
                _pf = getattr(_dep, "package_folder", None)
                for _d in (getattr(_dep.cpp_info, "libdirs", None) or []):
                    _p = _d if os.path.isabs(_d) else os.path.join(_pf or "", _d)
                    if _p and os.path.isdir(_p):
                        _libpaths.append(_p)
        except Exception:
            pass
        if _libpaths:
            _prev = _env.get("LD_LIBRARY_PATH", "")
            _env["LD_LIBRARY_PATH"] = os.pathsep.join(
                _libpaths + ([_prev] if _prev else []))
        self.output.info("noshell: %s" % " ".join(args))
        subprocess.run(args, check=True, cwd=self.build_folder, env=_env)

    def test(self):
        # readonly_tmp: keep ctest/test_bin temp files off read-only /tmp.
        # generate() already forwarded HMBS TMPDIR via runenv; re-assert
        # os.environ here as a fallback (e.g. build_folder/tmp) so direct
        # children never see an unset TMPDIR.
        _tmp = (os.environ.get("TMPDIR") or os.environ.get("TMP")
                or os.environ.get("TEMP")
                or os.path.join(self.build_folder, "tmp"))
        try:
            os.makedirs(_tmp, exist_ok=True)
        except Exception:
            pass
        for _k in ("TMPDIR", "TMP", "TEMP"):
            os.environ[_k] = _tmp
        if self.conf.get("tools.build:skip_test", default=False, check_type=bool):
            return
        if not can_run(self):
            return
        # Run the declared ctest suite (test_cld2_english + test_cld2_french)
        # so both consumer cases execute as registered in CMakeLists.txt.
        cmake = CMake(self)
        cmake.test()
        # Aggregate consumer run: emits HMBS_TEST_PACKAGE_RESULT with
        # discovered=2/passedCount=2 for the machine gate. Shell-free exec
        # (no /bin/sh -c, no /tmp/sh*.tmp); failures stay fatal via check.
        test_bin = os.path.join(self.build_folder, "test_cld2")
        if not os.path.isfile(test_bin):
            cand = os.path.join(self.cpp.build.bindirs[0], "test_cld2")
            if os.path.isfile(cand):
                test_bin = cand
        self._run_noshell([test_bin])
        # Re-emit the upstream suite verdict AFTER the test commands finish
        # so the marker is produced at the end of test() on every run,
        # including Conan cache hits where build() is skipped. The JSON was
        # produced from actual on-device upstream execution
        # (cld2_unittest_chrome_2 + cld2_unittest_full), never guessed.
        # Dual channel (output.info + print) mirrors the build() marker:
        # the harness scans the stdout tail.
        try:
            for _dep in self.dependencies.values():
                _pf = getattr(_dep, "package_folder", None)
                if not _pf:
                    continue
                _mf = os.path.join(str(_pf), "hmbs_upstream_result.json")
                if os.path.isfile(_mf):
                    with open(_mf, encoding="utf-8") as _fh:
                        _data = json.load(_fh)
                    _marker = {k: _data.get(k) for k in
                               ("status", "framework", "command",
                                "discovered", "executed", "passed",
                                "failed", "skipped")}
                    _line = ("HMBS_UPSTREAM_TEST_RESULT="
                             + json.dumps(_marker, ensure_ascii=False))
                    self.output.info(_line)
                    print(_line, flush=True)
                    break
        except Exception:
            pass

    def _compiler_executable(self, key, fallback_name):
        executables = self.conf.get(
            "tools.build:compiler_executables",
            default={},
            check_type=dict,
        ) or {}
        configured = executables.get(key)
        if configured and os.path.isfile(configured):
            return configured
        found = shutil.which(fallback_name)
        return found or configured or fallback_name

    def _patch_cmake_toolchain_compilers(self):
        toolchain = os.path.join(self.generators_folder, "conan_toolchain.cmake")
        replacements = {
            "/data/service/hnp/bin/clang++": self._compiler_executable(
                "cpp", "clang++"
            ),
            "/data/service/hnp/bin/clang": self._compiler_executable("c", "clang"),
        }
        for old, new in replacements.items():
            replace_in_file(self, toolchain, old, new, strict=False)
