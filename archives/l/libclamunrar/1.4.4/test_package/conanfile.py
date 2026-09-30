#!/usr/bin/env python3
"""Conan test_package for libclamunrar 1.4.4.

Builds test_libclamunrar.cpp against the packaged library with CMake and
runs it. Emits HMBS evidence markers every round (build() may be skipped
on cache hits, but test() always runs).
"""

import json
import os
import re
import shutil

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import can_run
from conan.tools.cmake import CMake, cmake_layout
from conan.tools.env import VirtualRunEnv


class LibclamunrarTestConan(ConanFile):
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
        if not can_run(self):
            raise ConanException("test_package requires can_run on OHOS native build")
        test_bin = os.path.join(self.cpp.build.bindirs[0], "test_libclamunrar")
        # PF3: real execution of the consumer binary linked against libclamunrar.
        self.run(test_bin, env="conanrun")
        # HMBS evidence: test_libclamunrar.cpp runs 3 deterministic checks
        # (DLL version + RAROpenArchive/RAROpenArchiveEx missing-file EOPEN
        # paths); non-zero exit on any failure, so success means 3/3 passed.
        marker = {
            "executed": True,
            "passed": True,
            "command": test_bin,
            "discovered": 3,
            "passedCount": 3,
        }
        print("HMBS_TEST_PACKAGE_RESULT=" + json.dumps(marker, ensure_ascii=False))
        # Upstream has no standalone suite (see MANIFEST audit); re-emit the
        # packaged audit so the marker survives cache-hit preflights.
        summary_path = os.path.join(
            self.dependencies["libclamunrar"].package_folder, "res", "upstream_test_audit.json"
        )
        if not os.path.isfile(summary_path):
            raise ConanException("missing upstream audit in package: " + summary_path)
        with open(summary_path, "r", encoding="utf-8") as handle:
            upstream = json.load(handle)
        if upstream.get("status") != "no_tests":
            raise ConanException(
                "unexpected upstream audit status: " + json.dumps(upstream, ensure_ascii=False)
            )
        print("HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(upstream, ensure_ascii=False))

    def _prepend_ohos_tool_paths(self):
        existing = os.environ.get("PATH", "")
        parts = existing.split(os.pathsep) if existing else []
        for path in reversed(self._ohos_tool_paths()):
            if path not in parts:
                existing = path + (os.pathsep + existing if existing else "")
                parts.insert(0, path)
        os.environ["PATH"] = existing

    def _patch_cmake_toolchain_compilers(self):
        generators_folder = self.generators_folder
        if not generators_folder or not os.path.isdir(generators_folder):
            return
        toolchain = os.path.join(generators_folder, "conan_toolchain.cmake")
        if not os.path.isfile(toolchain):
            return
        with open(toolchain, "r", encoding="utf-8") as handle:
            content = handle.read()
        original = content
        # E092: declarative CMakeToolchain maps os=OHOS to HarmonyOS which
        # CMake 4.x rejects ("System is unknown to cmake"). Same override
        # as the main recipe: plain Linux target built with OHOS clang.
        content = re.sub(
            r'set\(CMAKE_SYSTEM_NAME\s+"HarmonyOS"\)',
            'set(CMAKE_SYSTEM_NAME "Linux")',
            content,
        )
        content = re.sub(
            r'set\(CMAKE_SYSTEM_PROCESSOR\s+"[^"]*"\)',
            'set(CMAKE_SYSTEM_PROCESSOR "aarch64")',
            content,
        )
        replacements = {
            "C": self._fallback_compiler("c", "clang"),
            "CXX": self._fallback_compiler("cpp", "clang++"),
        }
        for language, replacement in replacements.items():
            if not replacement:
                continue
            content = re.sub(
                rf'(set\(CMAKE_{language}_COMPILER\s+)"[^"]+"',
                rf'\1"{replacement}"',
                content,
            )
        if content != original:
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
        marker = "# libclamunrar test_package OHOS PATH bootstrap"
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
