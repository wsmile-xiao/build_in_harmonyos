#!/usr/bin/env python3
"""Conan recipe for abseil 20260526.0 (LTS) — CMake build.

Abseil is the C++ common-libraries collection that protobuf, gRPC, and many
other packages depend on.  Most of it is header-only; the compiled components
(strings, status, time, synchronization, ...) ship as per-component static
libraries (`libabsl_<component>.a`).

This recipe adapts **20260526.0** as a distinct Conan package version.  The
registry also carries `abseil-cpp` (the packaging name used by protobuf/33.6),
which is a *different* Conan package name — this one keeps the historical
`absl` name used by earlier versions in this archive, so existing consumers
that reference `absl/<version>` are not disturbed.

HarmonyOS notes:
  - `ABSL_BUILD_TESTING=OFF`: the upstream test suite has 232 *_test.cc files
    (gtest) and takes a very long time to build; the recipe builds the library
    only.  Test status is reported honestly in notes.md.
  - The OHOS SDK's lld needs libxml2.so.16 from the SDK llvm/lib at link time,
    otherwise cmake's compiler link tests fail with
    "Error loading shared library libxml2.so.16".  Injecting the directory via
    LD_LIBRARY_PATH (see `environment()`).
  - `ABSL_ENABLE_INSTALL=ON` so the upstream per-component CMake package
    config (`lib/cmake/absl/abslConfig.cmake`) is installed — downstream
    packages such as gRPC find `absl::<component>` targets through it.
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.env import Environment
from conan.tools.files import get


class AbslConan(ConanFile):
    name = "absl"
    version = "20260526.0"
    description = "Abseil Common Libraries (C++)"
    license = "Apache-2.0"
    homepage = "https://abseil.io"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False]}
    default_options = {"shared": False}
    exports_sources = "conandata.yml"

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"]["absl"], strip_root=True)

    def environment(self):
        # lld 链接器运行时依赖 libxml2.so.16（OHOS SDK llvm/lib——CI 实测
        # 'Error loading shared library libxml2.so.16'——cmake 编译器链接
        # 测试失败——注入 lld 的 libxml2 依赖目录，cmake.configure 的
        # clang++ 链接测试才能通过）
        env = Environment()
        env.append_path(
            "LD_LIBRARY_PATH",
            "/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/"
            "ohos/native/llvm/lib")
        return env

    def generate(self):
        tc = CMakeToolchain(self)
        # Install the upstream per-component CMake config so downstream
        # find_package(absl CONFIG) works against this package.
        tc.variables["ABSL_ENABLE_INSTALL"] = True
        tc.variables["ABSL_PROPAGATE_CXX_STD"] = True
        # Library only: skip the (very large) gtest suite.
        tc.variables["ABSL_BUILD_TESTING"] = False
        tc.variables["BUILD_TESTING"] = False
        tc.variables["BUILD_SHARED_LIBS"] = bool(self.options.shared)
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        # Most absl components are header-only; the compiled ones are consumed
        # downstream either through the installed CMake config (absl::<comp>)
        # or by enumerating libabsl_*.a.  Keep libs empty here to preserve
        # compatibility with the existing absl/20240722.0 package, whose
        # consumers link the component archives explicitly or via CMakeDeps.
        self.cpp_info.libs = []
        if str(self.settings.os) in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["pthread"]
