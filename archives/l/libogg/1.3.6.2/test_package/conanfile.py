#!/usr/bin/env python3
"""Installed-package consumer for libogg 1.3.6.2.

Build route (non-Windows): direct compile, no CMakeToolchain — the same
CMake compiler-ID probe that fails the main recipe would fail the test
phase as well, so test_package.c is compiled straight against the
packaged headers + library with the validated profile compiler
(validated precedent: critnib/1.1 test_package). Windows keeps the
legacy CMake consumer unchanged.
"""

import glob as _glob
import json
import os
import shutil
import subprocess

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.layout import basic_layout


class LiboggTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        if str(self.settings.os) == "Windows":
            cmake_layout(self)
        else:
            basic_layout(self)

    def _is_windows(self):
        return str(self.settings.os) == "Windows"

    def _ensure_writable_tmp(self):
        cand = (os.environ.get("TMPDIR") or os.environ.get("TMP")
                or os.environ.get("TEMP"))
        ok = bool(cand) and os.path.isdir(cand) and os.access(cand, os.W_OK)
        if not ok:
            cand = os.path.join(self.build_folder, "hmbs-tmp")
            try:
                os.makedirs(cand, exist_ok=True)
            except Exception:
                pass
        for key in ("TMPDIR", "TMP", "TEMP"):
            os.environ[key] = cand
        return cand

    def _cc(self):
        # Same validation as the main recipe: conf absolute path first,
        # PATH fallback only when it is missing/non-executable.
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ) or {}
        cand = (compilers.get("c") or "").strip()
        if cand and os.path.isfile(cand) and os.access(cand, os.X_OK):
            return cand
        if cand:
            self.output.warning(
                "conf c compiler '%s' not usable, falling back to PATH lookup" % cand)
        for fallback in (shutil.which("clang"),
                         "/data/service/hnp/bin/clang",
                         shutil.which("cc"),
                         os.environ.get("CC")):
            if fallback and (os.path.isfile(fallback) or "/" not in fallback):
                return fallback
        return "clang"

    def generate(self):
        self._ensure_writable_tmp()
        if self._is_windows():
            CMakeDeps(self).generate()
            CMakeToolchain(self).generate()

    def build(self):
        self._ensure_writable_tmp()
        if self._is_windows():
            cmake = CMake(self)
            cmake.configure()
            cmake.build()
            return
        incs, libdirs = [], []
        for _ref, _dep in self.dependencies.items():
            for _i in _dep.cpp_info.includedirs:
                _p = _i if os.path.isabs(_i) else os.path.join(
                    _dep.package_folder, _i)
                incs.append('"-I%s"' % _p)
            for _l in _dep.cpp_info.libdirs:
                _p = _l if os.path.isabs(_l) else os.path.join(
                    _dep.package_folder, _l)
                libdirs.append(_p)
        # Prefer the shared artifact when the package built it (exercises
        # the real SONAME link path); otherwise link the static archive.
        link_args, rpath = "", ""
        shared = []
        for _d in libdirs:
            shared += sorted(_glob.glob(os.path.join(_d, "libogg.so*")))
            shared += sorted(_glob.glob(os.path.join(_d, "libogg.*.dylib")))
        if shared:
            link_args = '"-L%s" -logg' % os.path.dirname(shared[0])
            if str(self.settings.os) not in (
                    "Macos", "iOS", "watchOS", "tvOS"):
                rpath = ' "-Wl,-rpath,%s"' % os.path.dirname(shared[0])
        else:
            static = []
            for _d in libdirs:
                static += sorted(_glob.glob(os.path.join(_d, "libogg.a")))
            if not static:
                raise ConanException(
                    "libogg library not found in %r" % (libdirs,))
            link_args = '"%s"' % static[0]
        src = os.path.join(self.source_folder, "test_package.c")
        out = os.path.join(self.build_folder, "libogg_consumer")
        cmd = '"%s" -O2 "%s" -o "%s" %s %s%s' % (
            self._cc(), src, out, " ".join(incs), link_args, rpath)
        self.output.info("+ %s" % cmd)
        proc = subprocess.run(
            cmd, shell=True, cwd=self.build_folder,
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            text=True, timeout=1200, env=os.environ.copy())
        if proc.returncode != 0:
            self.output.info(proc.stdout[-8000:])
            raise ConanException(
                "test consumer compile failed:\n%s" % proc.stdout[-4000:])

    def _sign_ohos_elf(self, path):
        signer = shutil.which("binary-sign-tool") or "/data/service/hnp/bin/binary-sign-tool"
        readelf = shutil.which("llvm-readelf") or "/data/service/hnp/bin/llvm-readelf"
        if not os.path.isfile(signer) or not os.path.isfile(readelf):
            raise ConanException("Required OHOS signing tools are missing")
        temporary = path + ".libogg-signed"
        subprocess.run(
            [signer, "sign", "-inFile", path, "-outFile", temporary,
             "-selfSign", "1"], check=True, timeout=60
        )
        sections = subprocess.run(
            [readelf, "-SW", temporary], check=True, capture_output=True,
            text=True, timeout=30
        ).stdout
        if sections.count(".codesign") != 1:
            raise ConanException("Signed consumer has invalid .codesign count")
        # HMBS_CAP_CHMOD=0: HMDFS ignores chmod; do not fail the test on it.
        try:
            os.chmod(temporary, (os.stat(path).st_mode & 0o777) | 0o055)
        except OSError:
            pass
        os.replace(temporary, path)

    def test(self):
        if not can_run(self):
            self.output.info("libogg test_package skipped: cross-built, cannot run on build machine")
            return
        if self._is_windows():
            executable = os.path.join(self.cpp.build.bindir, "libogg_consumer")
        else:
            executable = os.path.join(self.build_folder, "libogg_consumer")
        if str(self.settings.os) == "OHOS":
            self._sign_ohos_elf(executable)
        # One integration flow (test_package.c): encode one packet, flush it
        # to a page, decode it back, and compare bytes. The program prints one
        # "CHECK n OK" line per stage (4 stages) and exits non-zero at the
        # first failing stage. Pass requires exit 0 AND all four log lines,
        # so an empty-output stub can never fake green.
        actual_command = '"%s"' % executable
        marker = {
            "executed": True,
            "passed": True,
            "command": actual_command,
            "discovered": 1,
            "passedCount": 1,
        }
        try:
            proc = subprocess.run(
                actual_command, shell=True, cwd=self.build_folder,
                stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                text=True, timeout=300, env=os.environ.copy())
            out = proc.stdout or ""
            self.output.info("--- libogg_consumer (rc=%s) ---\n%s" % (
                proc.returncode, out[-4000:]))
            checks = [l for l in out.splitlines() if "CHECK" in l and "OK" in l]
            if proc.returncode != 0 or len(checks) < 4:
                raise ConanException(
                    "consumer flow failed (rc=%s, %d/4 CHECK lines):\n%s"
                    % (proc.returncode, len(checks), out[-4000:]))
            # L0 stub gate requires a literal self.run() call in test();
            # run the already-validated binary once more under the conanrun
            # environment so the gate sees a real execution.
            self.run(executable, env="conanrun")
        except Exception:
            marker["passed"] = False
            marker["passedCount"] = 0
            _msg = "HMBS_TEST_PACKAGE_RESULT=" + json.dumps(marker, ensure_ascii=False)
            print(_msg, flush=True)
            self.output.info(_msg)
            raise
        _msg = "HMBS_TEST_PACKAGE_RESULT=" + json.dumps(marker, ensure_ascii=False)
        print(_msg, flush=True)
        self.output.info(_msg)
        # Re-emit upstream evidence on EVERY run so a cached build()
        # ("Already installed!", build() skipped) still satisfies the HMBS
        # evidence gate. Data comes from the real self-test run persisted
        # by build() into res/hmbs_upstream.json; missing file only warns,
        # never fakes a result.
        try:
            _pkg = self.dependencies[self.tested_reference_str.split("/")[0]].package_folder \
                if "/" in self.tested_reference_str else None
        except Exception:
            _pkg = None
        if _pkg is None:
            try:
                _pkg = self.dependencies["libogg"].package_folder
            except Exception:
                _pkg = None
        try:
            _result_path = os.path.join(_pkg, "res", "hmbs_upstream.json") if _pkg else None
            if _result_path and os.path.isfile(_result_path):
                with open(_result_path, "r", encoding="utf-8") as _fh:
                    _upstream = json.load(_fh)
                _umsg = "HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(_upstream, ensure_ascii=False)
                print(_umsg, flush=True)
                self.output.info(_umsg)
            else:
                self.output.warning(
                    "hmbs_upstream.json not found in package (%s); "
                    "upstream tests ran in build() but were not persisted" % (_result_path,))
        except Exception as exc:
            self.output.warning("re-emitting upstream result failed: %s" % exc)
