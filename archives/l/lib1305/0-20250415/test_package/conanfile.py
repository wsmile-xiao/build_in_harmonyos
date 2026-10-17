#!/usr/bin/env python3
"""Conan test_package — lib1305 0-20250415 (consumer-side API contract test)."""
import json
import os
import shutil
import subprocess

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, cmake_layout


class Lib1305TestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def _resolve_compiler(self, key, fallbacks):
        try:
            conf = self.conf.get(
                "tools.build:compiler_executables", default={}, check_type=dict
            )
        except Exception:
            conf = {}
        configured = (conf or {}).get(key)
        if configured:
            resolved = shutil.which(configured)
            if resolved and os.path.isfile(resolved):
                return resolved
            if os.path.isabs(configured):
                by_name = shutil.which(os.path.basename(configured))
                if by_name and os.path.isfile(by_name):
                    self.output.warning(
                        f"configured compiler '{configured}' missing; "
                        f"falling back to PATH '{by_name}'"
                    )
                    return by_name
        for cand in fallbacks:
            resolved = shutil.which(cand)
            if resolved and os.path.isfile(resolved):
                return resolved
        return None

    def build(self):
        cmake = CMake(self)
        cc = self._resolve_compiler("c", ("clang", "cc", "gcc"))
        cxx = self._resolve_compiler("cpp", ("clang++", "c++", "g++"))
        variables = {}
        if cc:
            variables["CMAKE_C_COMPILER"] = cc
        if cxx:
            variables["CMAKE_CXX_COMPILER"] = cxx
        tc_path = os.path.join(self.generators_folder, "conan_toolchain.cmake")
        if os.path.isfile(tc_path):
            try:
                with open(tc_path, encoding="utf-8") as f:
                    tc_content = f.read()
                patched = tc_content
                if cxx and "/data/service/hnp/bin/clang++" in patched and not os.path.isfile("/data/service/hnp/bin/clang++"):
                    patched = patched.replace("/data/service/hnp/bin/clang++", cxx)
                if cc and "/data/service/hnp/bin/clang" in patched and not os.path.isfile("/data/service/hnp/bin/clang"):
                    patched = patched.replace("/data/service/hnp/bin/clang", cc)
                if patched != tc_content:
                    with open(tc_path, "w", encoding="utf-8") as f:
                        f.write(patched)
            except OSError as exc:
                self.output.warning(f"toolchain patch skipped: {exc}")
        if variables:
            cmake.configure(variables=variables)
        else:
            cmake.configure()
        cmake.build()

    def _reemit_upstream_marker(self):
        # HMBS persistence: build() is skipped on cache hits, so re-emit the
        # upstream marker persisted in the package (share/lib1305/
        # hmbs_upstream_test_result.json). Read verbatim, never fabricate.
        for dep in self.dependencies.host.values():
            candidate = os.path.join(dep.package_folder, "share", "lib1305", "hmbs_upstream_test_result.json")
            if os.path.isfile(candidate):
                try:
                    with open(candidate, encoding="utf-8") as f:
                        marker = json.load(f)
                    print("HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(marker), flush=True)
                    return
                except (OSError, ValueError) as exc:
                    self.output.warning(f"upstream marker re-emit skipped: {exc}")
                    return
        self.output.warning("upstream marker file missing in package")

    def test(self):
        bin_path = os.path.join(self.cpp.build.bindirs[0], "test_lib1305")
        if can_run(self):
            run_env = os.environ.copy()
            lib_dirs = []
            for dep in self.dependencies.host.values():
                libdir = os.path.join(dep.package_folder, "lib")
                if os.path.isdir(libdir):
                    lib_dirs.append(libdir)
            if lib_dirs:
                run_env["LD_LIBRARY_PATH"] = os.pathsep.join(
                    lib_dirs
                    + ([run_env["LD_LIBRARY_PATH"]] if run_env.get("LD_LIBRARY_PATH") else [])
                )
            proc = subprocess.run(
                [bin_path], capture_output=True, text=True, timeout=120,
                env=run_env,
            )
            out = (proc.stdout or "") + (proc.stderr or "")
            print(out, end="", flush=True)
            if proc.returncode != 0:
                raise RuntimeError(f"test_lib1305 failed (exit {proc.returncode})")
            discovered = 8
            passed_count = out.count("[PASS]")
            tp_marker = {
                "executed": True,
                "passed": proc.returncode == 0 and passed_count == discovered,
                "command": "./test_lib1305",
                "discovered": discovered,
                "passedCount": passed_count,
            }
            print(
                "HMBS_TEST_PACKAGE_RESULT=" + json.dumps(tp_marker),
                flush=True,
            )
            if not tp_marker["passed"]:
                raise RuntimeError(f"consumer test checks failed: {tp_marker}")
            self._reemit_upstream_marker()
        else:
            self.run(bin_path, env="conanrun")
            self._reemit_upstream_marker()
