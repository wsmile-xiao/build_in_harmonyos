#!/usr/bin/env python3
"""Conan recipe — eastdc 0.0.0-fbcc34e (Electronic Arts EAStdC).

EAStdC is EA's foundational C/C++ standard library supplement: endian
swizzling, aligned allocation, random, scanf/sprintf, string/text helpers,
int128_t etc. Builds a static library via upstream CMake.

OHOS adaptation notes:
  - Upstream CMakeLists declares cmake_minimum_required(3.1); CMake >= 4.x
    removed <3.5 compat, so we set CMAKE_POLICY_VERSION_MINIMUM=3.5 and
    CMAKE_SYSTEM_NAME=Linux when os=OHOS (conan toolchain maps OHOS).
  - Library compile-time requires EABase/EAAssert/EAThread headers
    (EACallback.h/internal/Thread.h unconditionally include eathread
    headers); all three provided by published ohpcd recipes
    (eabase/0699a15, eaassert/0.0.0-e5e1812, eathread/0.0.0-f3c6c54).
  - No CLI produced (library only), so no commands.json is declared (R38).
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches


class EastdcConan(ConanFile):
    name = "eastdc"
    version = "0.0.0-fbcc34e"
    description = "EAStdC - Electronic Arts foundational C/C++ standard library supplement"
    license = "BSD-3-Clause"
    homepage = "https://github.com/electronicarts/EAStdC"
    url = ""  # CI fills this

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    generators = "CMakeDeps"

    def requirements(self):
        self.requires("eabase/0699a15")
        self.requires("eaassert/0.0.0-e5e1812")
        self.requires("eathread/0.0.0-f3c6c54")

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        if self.settings.os == "OHOS":
            tc.variables["CMAKE_SYSTEM_NAME"] = "Linux"
        tc.variables["CMAKE_POLICY_VERSION_MINIMUM"] = "3.5"
        tc.variables["EASTDC_BUILD_TESTS"] = "OFF"
        # 上游 CMakeLists 用 plain-name 链接 EABase/EAAssert/EAThread
        # （无 CMake 目标传播），纯净源码树编译时不会自动获得依赖头文件
        # include 路径，这里把已安装依赖的 include 目录注入编译标志。
        inc_flags = []
        for dep_name in ("eabase", "eaassert", "eathread"):
            dep = self.dependencies[dep_name]
            pkg = dep.package_folder
            for inc in dep.cpp_info.includedirs:
                inc_flags.append(f"-I{os.path.join(pkg, inc)}")
        if inc_flags:
            tc.variables["CMAKE_CXX_FLAGS"] = " ".join(inc_flags)
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        # Upstream CMakeLists.txt has no install() rules: mirror the upstream
        # export layout manually (public headers + built library), same
        # approach as the eaassert/0.0.0-e5e1812 recipe.
        copy(self, "*", src=os.path.join(self.source_folder, "include", "EAStdC"),
             dst=os.path.join(self.package_folder, "include", "EAStdC"))
        copy(self, "libEAStdC.a", src=self.build_folder,
             dst=os.path.join(self.package_folder, "lib"), keep_path=False)
        copy(self, "LICENSE", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"), keep_path=False)

    def package_info(self):
        self.cpp_info.libs = ["EAStdC"]
        # EAStdC public headers unconditionally include EABase/EAAssert/EAThread
        # headers, so consumers must receive those packages' include dirs too
        # (adds eaassert::eaassert/eabase::eabase/eathread::eathread to the
        # generated CMakeDeps DEPS_TARGET so the full chain propagates).
        self.cpp_info.requires = ["eabase::eabase", "eaassert::eaassert", "eathread::eathread"]
