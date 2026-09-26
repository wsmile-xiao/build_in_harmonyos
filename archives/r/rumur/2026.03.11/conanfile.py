#!/usr/bin/env python3
"""
Conan recipe for rumur v2026.03.11 — OHOS (OpenHarmony) aarch64 adaptation.

Rumur is a model checker for Murphi security protocol models.
Upstream: https://github.com/Smattr/rumur

Build system: CMake (C99 + C++11)
Dependencies:
  - gmp/6.3.0.1 (libgmp + libgmpxx for arbitrary precision arithmetic)
Build tools:
  - bison/3.8.2 (parser generator)
  - flex/2.6.4.2 (lexer generator)

OHOS fixes:
  1. gzip is busybox, no --to-stdout flag → use -c
  2. bison needs BISON_PKGDATADIR set to find m4sugar.m4
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches, replace_in_file


class RumurConan(ConanFile):
    name = "rumur"
    version = "2026.03.11"
    description = "Rumur model checker for Murphi security protocol models"
    license = "Unlicense"
    homepage = "https://github.com/Smattr/rumur"
    url = "https://github.com/Smattr/rumur"

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"
    # package_type = "application"：CLI 工具包不使用 shared 选项。
    # 两者并存时 Conan 会发 "package_type will have precedence over the options"
    # 警告，且该选项对本包无任何作用。
    options = {"fPIC": [True, False]}
    default_options = {"fPIC": True}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("gmp/6.3.0.1")

    def build_requirements(self):
        self.tool_requires("bison/3.8.2")
        self.tool_requires("flex/2.6.4.2")
        self.tool_requires("m4/1.4.19")

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        apply_conandata_patches(self)
        # Fix 1: OHOS gzip is busybox, no --to-stdout flag
        # 仅在确实含该 pattern 的文件上调用 replace_in_file：strict=False 对
        # 未命中的文件同样会打印 "didn't find pattern" 警告（每次构建 40+ 条噪声）
        _gzip_old = "gzip -9 --no-name --to-stdout"
        for root, dirs, files in os.walk(self.source_folder):
            for f in files:
                if f != "CMakeLists.txt":
                    continue
                path = os.path.join(root, f)
                try:
                    with open(path, "r", encoding="utf-8", errors="replace") as fh:
                        if _gzip_old not in fh.read():
                            continue
                except OSError:
                    continue
                replace_in_file(self, path, _gzip_old, "gzip -9 -c", strict=False)
        # Fix 2: Add flex include dir to librumur's PUBLIC include dirs
        # so consumers that #include <rumur/scanner.h> can find FlexLexer.h
        flex_inc = os.path.join(
            self.dependencies.build["flex"].package_folder, "include"
        )
        librumur_cmake = os.path.join(self.source_folder, "librumur", "CMakeLists.txt")
        replace_in_file(
            self,
            librumur_cmake,
            "  PUBLIC\n  $<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}/include>\n  $<INSTALL_INTERFACE:include>",
            f"  PUBLIC\n  $<BUILD_INTERFACE:${{CMAKE_CURRENT_SOURCE_DIR}}/include>\n  $<INSTALL_INTERFACE:include>\n  {flex_inc}",
            strict=False,
        )

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["CMAKE_POLICY_VERSION_MINIMUM"] = "3.5"
        # Set RPATH so the binary can find libgmp.so / libgmpxx.so in ../lib
        tc.variables["CMAKE_BUILD_RPATH"] = "$ORIGIN/../lib"
        tc.variables["CMAKE_INSTALL_RPATH"] = "$ORIGIN/../lib"
        # Fix 2: Set BISON_PKGDATADIR so bison can find its data files
        bison_pkg = self.dependencies.build["bison"].package_folder
        bison_data = os.path.join(bison_pkg, "share", "bison")
        if os.path.isdir(bison_data):
            os.environ["BISON_PKGDATADIR"] = bison_data
        # Fix 3: Ensure FLEX_INCLUDE_DIR is found
        flex_pkg = self.dependencies.build["flex"].package_folder
        flex_inc = os.path.join(flex_pkg, "include")
        if os.path.isdir(flex_inc):
            tc.variables["FLEX_INCLUDE_DIR"] = flex_inc
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()
        # OHOS musl does not resolve SONAME symlinks at runtime.
        # Materialize the gmp SONAME files into the rumur package's lib
        # so the binary can find libgmp.so.10 / libgmpxx.so.4 at load time.
        import shutil
        gmp_pkg = self.dependencies["gmp"].package_folder
        gmp_lib = os.path.join(gmp_pkg, "lib")
        my_lib = os.path.join(self.package_folder, "lib")
        os.makedirs(my_lib, exist_ok=True)
        for soname in ("libgmp.so.10", "libgmpxx.so.4"):
            src_link = os.path.join(gmp_lib, soname)
            if os.path.islink(src_link):
                real = os.path.realpath(src_link)
                dst = os.path.join(my_lib, soname)
                shutil.copy2(real, dst)

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.includedirs = []
        # 工具类包：显式声明 bindirs（code-style 第 40 条 "工具类必须设置
        # cpp_info.bindirs"）。Conan 2 的 CppInfo 默认已是 ["bin"]，此处显式
        # 写出以符合规范；同时替代 Conan 1.x 已废弃的 env_info（Conan 2 下
        # env_info 只是发出 deprecation 警告的空壳，消费方通过 VirtualRunEnv
        # 从 bindirs 继承 PATH）。
        self.cpp_info.bindirs = ["bin"]
