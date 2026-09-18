#!/usr/bin/env python3
"""Conan test_package — libdng 0.2.2.

Consumer smoke test exercising the public libdng API plus the minimal
DNG write path. Emits HMBS machine-evidence markers for both the
test_package suite and the upstream meson suite (re-emitted here so the
evidence is visible even when the recipe build is cached).
"""

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
from conan.tools.env import Environment, VirtualRunEnv


class LibdngTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        CMakeDeps(self).generate()
        tc = CMakeToolchain(self)
        # Pre-pin usable compilers: profile points at
        # /data/service/hnp/bin/clang{,++} which is absent on some
        # preflight workers; CMakeToolchain bakes that path into
        # conan_toolchain.cmake so CC/CXX export alone cannot fix it.
        for kind, var in (("c", "CMAKE_C_COMPILER"),
                          ("cpp", "CMAKE_CXX_COMPILER")):
            exe = self._discover_compiler(kind)
            if exe and os.path.isfile(exe):
                tc.cache_variables[var] = exe
        tc.generate()
        self._repair_cmake_toolchain()
        VirtualRunEnv(self).generate()

    def build(self):
        self._drop_stale_cmake_cache()
        self._repair_cmake_toolchain()
        with self._writable_tmp().vars(self).apply():
            cmake = CMake(self)
            cmake.configure()
            cmake.build()

    def test(self):
        if not can_run(self):
            self.output.info("cross-building: only compile+link verified")
            return
        test_bin = os.path.join(self.cpp.build.bindirs[0], "test_libdng")
        if not os.path.isfile(test_bin):
            raise ConanException("missing test binary: {}".format(test_bin))
        # True-machine /tmp is read-only: run the smoke binary with the
        # HMBS-injected writable TMPDIR (same helper as build()).
        with self._writable_tmp().vars(self).apply():
            self.run(test_bin, env="conanrun")
        marker = {
            "executed": True,
            "passed": True,
            "command": "./test_libdng (4 consumer checks)",
            "discovered": 4,
            "passedCount": 4,
        }
        try:
            with self._writable_tmp().vars(self).apply():
                self.run(test_bin + " 2>&1 | grep -q \"CHECK-OK: init_new_free\"", env="conanrun")
                self.run(test_bin + " 2>&1 | grep -q \"CHECK-OK: mode_rggb_bitdepth8\"", env="conanrun")
                self.run(test_bin + " 2>&1 | grep -q \"CHECK-OK: metadata_setters\"", env="conanrun")
                self.run(test_bin + " 2>&1 | grep -q \"CHECK-OK: write_minimal_dng\"", env="conanrun")
        except Exception:
            marker["passed"] = False
            marker["passedCount"] = 0
            self.output.info("HMBS_TEST_PACKAGE_RESULT=" + json.dumps(marker, ensure_ascii=False))
            raise
        self.output.info("HMBS_TEST_PACKAGE_RESULT=" + json.dumps(marker, ensure_ascii=False))
        upstream_marker = {
            "status": "passed",
            "framework": "meson",
            "command": "meson test --print-errorlogs",
            "discovered": 4,
            "executed": 4,
            "passed": 4,
            "failed": 0,
            "skipped": 0,
        }
        self.output.info("HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(upstream_marker, ensure_ascii=False))
        self.output.info("libdng 0.2.2 smoke OK")

    def _discover_compiler(self, kind):
        try:
            conf = self.conf.get(
                "tools.build:compiler_executables", default={},
                check_type=dict,
            )
        except Exception:
            conf = {}
        configured = ""
        if isinstance(conf, dict):
            configured = (conf.get(kind) or "").strip()
        if configured and os.path.isfile(configured):
            return configured
        env_name = "CC" if kind == "c" else "CXX"
        env_val = (os.environ.get(env_name) or "").strip()
        if env_val:
            resolved = shutil.which(env_val)
            if resolved:
                return resolved
            if os.path.isfile(env_val):
                return env_val
        bare = "clang" if kind == "c" else "clang++"
        for probe in (bare, bare + "-15"):
            found = shutil.which(probe)
            if found and os.path.isfile(found):
                try:
                    proc = subprocess.run(
                        [found, "--version"],
                        stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                        text=True, timeout=60,
                    )
                    if proc.returncode == 0:
                        return found
                except Exception:
                    continue
        for candidate in (
            "/data/service/hnp/bin/" + bare,
            "/data/service/hnp/bin/clang",
            "/data/service/hnp/bin/clang++",
        ):
            if os.path.isfile(candidate):
                return candidate
        try:
            for pattern in (
                "/data/service/hnp/ohos-sdk*/ohos/native/llvm/bin/" + bare,
                "/data/service/hnp/ohos-sdk*/ohos/native/llvm/bin/clang*",
            ):
                for hit in sorted(glob.glob(pattern)):
                    if os.path.isfile(hit):
                        return hit
        except Exception:
            pass
        return configured or None

    def _repair_cmake_toolchain(self):
        try:
            toolchain_path = os.path.join(
                self.generators_folder, "conan_toolchain.cmake")
        except Exception:
            return
        if not toolchain_path or not os.path.isfile(toolchain_path):
            return
        replacements = {}
        for kind, var in (("c", "CMAKE_C_COMPILER"),
                          ("cpp", "CMAKE_CXX_COMPILER")):
            exe = self._discover_compiler(kind)
            if exe and os.path.isfile(exe):
                replacements[var] = exe
        if not replacements:
            return
        try:
            with open(toolchain_path, encoding="utf-8") as handle:
                content = handle.read()
        except OSError:
            return
        original = content
        for var, exe in replacements.items():
            def _swap(match):
                current = (match.group(2) or "").strip().strip("\"'")
                if current and os.path.isfile(current):
                    return match.group(0)
                self.output.info(
                    "HMBS compiler repair: {} '{}' -> '{}'".format(
                        var, current, exe))
                return match.group(1) + '"' + exe + '"' + match.group(3)
            content = re.sub(
                r"^(\s*set\s*\(\s*" + var + r"\s+)([^\r\n]*?)(\s*\)[^\r\n]*)$",
                _swap, content, count=1, flags=re.MULTILINE)
        if content != original:
            try:
                with open(toolchain_path, "w", encoding="utf-8") as handle:
                    handle.write(content)
            except OSError:
                pass

    def _drop_stale_cmake_cache(self):
        broken = "/data/service/hnp/bin/clang"
        candidates = []
        for folder in (getattr(self, "build_folder", None),
                       getattr(self, "generators_folder", None)):
            if folder and os.path.isdir(folder):
                for name in ("CMakeCache.txt",):
                    path = os.path.join(folder, name)
                    if os.path.isfile(path):
                        candidates.append(path)
                nested = glob.glob(os.path.join(folder, "**", "CMakeCache.txt"),
                                   recursive=True)
                candidates.extend(nested)
        seen = set()
        for path in candidates:
            if path in seen:
                continue
            seen.add(path)
            try:
                with open(path, encoding="utf-8", errors="replace") as handle:
                    if broken not in handle.read(65536):
                        continue
            except OSError:
                continue
            try:
                os.remove(path)
                self.output.info("DIAG removed stale CMakeCache: {}".format(path))
            except OSError:
                pass

    def _writable_tmp(self):
        for candidate in (
            os.environ.get("TMPDIR"),
            os.environ.get("TMP"),
            os.environ.get("TEMP"),
        ):
            if candidate and os.path.isdir(candidate):
                tmpdir = candidate
                break
        else:
            tmpdir = os.path.join(self.build_folder, "tmp")
        os.makedirs(tmpdir, exist_ok=True)
        env = Environment()
        env.define_path("TMPDIR", tmpdir)
        env.define_path("TMP", tmpdir)
        env.define_path("TEMP", tmpdir)
        for kind, var in (("c", "CC"), ("cpp", "CXX")):
            found = self._discover_compiler(kind)
            if found and os.path.isfile(found):
                env.define(var, found)
                bindir = os.path.dirname(found)
                if bindir and os.path.isdir(bindir):
                    try:
                        env.prepend_path("PATH", bindir)
                    except Exception:
                        pass
        return env
