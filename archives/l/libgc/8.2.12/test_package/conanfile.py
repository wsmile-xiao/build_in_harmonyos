#!/usr/bin/env python3
"""Conan test_package — libgc 8.2.12 (Boehm GC consumer test).

L1 consumer test (R34): builds test.c against the packaged libgc and runs
it. test.c performs 3 real API checks (GC_MALLOC, GC_REALLOC, GC_STRDUP +
GC_gcollect); this recipe parses the binary output for "CHECK n: PASS"
lines so HMBS_TEST_PACKAGE_RESULT counts come from the real run.

Upstream suite (make check, autotools) runs in the main recipe build();
its aggregated counts are shipped in res/upstream_test_summary.json and
re-emitted here as HMBS_UPSTREAM_TEST_RESULT (hmbs gate scans test_package
stdout, and build() is skipped on cache hit).
"""

import json
import os
import re
import shutil

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.env import VirtualRunEnv
from conan.tools.files import replace_in_file


class LibgcTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def _writable_tmpdir(self):
        """Reuse HMBS writable tmpdir; /tmp is erofs read-only on workers."""
        candidates = []
        fallback_var = os.environ.get("HMBS_AUTOCONF_MKTEMP_FALLBACK", "")
        if fallback_var and fallback_var not in ("0", "1"):
            candidates.append(fallback_var)
        for var in ("TMPDIR", "TMP", "TEMP", "HMBS_TMPDIR"):
            val = os.environ.get(var, "")
            if val and val != "/tmp" and val not in candidates:
                candidates.append(val)
        for cand in candidates:
            try:
                os.makedirs(cand, exist_ok=True)
                probe = os.path.join(cand, ".hmbs_probe")
                with open(probe, "w") as handle:
                    handle.write("probe")
                try:
                    os.remove(probe)
                except OSError:
                    pass
                return cand
            except OSError:
                continue
        fallback = os.path.join(os.path.expanduser("~"), "tmp", "libgc-8.2.12-test")
        try:
            os.makedirs(fallback, exist_ok=True)
        except OSError:
            fallback = self.build_folder or os.getcwd()
        return fallback

    def _compiler_executable(self, key, fallback_name):
        """Prefer a compiler that exists on this worker.

        The shared profile hardcodes /data/service/hnp/bin/clang(++),
        which is absent on some true-machine workers (main build falls
        back to harmonybrew clang via PATH). Probe conf value first
        (only if it is a file), then PATH, else the conf value / name.
        """
        try:
            executables = self.conf.get(
                "tools.build:compiler_executables",
                default={},
                check_type=dict,
            ) or {}
        except Exception:
            executables = {}
        configured = executables.get(key)
        if configured and os.path.isfile(configured):
            return configured
        found = shutil.which(fallback_name)
        if found:
            return found
        return configured or fallback_name

    def _patch_cmake_toolchain_compilers(self):
        """Replace stale hardcoded compiler paths in generated toolchain."""
        toolchain = os.path.join(self.generators_folder, "conan_toolchain.cmake")
        if not os.path.isfile(toolchain):
            return
        replacements = {
            "/data/service/hnp/bin/clang++": self._compiler_executable(
                "cpp", "clang++"
            ),
            "/data/service/hnp/bin/clang": self._compiler_executable("c", "clang"),
        }
        for old, new in replacements.items():
            try:
                replace_in_file(self, toolchain, old, new, strict=False)
            except Exception:
                pass

    def generate(self):
        tmpdir = self._writable_tmpdir()
        try:
            os.makedirs(tmpdir, exist_ok=True)
        except OSError:
            pass
        for k in ("TMPDIR", "TMP", "TEMP"):
            os.environ[k] = tmpdir
        self.output.info("libgc test_package: writable tmpdir %s" % tmpdir)
        CMakeDeps(self).generate()
        tc = CMakeToolchain(self)
        if self.settings.os == "OHOS":
            cc = self._compiler_executable("c", "clang")
            cxx = self._compiler_executable("cpp", "clang++")
            tc.cache_variables["CMAKE_C_COMPILER"] = cc
            tc.cache_variables["CMAKE_CXX_COMPILER"] = cxx
            self.output.info(
                "libgc test_package: CMAKE_C_COMPILER=%s CXX=%s" % (cc, cxx)
            )
        tc.generate()
        if self.settings.os == "OHOS":
            self._patch_cmake_toolchain_compilers()
        VirtualRunEnv(self).generate()

    def build(self):
        tmpdir = self._writable_tmpdir()
        try:
            os.makedirs(tmpdir, exist_ok=True)
        except OSError:
            pass
        for k in ("TMPDIR", "TMP", "TEMP"):
            os.environ[k] = tmpdir
        cmake = CMake(self)
        if self.settings.os == "OHOS":
            cc = self._compiler_executable("c", "clang")
            cxx = self._compiler_executable("cpp", "clang++")
            self.output.info(
                "libgc test_package configure with CC=%s CXX=%s TMPDIR=%s"
                % (cc, cxx, tmpdir)
            )
            cmake.configure(
                variables={
                    "CMAKE_C_COMPILER": cc,
                    "CMAKE_CXX_COMPILER": cxx,
                }
            )
        else:
            cmake.configure()
        cmake.build()

    def test(self):
        if not can_run(self):
            self.output.info("libgc: cross-build, skipping run (binaries verified at build)")
            return
        cmake = CMake(self)
        try:
            cmake.test()
        except Exception as exc:
            raise ConanException(f"libgc: ctest failed: {exc}")
        test_bin = None
        for root, _, files in os.walk(self.build_folder):
            if "test_libgc" in files or "test_libgc.exe" in files:
                cand = os.path.join(root, "test_libgc.exe" if "test_libgc.exe" in files else "test_libgc")
                if os.path.isfile(cand):
                    test_bin = cand
                    break
        if test_bin is None:
            raise ConanException("libgc: test binary test_libgc not found after build")
        logfile = os.path.join(self.build_folder, "test_libgc_run.log")
        # Redirect through shell so output lands in a file we can parse
        self.run(f'"{test_bin}" > "{logfile}" 2>&1', env="conanrun")
        out = ""
        if os.path.isfile(logfile):
            with open(logfile, "r", encoding="utf-8", errors="replace") as f:
                out = f.read()
        self.output.info("test_libgc output:\n" + "\n".join(out.splitlines()[-12:]))
        m = re.findall(r"CHECK\s+\d+:\s*PASS", out)
        passed = len(m)
        discovered = 3
        # Fail closed: no CHECK lines means harness broken, not a pass
        if passed == 0:
            raise ConanException("libgc: test binary produced no CHECK PASS lines")
        ok = passed == discovered
        marker = {
            "executed": True,
            "passed": ok,
            "command": "test_libgc (GC_MALLOC/GC_REALLOC/GC_STRDUP+GC_gcollect)",
            "discovered": discovered,
            "passedCount": passed,
        }
        self.output.info("HMBS_TEST_PACKAGE_RESULT=" + json.dumps(marker, ensure_ascii=False))
        if not ok:
            raise ConanException(f"libgc: test_package checks failed {passed}/{discovered}")
        pkg = self.dependencies["libgc"]
        summary_path = os.path.join(pkg.package_folder, "res", "upstream_test_summary.json")
        if os.path.isfile(summary_path):
            try:
                with open(summary_path, "r", encoding="utf-8") as f:
                    upstream = json.load(f)
                self.output.info("HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(upstream, ensure_ascii=False))
            except (OSError, ValueError) as exc:
                raise ConanException(f"libgc: unreadable upstream summary: {exc}")
        else:
            raise ConanException("libgc: upstream_test_summary.json missing in package")
        self.output.info("libgc functional test_package passed")
