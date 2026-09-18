#!/usr/bin/env python3
"""Conan test_package for libisl 0.28."""

import json
import os
import shutil

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.env import VirtualRunEnv


class LibislTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def _resolve_compiler(self, kind, fallbacks):
        """Verified compiler path: profile may hardcode a missing HNP clang.

        Device evidence (this round): CMakeToolchain baked
        CMAKE_C_COMPILER=/data/service/hnp/bin/clang which does not exist
        on the shard, so cmake configure aborts before compiling. Check
        the profile path with isfile (HMDFS ignores chmod/X_OK, so no
        os.access probe) and fall back to PATH lookup where hmbs
        prepends its tool dir. Mirrors the main recipe resolver.
        """
        try:
            executables = self.conf.get(
                "tools.build:compiler_executables", default={}, check_type=dict
            ) or {}
        except Exception:
            executables = {}
        configured = executables.get(kind)
        if configured and os.path.isabs(configured) and os.path.isfile(configured):
            return configured
        if configured and not os.path.isabs(configured):
            found = shutil.which(configured)
            if found:
                return found
        for cand in fallbacks:
            found = shutil.which(cand)
            if found:
                return found
        return configured or fallbacks[0]

    def generate(self):
        deps = CMakeDeps(self)
        deps.generate()
        tc = CMakeToolchain(self)
        tc.variables["CMAKE_C_COMPILER"] = self._resolve_compiler(
            "c", ("clang", "cc", "gcc"))
        tc.variables["CMAKE_CXX_COMPILER"] = self._resolve_compiler(
            "cpp", ("clang++", "c++", "g++"))
        tc.generate()
        run = VirtualRunEnv(self)
        run.generate()

    def _writable_tmpdir(self):
        # readonly_tmp: cmake/clang temp must avoid readonly /tmp.
        for cand in (
            os.environ.get("HMBS_TMPDIR"),
            os.environ.get("TMPDIR"),
            os.environ.get("TMP"),
            os.environ.get("TEMP"),
            os.environ.get("HMBS_AUTOCONF_MKTEMP_FALLBACK"),
            os.environ.get("HMBS_INSTALL"),
            "/data/storage/el2/base/cache",
        ):
            if not cand or cand == "/tmp":
                continue
            try:
                os.makedirs(cand, exist_ok=True)
                probe = os.path.join(cand, ".hmbs-write-probe")
                with open(probe, "w", encoding="utf-8") as f:
                    f.write("ok")
                os.unlink(probe)
                return cand
            except OSError:
                continue
        fallback = os.path.join(self.build_folder or os.getcwd(), ".tmp")
        try:
            os.makedirs(fallback, exist_ok=True)
        except OSError:
            pass
        return fallback

    def build(self):
        tmpdir = self._writable_tmpdir()
        os.environ["TMPDIR"] = tmpdir
        os.environ["TMP"] = tmpdir
        os.environ["TEMP"] = tmpdir
        cc = self._resolve_compiler("c", ("clang", "cc", "gcc"))
        cxx = self._resolve_compiler("cpp", ("clang++", "c++", "g++"))
        os.environ["CC"] = cc
        os.environ["CXX"] = cxx
        self.output.info(f"[HMBS cc] test_package CC={cc} CXX={cxx}")
        cmake = CMake(self)
        cmake.configure()
        cmake.build(build_tool_args=["-j1"])

    def _dump_ctest_log(self):
        """Print LastTest.log + test binary output on ctest failure.

        The 2026-09-16 preflight showed only 'test_libisl Failed 0.03s'
        with no binary output, so the next round needs the real reason
        (version assert, loader error, /tmp write, ...). Best-effort,
        never raises.
        """
        try:
            base = self.build_folder or os.getcwd()
            for root, _, files in os.walk(base):
                if "LastTest.log" in files:
                    path = os.path.join(root, "LastTest.log")
                    try:
                        with open(path, "r", encoding="utf-8",
                                  errors="replace") as f:
                            text = f.read()
                    except OSError:
                        continue
                    self.output.info("[HMBS test] LastTest.log tail:")
                    for line in text.splitlines()[-40:]:
                        self.output.info("  ctest| " + line[:400])
        except Exception:
            pass

    def test(self):
        if not can_run(self):
            self.output.info("Skipping test_libisl execution because this is a cross build")
            return
        # readonly_tmp: ctest + test binary must not touch readonly /tmp.
        # build() already redirected compile temps; test() is a separate
        # conan phase where profile aggregation can restore /tmp, so
        # re-establish the write-probed dir here (env only, no test skip).
        tmpdir = self._writable_tmpdir()
        os.environ["TMPDIR"] = tmpdir
        os.environ["TMP"] = tmpdir
        os.environ["TEMP"] = tmpdir
        self.output.info(f"[HMBS tmp] test_package test() TMPDIR={tmpdir}")
        cmake = CMake(self)
        try:
            cmake.test()
        except Exception:
            self._dump_ctest_log()
            raise
        bin_path = os.path.join(self.cpp.build.bindir, "test_libisl")
        self.run(bin_path, env="conanrun")
        # Machine evidence: ctest (1 case) + direct binary run both passed;
        # test.c itself holds 7 assertions (version/ctx/parse/empty/count).
        print(
            'HMBS_TEST_PACKAGE_RESULT={"executed":true,"passed":true,'
            '"command":"ctest --output-on-failure + ./test_libisl",'
            '"discovered":1,"passedCount":1}',
            flush=True,
        )
        # Re-emit upstream evidence persisted by the main recipe so every
        # preflight log carries both markers (cached-package rounds skip
        # build() output entirely).
        try:
            pkg_folder = self.dependencies["libisl"].package_folder
            result_file = os.path.join(pkg_folder, "res", "upstream_test_result.json")
            if os.path.isfile(result_file):
                with open(result_file, "r", encoding="utf-8") as f:
                    upstream = json.load(f)
                print("HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(upstream, ensure_ascii=False),
                      flush=True)
        except Exception:
            pass
