#!/usr/bin/env python3
"""Conan recipe — mitama-cpp-result 11.0.0 (header-library).

上游 mitama-cpp-result 11.0.0 是 Rust 风格的 C++20 Result<T, E> / Option<T>
头文件库。上游 CMakeLists.txt 用 `add_library(... INTERFACE)` + `cxx_std_20`，
install 只装 include/*.hpp 与 cmake config，无 .so/.a/.bin。

运行时依赖：fmt（panic 消息格式化，result.hpp 等头文件 `#include <fmt/core.h>`、
`<fmt/std.h>`、`<fmt/format.h>`、`<fmt/ostream.h>`、`<fmt/ranges.h>`）。
上游 test/CMakeLists.txt 要求 `find_package(fmt 9.0.0 CONFIG REQUIRED)`，本仓库
已发布的 fmt/12.2.0 满足（fmt/12.2.0 含 fmt/std.h，见 fmt 12.2.0 notes）。

0 patch：fmt/12.2.0 已提供 <fmt/std.h>，无需再裁剪上游 includes。
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import copy, get
from conan.tools.layout import basic_layout
from conan.tools.scm import Version


class MitamaCppResultConan(ConanFile):
    name = "mitama-cpp-result"
    version = "11.0.0"
    description = (
        "mitama::result<T, E> — a Rust-inspired Result type for C++20, "
        "providing explicit success/error handling without exceptions."
    )
    license = "MIT"
    homepage = "https://github.com/LoliGothick/mitama-cpp-result"
    url = "https://github.com/LoliGothick/mitama-cpp-result"
    topics = ("result", "error-handling", "rust", "header-only", "cpp20")
    package_type = "header-library"
    settings = "os", "arch", "compiler", "build_type"
    no_copy_source = True

    # ── Dependencies ────────────────────────────────────────────────────
    # 上游 result.hpp:13 `#include <fmt/std.h>` 要求 fmt >= 9.0；
    # 上游 test/CMakeLists.txt `find_package(fmt 9.0.0 CONFIG REQUIRED)`。
    # 本仓库 fmt/12.2.0 已含 fmt/std.h，满足要求，不内置/下载第二份 fmt。
    def requirements(self):
        self.requires("fmt/12.2.0")

    def configure(self):
        self.settings.compiler.cppstd = 20

    def layout(self):
        basic_layout(self, src_folder="src")

    # ── Validation ──────────────────────────────────────────────────────
    def validate(self):
        compiler = self.settings.compiler
        cppstd = compiler.get_safe("cppstd")
        if cppstd and Version(str(cppstd)) < 20:
            raise ConanInvalidConfiguration(
                f"{self.ref} requires C++20 or higher, "
                f"but compiler.cppstd is {cppstd}."
            )
        # C++20 concept support needs a recent-enough compiler
        min_versions = {
            "gcc": "10",
            "clang": "12",
            "apple-clang": "13",
            "msvc": "192",
            "Intel": "2021",
        }
        min_ver = min_versions.get(str(compiler))
        if min_ver and Version(str(compiler.version)) < min_ver:
            raise ConanInvalidConfiguration(
                f"{self.ref} needs {compiler} >= {min_ver} for C++20 concepts, "
                f"got {compiler.version}."
            )

    # ── Source ──────────────────────────────────────────────────────────
    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def package(self):
        copy(
            self,
            pattern="*.hpp",
            src=os.path.join(self.source_folder, "include"),
            dst=os.path.join(self.package_folder, "include"),
        )
        copy(
            self,
            "LICENSE",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
            keep_path=False,
        )

    # ── Package info ────────────────────────────────────────────────────
    def package_info(self):
        self.cpp_info.bindirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.set_property("cmake_file_name", "mitama-cpp-result")
        self.cpp_info.set_property("cmake_target_name", "mitama-cpp-result::mitama-cpp-result")
        self.cpp_info.includedirs = ["include"]

        # Single header-only component; propagate fmt so consumers link it.
        self.cpp_info.components["mitama"].set_property(
            "cmake_target_name", "mitama-cpp-result::mitama-cpp-result"
        )
        self.cpp_info.components["mitama"].libs = []
        self.cpp_info.components["mitama"].requires = ["fmt::fmt"]
