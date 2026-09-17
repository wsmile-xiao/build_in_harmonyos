#!/usr/bin/env python3
"""Conan test_package — liblqr 0.4.2.

Builds test.c against the packaged library (R34: real API calls —
lqr_carver_new / get dims / init / resize) and emits HMBS
machine-evidence markers. Upstream 0.4.2 ships no test suite
(audited tarball, see test_package/MANIFEST.yml), so the upstream
marker is the honest no_tests/0 result.
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


class LiblqrTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "CMakeDeps", "CMakeToolchain"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def _runnable(self, cmd):
        """True when `cmd --version` exits 0 (exists + exec works)."""
        try:
            if not cmd:
                return False
            if os.path.sep in cmd or "/" in cmd:
                if not (os.path.isfile(cmd) and os.access(cmd, os.X_OK)):
                    return False
            r = subprocess.run([cmd, "--version"],
                               stdout=subprocess.DEVNULL,
                               stderr=subprocess.DEVNULL,
                               timeout=20, check=False)
            return r.returncode == 0
        except Exception:
            return False

    def _pick(self, kind):
        """Adapted dhex/0.69: gated fallback, PATH clang->cc->gcc order."""
        try:
            conf = self.conf.get("tools.build:compiler_executables",
                                 default={}, check_type=dict) or {}
        except Exception:
            conf = {}
        cands = []
        if kind == "cc":
            if isinstance(conf, dict) and conf.get("c"):
                cands.append(conf.get("c"))
            if os.environ.get("CC"):
                cands.append(os.environ.get("CC"))
            for b in ("clang", "cc", "gcc"):
                w = shutil.which(b)
                if w and w not in cands:
                    cands.append(w)
                if b not in cands:
                    cands.append(b)
        else:
            if isinstance(conf, dict) and conf.get("cpp"):
                cands.append(conf.get("cpp"))
            if os.environ.get("CXX"):
                cands.append(os.environ.get("CXX"))
            for b in ("clang++", "c++", "g++"):
                w = shutil.which(b)
                if w and w not in cands:
                    cands.append(w)
                if b not in cands:
                    cands.append(b)
        for c in cands:
            if self._runnable(c):
                return c
        return None

    def _fix_toolchain_compilers(self):
        """Rewrite conan_toolchain.cmake compilers when injected one is dead.

        The profile injects CMAKE_C_COMPILER=/data/service/hnp/bin/clang,
        which is unrunnable on some preflight workers (this round:
        'CMAKE_C_COMPILER ... is not able to compile a simple test
        program'; main recipe already falls back to harmonybrew clang
        via PATH for the same reason). Timing follows gupnp-av: patch
        the generated file in build(), after generation but before
        cmake.configure(), so it always takes effect. Only acts when
        the current value is provably unrunnable; healthy values are
        left untouched. C/CXX are kept as a pair.
        """
        tc_file = os.path.join(self.generators_folder,
                               "conan_toolchain.cmake")
        if not os.path.isfile(tc_file):
            return
        try:
            with open(tc_file, encoding="utf-8") as f:
                content = f.read()
        except OSError:
            return
        m_c = re.search(r'set\(\s*CMAKE_C_COMPILER\s+"([^"]*)"', content)
        m_cxx = re.search(r'set\(\s*CMAKE_CXX_COMPILER\s+"([^"]*)"', content)
        cur_c = m_c.group(1) if m_c else ""
        cur_cxx = m_cxx.group(1) if m_cxx else ""
        new_c = new_cxx = None
        if cur_c and not self._runnable(cur_c):
            new_c = self._pick("cc")
        if cur_cxx and not self._runnable(cur_cxx):
            new_cxx = self._pick("cxx")
        if new_c is None and new_cxx is None:
            return
        # Keep the pair consistent: if only one side needed a fallback,
        # derive its sibling from the same toolchain when possible.
        if new_c is not None and new_cxx is None and cur_cxx:
            new_cxx = cur_cxx
        if new_cxx is not None and new_c is None and cur_c:
            new_c = cur_c
        changed = False
        if new_c and m_c and new_c != cur_c:
            content = re.sub(
                r'(set\(\s*CMAKE_C_COMPILER\s+)"[^"]*"',
                r'\1"%s"' % new_c, content)
            changed = True
            self.output.info("test_package CMAKE_C_COMPILER %s -> %s"
                             % (cur_c, new_c))
        if new_cxx and m_cxx and new_cxx != cur_cxx:
            content = re.sub(
                r'(set\(\s*CMAKE_CXX_COMPILER\s+)"[^"]*"',
                r'\1"%s"' % new_cxx, content)
            changed = True
            self.output.info("test_package CMAKE_CXX_COMPILER %s -> %s"
                             % (cur_cxx, new_cxx))
        if changed:
            try:
                with open(tc_file, "w", encoding="utf-8") as f:
                    f.write(content)
            except OSError as e:
                self.output.warning("cannot save toolchain: %s" % e)

    def build(self):
        self._fix_toolchain_compilers()
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        if not can_run(self):
            raise ConanException("liblqr target consumers are not runnable")
        discovered = 4
        passed = 0
        command = "test_liblqr"
        try:
            cmake = CMake(self)
            cmake.test()
            passed = discovered
        except Exception as exc:
            self.output.error(f"ctest failed: {exc}")
            # Fall back to running the binary directly so a ctest-harness
            # issue cannot mask a real library failure (or vice versa).
            try:
                exe = os.path.join(self.cpp.build.bindir, "test_liblqr")
                self.run(f'"{exe}"', env="conanrun")
                passed = discovered
            except Exception as exc2:
                self.output.error(f"direct run failed: {exc2}")

        tp_result = {
            "executed": True,
            "passed": passed == discovered,
            "command": command,
            "discovered": discovered,
            "passedCount": passed,
        }
        print(f"HMBS_TEST_PACKAGE_RESULT={json.dumps(tp_result)}")

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
                "liblqr-1-0.4.2.tar.bz2 audited (sha256 "
                "173a822efd207d72cda7d7f4e951c5000f31b10209366ff7f0f5972f7f9ff137): "
                "93 files, no tests/ test/ spec/ t/ directory and no test "
                "source files anywhere (case-insensitive find for *test* "
                "returns 0 hits); top Makefile.am defines only "
                "SUBDIRS = lqr man with no TESTS/check_PROGRAMS/check-local; "
                "lqr/Makefile.am builds only liblqr-1.la plus headers; "
                "configure.ac contains no test macros (only "
                "PKG_CHECK_MODULES for glib-2.0); `make -n check` expands to "
                "automake's default empty target, so make check executes 0 cases"
            ),
        }
        print(f"HMBS_UPSTREAM_TEST_RESULT={json.dumps(ut_result)}")

        if passed != discovered:
            raise ConanException("test_package checks failed")
