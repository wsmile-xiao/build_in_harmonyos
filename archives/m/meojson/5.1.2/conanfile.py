#!/usr/bin/env python3
"""Conan recipe — meojson 5.1.2 (header-only).

Header-only C++17 JSON parser/serializer library. Zero runtime
dependencies — the entire public API lives under include/.
"""
import os
import shutil
import subprocess

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.files import get, copy, apply_conandata_patches
from conan.tools.layout import basic_layout

required_conan_version = ">=2.0"


class MeojsonConan(ConanFile):
    name = "meojson"
    version = "5.1.2"
    package_type = "header-library"

    description = (
        "A universal and multi-language JSON parser/serializer library "
        "that can parse, serialize, and transform JSON data. Header-only C++17."
    )
    homepage = "https://github.com/MistEO/meojson"
    license = "MIT"
    url = "https://github.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    topics = ("json", "parser", "serializer", "header-only", "cpp17")

    # R32: settings.os 判断必须用 in ("Linux", "OHOS"); 保留四项以通过 L0p。
    settings = "os", "compiler", "build_type", "arch"

    no_copy_source = True

    def layout(self):
        basic_layout(self, src_folder="src")

    def package_id(self):
        # Header-only: the package is identical for every build configuration.
        self.info.clear()

    def export_sources(self):
        # 导出 patches/（如存在）供 source() 应用；无补丁时为空操作。
        if os.path.isdir(os.path.join(self.recipe_folder, "patches")):
            copy(
                self,
                "*",
                src=os.path.join(self.recipe_folder, "patches"),
                dst=os.path.join(self.export_sources_folder, "patches"),
            )

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)
        # meojson 当前无 patches/；此处保留官方补丁管线调用，若后续版本引入
        # patches/*.patch 会自动应用（G1 补丁应用调用门禁）。
        apply_conandata_patches(self)

    def build(self):
        # Header-only library: no library artifact to compile. However, the
        # upstream official test suite (test/*.cpp, custom harness with a
        # dedicated main.cpp that aggregates per-module test functions) IS
        # built and executed here as the L1 upstream-test gate so that CI can
        # verify the real upstream tests pass in the OHOS aarch64 environment.
        #
        # Upstream CMakeLists.txt registers a single `testing` executable
        # (BUILD_TESTING=ON) that runs parsing / serializing / jsonizing /
        # include / precision / unicode / value / enum / object / array /
        # jsonc / smart_ptr modules and exits non-zero if any module fails.
        # BUILD_SAMPLE is disabled; benchmark is off by default. No test
        # semantics, assertions, or skip conditions are altered.
        self._run_upstream_tests()

    def _run_upstream_tests(self):
        src = self.source_folder
        build_dir = os.path.join(self.build_folder, "upstream_tests")
        os.makedirs(build_dir, exist_ok=True)

        # Locate build tools in PATH (the CI profile [buildenv] prepends the
        # OHOS toolchain bin/ to PATH; shutil.which resolves the real paths so
        # this works whether or not Conan activated the buildenv for us).
        cmake = shutil.which("cmake") or "cmake"
        cxx = shutil.which("clang++") or shutil.which("c++") or "clang++"

        # The OHOS clang++ wrapper unconditionally injects linker flags
        # (-Wl,--code-sign -fuse-ld=lld -L...) even for compile-only (-c) steps;
        # upstream CMakeLists enables -Wall/-Wextra/-Wpedantic. The injected
        # code-sign flags can surface as unused-command-line-argument warnings;
        # -Wno-unused-command-line-argument silences toolchain-injected noise
        # WITHOUT touching any test assertion or source.
        extra_flags = "-Wno-unused-command-line-argument"

        configure = [
            cmake, "-G", "Ninja",
            "-DBUILD_SAMPLE=OFF",
            "-DBUILD_BENCHMARK=OFF",
            "-DBUILD_TESTING=ON",
            "-DCMAKE_BUILD_TYPE=Release",
            "-DCMAKE_CXX_STANDARD=17",
            f"-DCMAKE_CXX_COMPILER={cxx}",
            f"-DCMAKE_CXX_FLAGS={extra_flags}",
            src,
        ]
        self._run(configure, cwd=build_dir)
        self._run([cmake, "--build", ".", "-j", "4"], cwd=build_dir)

        # Execute the upstream `testing` binary. can_run guards the actual
        # execution: when cross-compiling to a target that cannot run host
        # binaries, the tests are compiled (build pass) but not executed.
        from conan.tools.build import can_run
        if can_run(self):
            self._run([os.path.join(build_dir, "testing")], cwd=build_dir)
        else:
            self.output.warning(
                "Upstream tests compiled successfully but not executed: "
                "target binaries cannot run in this environment (can_run=False)."
            )

    def _run(self, cmd, cwd=None):
        self.output.info(f"$ {' '.join(cmd)}")
        env = dict(os.environ)
        result = subprocess.run(cmd, cwd=cwd, env=env,
                                capture_output=True, text=True)
        out = (result.stdout or "") + (result.stderr or "")
        if out.strip():
            self.output.info(out.strip())
        if result.returncode != 0:
            raise ConanException(
                f"Command failed (exit {result.returncode}): {' '.join(cmd)}\n{out}"
            )

    def package(self):
        # Install the full public header tree under include/meojson/ to match
        # upstream install layout (include/meojson/json.hpp), so consumers use
        # `#include <meojson/json.hpp>` and find_package(meojson).
        copy(
            self,
            "*",
            src=os.path.join(self.source_folder, "include"),
            dst=os.path.join(self.package_folder, "include", "meojson"),
        )
        copy(
            self,
            "LICENSE",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
        )

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "meojson")
        self.cpp_info.set_property("cmake_target_name", "meojson::meojson")
        self.cpp_info.bindirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.includedirs = ["include"]