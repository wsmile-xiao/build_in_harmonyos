#!/usr/bin/env python3
"""Conan test_package for libxcb 1.17.0.

Inherits the OHOS adaptation validated for libxcb 1.16
(archives/l/libxcb/1.16/test_package/conanfile.py): on OHOS the Conan
profile names /data/service/hnp/bin/clang but some validation devices
only carry $HOME/usr/local/bin/clang, and the generated conanbuild*.sh
scripts call printenv before applying the profile PATH on a minimal
base PATH. The test package therefore prepends OHOS tool paths into
os.environ['PATH'], patches generated conan_toolchain.cmake to fall
back to a PATH-discovered compiler when the configured one is missing,
and bootstraps PATH inside generated .sh scripts before CMake configure.
"""

import json
import os
import re
import shutil

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.cmake import CMake, cmake_layout
from conan.tools.env import VirtualRunEnv


class LibxcbTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "CMakeDeps", "CMakeToolchain"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        VirtualRunEnv(self).generate()

    def build(self):
        if str(self.settings.os) == "OHOS":
            self._prepend_ohos_tool_paths()
            self._patch_cmake_toolchain_compilers()
            self._patch_conan_env_scripts()
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        if str(self.settings.os) == "OHOS":
            self._prepend_ohos_tool_paths()
            self._patch_conan_env_scripts()
        test_bin = os.path.join(self.cpp.build.bindirs[0], "test_libxcb")
        self.run(test_bin, env="conanrun")
        # HMBS evidence marker: test.c runs 3 real cases (two
        # xcb_parse_display assertions + one xcb_big_requests_id symbol
        # touch); the binary exits non-zero on any failure, so on success
        # all 3 passed. Numbers are the actual test_package case count.
        marker = {
            "executed": True,
            "passed": True,
            "command": test_bin,
            "discovered": 3,
            "passedCount": 3,
        }
        print("HMBS_TEST_PACKAGE_RESULT=" + json.dumps(marker, ensure_ascii=False))
        # HMBS upstream-test evidence: the main recipe runs upstream
        # `make check` during build() and carries the real automake summary
        # into the package as res/upstream_test_summary.json. The test_package
        # stage always runs (even when a later preflight reuses the cached
        # binary and skips build()), so re-emit the marker here from that
        # summary — the numbers come from the true-machine make check run.
        summary_path = os.path.join(
            self.dependencies["libxcb"].package_folder, "res", "upstream_test_summary.json"
        )
        if not os.path.isfile(summary_path):
            raise ConanException(
                "missing upstream test summary in package: " + summary_path
            )
        with open(summary_path, "r", encoding="utf-8") as handle:
            upstream = json.load(handle)
        if upstream.get("status") != "passed":
            raise ConanException(
                "upstream test summary status is not passed: "
                + json.dumps(upstream, ensure_ascii=False)
            )
        print(
            "HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(upstream, ensure_ascii=False)
        )

    def _prepend_ohos_tool_paths(self):
        existing = os.environ.get("PATH", "")
        existing_parts = existing.split(os.pathsep) if existing else []
        for path in reversed(self._ohos_tool_paths()):
            if path not in existing_parts:
                existing = path + (os.pathsep + existing if existing else "")
                existing_parts.insert(0, path)
        os.environ["PATH"] = existing

    def _patch_cmake_toolchain_compilers(self):
        generators_folder = self.generators_folder
        if not generators_folder or not os.path.isdir(generators_folder):
            return

        replacements = {
            "C": self._fallback_compiler("c", "clang"),
            "CXX": self._fallback_compiler("cpp", "clang++"),
        }
        if not any(replacements.values()):
            return

        toolchain = os.path.join(generators_folder, "conan_toolchain.cmake")
        if not os.path.isfile(toolchain):
            return

        with open(toolchain, "r", encoding="utf-8") as handle:
            content = handle.read()

        for language, replacement in replacements.items():
            if not replacement:
                continue
            content = re.sub(
                rf'(set\(CMAKE_{language}_COMPILER\s+)"[^"]+"',
                rf'\1"{replacement}"',
                content,
            )

        with open(toolchain, "w", encoding="utf-8") as handle:
            handle.write(content)

    def _patch_conan_env_scripts(self):
        generators_folder = self.generators_folder
        if not generators_folder or not os.path.isdir(generators_folder):
            return

        bootstrap_paths = self._ohos_tool_paths()
        if not bootstrap_paths:
            return

        bootstrap = ":".join(bootstrap_paths)
        marker = "# libxcb test_package OHOS PATH bootstrap"
        for entry in os.listdir(generators_folder):
            if not entry.endswith(".sh") or entry.startswith("deactivate_"):
                continue
            script_path = os.path.join(generators_folder, entry)
            with open(script_path, "r", encoding="utf-8") as handle:
                content = handle.read()
            if marker in content:
                continue
            with open(script_path, "w", encoding="utf-8") as handle:
                handle.write(f'{marker}\nexport PATH="{bootstrap}:${{PATH}}"\n' + content)

    def _fallback_compiler(self, compiler_key, fallback_name):
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        )
        configured = compilers.get(compiler_key)
        if configured:
            configured_path = str(configured).split()[0].strip("\"'")
            if os.path.exists(configured_path) and os.access(configured_path, os.X_OK):
                return None
        fallback = shutil.which(fallback_name)
        if fallback and os.path.exists(fallback) and os.access(fallback, os.X_OK):
            return fallback
        return None

    def _ohos_tool_paths(self):
        return [
            path
            for path in (
                "/data/service/hnp/bin",
                os.path.join(os.path.expanduser("~"), "usr", "local", "bin"),
                "/bin",
                "/usr/bin",
            )
            if os.path.isdir(path)
        ]
