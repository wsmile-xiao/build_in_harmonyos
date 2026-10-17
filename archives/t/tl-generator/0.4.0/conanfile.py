#!/usr/bin/env python3
"""Conan recipe — tl-generator 0.4.0 (header-only).

C++20 coroutine-based, ranges-compatible generator type (single header,
TartanLlama/generator). Header-only: no library artifact to build.
The upstream test suite (tests/test.cpp, Catch2 v2 driven) is compiled and
run in build() as the upstream-test gate, and the test_package consumer
exercises the public API on OHOS aarch64.
"""
from conan import ConanFile
from conan.errors import ConanException
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout
import os
import shutil
import subprocess

required_conan_version = ">=2.0"


class TlGeneratorConan(ConanFile):
    name = "tl-generator"
    version = "0.4.0"
    package_type = "header-library"

    description = (
        "Single-header, ranges-compatible C++20 generator type built on "
        "coroutines (TartanLlama/generator)."
    )
    homepage = "https://tl.tartanllama.xyz"
    license = "MIT"
    url = "https://github.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    topics = ("generator", "coroutine", "ranges", "header-only", "cpp20")

    # R32: settings.os 判断必须用 in ("Linux", "OHOS"); 保留四项以通过 L0p。
    settings = "os", "compiler", "build_type", "arch"

    no_copy_source = True

    def layout(self):
        basic_layout(self, src_folder="src")

    def build_requirements(self):
        # Catch2 v2 single header drives the upstream test suite; declared as a
        # tool_requires so the build resolves it from the registry reproducibly
        # instead of depending on host-side paths (R9/R33).
        self.tool_requires("catch2/2.13.10-r0")

    def package_id(self):
        # Header-only: the package is identical for every build configuration.
        self.info.clear()

    def export_sources(self):
        export_conandata_patches(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        # Apply conandata-declared patches (the OHOS iota-test adaptation) before
        # running the upstream test suite.
        apply_conandata_patches(self)
        # Header-only: nothing to link. We still compile and run the upstream
        # test suite (tests/test.cpp, Catch2 v2.13.9 single-header) as the L1
        # upstream-test gate so CI verifies the real upstream tests pass on
        # OHOS aarch64 — not merely the consumer test_package.
        #
        # OHOS toolchain note: the libc++ (15.0.4) shipped with this SDK does
        # not expose std::views::take (no __cpp_lib_ranges). The upstream
        # "iota" test case is therefore exercised with an equivalent manual
        # take loop (same assertion semantics: first 10 values of iota match
        # the running counter). All other test cases run unmodified.
        self._run_upstream_tests()

    def _run_upstream_tests(self):
        src = self.source_folder
        build_dir = os.path.join(self.build_folder, "upstream_tests")
        os.makedirs(build_dir, exist_ok=True)

        cxx = shutil.which("clang++") or shutil.which("c++") or "clang++"

        # The OHOS clang++ wrapper unconditionally injects linker flags
        # (-Wl,--code-sign -fuse-ld=lld -L...) even for compile-only (-c) steps;
        # -Wno-unused-command-line-argument silences that toolchain-injected
        # noise WITHOUT touching any test assertion or source.
        extra_flags = "-Wno-unused-command-line-argument"

        # Catch2 v2 single header comes from the tool_requires dependency.
        catch2 = self.dependencies.build.get("catch2")
        catch_include = ""
        if catch2 is not None:
            inc = getattr(catch2.cpp_info, "includedirs", None)
            if inc:
                catch_include = inc[0]
        if not catch_include or not os.path.isdir(catch_include):
            # tool_requires did not resolve a usable Catch2 include dir: fail
            # the build loudly instead of silently skipping the upstream gate
            # (R9: 禁止以"跳过测试"冒充通过).
            raise ConanException(
                "Catch2 include dir not resolvable from tool_requires; "
                "cannot run upstream test suite."
            )

        test_cpp = os.path.join(src, "tests", "test.cpp")
        main_cpp = os.path.join(build_dir, "catch.main.cpp")
        with open(main_cpp, "w") as f:
            f.write("#define CATCH_CONFIG_MAIN\n#include <catch2/catch.hpp>\n")

        cmd = [
            cxx, "-std=c++20", "-Wall", "-Wextra", extra_flags,
            "-I", os.path.join(src, "include"),
            "-I", catch_include,
            test_cpp, main_cpp, "-o", os.path.join(build_dir, "upstream_tests"),
        ]

        self._run(cmd, cwd=build_dir)
        self._run([os.path.join(build_dir, "upstream_tests")], cwd=build_dir)

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
        # Install the full public header tree: include/tl/generator.hpp
        copy(
            self,
            "tl/*.hpp",
            src=os.path.join(self.source_folder, "include"),
            dst=os.path.join(self.package_folder, "include"),
        )
        copy(
            self,
            "COPYING",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
        )

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "tl-generator")
        self.cpp_info.set_property("cmake_target_name", "tl::generator")
        self.cpp_info.bindirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.includedirs = ["include"]
