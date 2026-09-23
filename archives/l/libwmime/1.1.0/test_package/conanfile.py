#!/usr/bin/env python3
"""Conan test_package — libwmime 1.1.0 consumer tests.

Builds two real API consumers against the packaged wmime library and runs
them under ctest. CHECK-OK lines feed the HMBS_TEST_PACKAGE_RESULT marker;
exit code alone is not proof.
"""

import json
import os
import re
import shutil
import subprocess

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import can_run
from conan.tools.cmake import CMake, cmake_layout


CONSUMER_BINARIES = ("test_message_build", "test_mime_parse")


class LibwmimeTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    test_type = "explicit"
    exports_sources = "CMakeLists.txt", "test_message_build.cpp", "test_mime_parse.cpp"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        tmp = self._ensure_writable_tmp()
        # readonly_tmp: same as main recipe — persist writable tmp into
        # conanbuild so consumer cmake/clang/ctest never default to /tmp.
        for _key in ("TMPDIR", "TMP", "TEMP", "TEMPDIR"):
            try:
                self.buildenv_info.define(_key, tmp)
            except Exception:
                pass
        from conan.tools.cmake import CMakeDeps, CMakeToolchain

        CMakeDeps(self).generate()
        tc = CMakeToolchain(self)
        # OHOS E092: same as main recipe — alias unknown HarmonyOS platform
        # to Linux (frei0r/ayatana-ido precedent); keeps consumer toolchain
        # consistent with the packaged library. No check/test skipped.
        tc.variables["CMAKE_SYSTEM_NAME"] = "Linux"
        try:
            _exes = self.conf.get("tools.build:compiler_executables",
                                  default=None)
        except Exception:
            _exes = None
        _conf_c = _conf_cxx = None
        if isinstance(_exes, dict):
            _conf_c = _exes.get("c")
            _conf_cxx = (_exes.get("cpp") or _exes.get("cxx")
                         or _exes.get("c"))
        for _key, _conf_val, _bare in (
                ("CMAKE_C_COMPILER", _conf_c, "clang"),
                ("CMAKE_CXX_COMPILER", _conf_cxx, "clang++")):
            if _conf_val and (os.path.sep in str(_conf_val)
                              or "/" in str(_conf_val)):
                try:
                    _ok = (os.path.isfile(str(_conf_val))
                           and os.access(str(_conf_val), os.X_OK))
                except Exception:
                    _ok = False
                if not _ok:
                    self.output.warning(
                        "conf compiler '%s' unusable; falling back to PATH"
                        % _conf_val)
                    _which = shutil.which(_bare)
                    if _which:
                        tc.variables[_key] = _which
        tc.generate()

    def _ensure_writable_tmp(self):
        # Same repo-standard handling as the main recipe (E002): prefer the
        # HMBS-injected writable dir (HMBS_TMPDIR newest standard, then
        # TMPDIR/TMP/TEMP). Hardened this round: create + write-probe
        # injected paths instead of requiring pre-existing isdir, so a fresh
        # worker tmpdir is adopted; fall back to a build-local dir.
        # No hardlink/chmod/symlink use (worker hardlink=0/chmod=0).
        tmp = None
        for key in ("HMBS_TMPDIR", "TMPDIR", "TMP", "TEMP"):
            candidate = os.environ.get(key)
            if not candidate:
                continue
            try:
                os.makedirs(candidate, exist_ok=True)
            except OSError:
                continue
            try:
                if not os.path.isdir(candidate):
                    continue
                probe = os.path.join(candidate, ".hmbs-write-probe")
                with open(probe, "w", encoding="utf-8") as handle:
                    handle.write("hmbs")
                try:
                    os.remove(probe)
                except OSError:
                    pass
                tmp = candidate
                break
            except OSError:
                continue
        if not tmp:
            fallback_base = getattr(self, "build_folder", None) or os.getcwd()
            tmp = os.path.join(fallback_base, ".hmbs-tmp")
            os.makedirs(tmp, exist_ok=True)
        for key in ("TMPDIR", "TMP", "TEMP", "TEMPDIR"):
            os.environ[key] = tmp
        return tmp

    def build(self):
        self._ensure_writable_tmp()
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        if not can_run(self):
            raise ConanException("libwmime target consumers are not runnable")
        self._ensure_writable_tmp()
        try:
            CMake(self).test()
            ctest_ok = True
        except Exception as exc:
            self.output.warning("ctest failed: %s" % exc)
            self._dump_last_test_log()
            ctest_ok = False
        binaries_passed = self._run_consumer_binaries_capture()
        # L0d quality gate + conanrun proof: execute the same binaries under
        # the managed run environment (covers shared-lib lookup paths).
        for name in CONSUMER_BINARIES:
            self.run(
                os.path.join(self.cpp.build.bindirs[0], name), env="conanrun"
            )
        marker = {
            "executed": True,
            "passed": ctest_ok and binaries_passed == len(CONSUMER_BINARIES),
            "command": "ctest --output-on-failure -j1 && ./test_message_build && ./test_mime_parse",
            "discovered": len(CONSUMER_BINARIES),
            "passedCount": binaries_passed,
        }
        self.output.info(
            "HMBS_TEST_PACKAGE_RESULT=" + json.dumps(marker, ensure_ascii=False)
        )
        if not marker["passed"]:
            raise ConanException(
                "consumer tests failed: ctest_ok=%s binaries %s/%s"
                % (ctest_ok, binaries_passed, len(CONSUMER_BINARIES))
            )
        self.output.info("libwmime consumer test_package passed")

    def _dump_last_test_log(self):
        # Surface the real ctest output so the next round diagnoses from
        # evidence instead of guessing.
        try:
            build_folder = getattr(self, "build_folder", "") or ""
            candidates = []
            if build_folder and os.path.isdir(build_folder):
                for root, dirs, files in os.walk(build_folder):
                    if "LastTest.log" in files:
                        candidates.append(os.path.join(root, "LastTest.log"))
                    if root.count(os.sep) - build_folder.count(os.sep) > 6:
                        dirs[:] = []
            for log_path in sorted(candidates)[:2]:
                try:
                    with open(log_path, "r", encoding="utf-8",
                              errors="replace") as handle:
                        content = handle.read()
                except OSError:
                    continue
                self.output.info("LastTest.log (%s) tail:" % log_path)
                self.output.info(content[-4000:])
        except Exception:
            pass

    def _consumer_test_env(self):
        # Raw subprocess does not inherit the conanrun aggregation, so prepend
        # every dependency libdir (libwmime/openssl/libiconv) to
        # LD_LIBRARY_PATH for the counting run. The self.run proof run above
        # additionally covers the managed environment.
        env = dict(os.environ)
        libdirs = []
        try:
            items = list(self.dependencies.items())
        except Exception:
            items = []
        for _req, dep in items:
            try:
                pkg_folder = str(dep.package_folder)
                for libdir in dep.cpp_info.libdirs:
                    cand = libdir if os.path.isabs(libdir) else os.path.join(
                        pkg_folder, libdir
                    )
                    if os.path.isdir(cand) and cand not in libdirs:
                        libdirs.append(cand)
            except Exception:
                continue
        if libdirs:
            current = env.get("LD_LIBRARY_PATH", "")
            env["LD_LIBRARY_PATH"] = os.pathsep.join(
                libdirs + ([current] if current else [])
            )
        return env

    def _run_consumer_binaries_capture(self):
        bindir = self.cpp.build.bindir
        binaries_passed = 0
        for name in CONSUMER_BINARIES:
            exe = os.path.join(bindir, name)
            if not os.path.isfile(exe):
                raise ConanException("test binary missing: %s" % exe)
            proc = subprocess.run(
                [exe],
                env=self._consumer_test_env(),
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                timeout=300,
            )
            output = proc.stdout or ""
            self.output.info(output[-2000:])
            ok_count = output.count("CHECK-OK:")
            fail_count = output.count("CHECK-FAIL:")
            checks = re.findall(r"CHECK-(?:OK|FAIL):\s*(\S+)", output)
            if not checks:
                raise ConanException("consumer %s emitted no CHECK lines" % name)
            if proc.returncode == 0 and fail_count == 0 and ok_count > 0:
                binaries_passed += 1
        return binaries_passed
