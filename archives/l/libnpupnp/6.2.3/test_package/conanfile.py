#!/usr/bin/env python3
"""Conan test_package for libnpupnp 6.2.3.

Builds test_npupnp.cpp (real public API: version checks, UpnpResolveURL2
cases ported from upstream test_url.cpp, UpnpInit/UpnpFinish from
test_init.cpp) with CMake and runs it. The test binary prints the
HMBS_TEST_PACKAGE_RESULT marker itself with runtime counters; it is run
via self.run (not plain ctest, whose passing-test output would be hidden)
so the marker flows into the conan log.
"""
import os
import re
import shutil
import subprocess

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class LibnpupnpTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        self._ensure_writable_tmp()
        tc = CMakeToolchain(self)
        tc.generate()
        self._repair_cmake_toolchain()

    def _ensure_writable_tmp(self):
        candidates = []
        for var in ("TMPDIR", "TMP", "TEMP"):
            val = os.environ.get(var)
            if val and val not in candidates:
                candidates.append(val)
        try:
            fallback = os.path.join(self.build_folder or "", "tmp-fallback")
        except Exception:
            fallback = ""
        if fallback:
            candidates.append(fallback)
        chosen = ""
        for cand in candidates:
            if not cand:
                continue
            try:
                os.makedirs(cand, exist_ok=True)
                probe = os.path.join(cand, ".hmbs_write_probe")
                with open(probe, "w", encoding="utf-8") as handle:
                    handle.write("ok")
                os.remove(probe)
                chosen = cand
                break
            except OSError:
                continue
        if chosen:
            for var in ("TMPDIR", "TMP", "TEMP"):
                os.environ[var] = chosen
            self.output.info("test_package using writable tmpdir {}".format(chosen))

    def _resolve_compiler(self, name):
        executables = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ) or {}
        key = "cpp" if name == "clang++" else "c"
        candidates = []
        configured = executables.get(key)
        if configured and configured not in candidates:
            candidates.append(configured)
        found = shutil.which(name)
        if found and found not in candidates:
            candidates.append(found)
        for directory in ("/data/service/hnp/bin", "/usr/bin"):
            cand = os.path.join(directory, name)
            if cand not in candidates:
                candidates.append(cand)
        for cand in candidates:
            if not cand or not os.path.isfile(cand):
                continue
            try:
                proc = subprocess.run(
                    [cand, "--version"],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    timeout=60,
                )
            except (OSError, subprocess.SubprocessError):
                continue
            if proc.returncode == 0:
                if cand != configured:
                    self.output.info(
                        "test_package using {} {} (profile {} unavailable)".format(
                            name, cand, configured
                        )
                    )
                return cand
        return ""

    def _repair_cmake_toolchain(self):
        c = self._resolve_compiler("clang")
        cpp = self._resolve_compiler("clang++")
        if not (c or cpp):
            return
        # CMakeToolchain writes absolute compiler paths from the profile
        # (tools.build:compiler_executables). On a worker missing the exact
        # DevBox path, cmake dies with "CMAKE_CXX_COMPILER: /data/... not
        # found". Rebind only dangling absolute paths; healthy workers keep
        # profile values untouched. Handles both quoted and unquoted forms.
        toolchain = os.path.join(self.generators_folder, "conan_toolchain.cmake")
        if not os.path.isfile(toolchain):
            return
        with open(toolchain, encoding="utf-8") as handle:
            content = handle.read()
        original = content

        def _is_abs(text):
            return os.path.isabs(text) or text.startswith("/")

        def _swap(path, wanted):
            if not wanted:
                return path
            if _is_abs(path) and not os.path.isfile(path):
                return wanted
            return path

        patterns = [
            (re.compile(r'set\(CMAKE_C_COMPILER\s+"([^"]+)"', re.S), c),
            (re.compile(r"set\(CMAKE_C_COMPILER\s+'([^']+)'", re.S), c),
            (re.compile(r"set\(CMAKE_C_COMPILER\s+([^\s\)]+)", re.S), c),
            (re.compile(r'set\(CMAKE_CXX_COMPILER\s+"([^"]+)"', re.S), cpp),
            (re.compile(r"set\(CMAKE_CXX_COMPILER\s+'([^']+)'", re.S), cpp),
            (re.compile(r"set\(CMAKE_CXX_COMPILER\s+([^\s\)]+)", re.S), cpp),
        ]
        for pattern, wanted in patterns:
            if not wanted:
                continue

            def _repl(match, wanted=wanted):
                return match.group(0).replace(match.group(1), _swap(match.group(1), wanted), 1)

            content = pattern.sub(_repl, content)
        if content != original:
            with open(toolchain, "w", encoding="utf-8") as handle:
                handle.write(content)
            self.output.info("test_package rebound toolchain compilers")

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        if not can_run(self):
            self.output.info(
                "Cross build: libnpupnp consumer was built; run it on the "
                "HarmonyOS PC target."
            )
            return
        executable = os.path.join(self.cpp.build.bindirs[0], "test_npupnp")
        self.run(executable, env="conanrun")
