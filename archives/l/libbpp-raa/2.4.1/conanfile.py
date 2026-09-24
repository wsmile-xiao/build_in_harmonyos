#!/usr/bin/env python3
"""Conan recipe — libbpp-raa 2.4.1 (CMake).

Bio++ RAA：ACNUC 序列数据库访问库，是 Bio++ 家族 `bpp-core → bpp-seq → bpp-raa`
链上的一员（只依赖 bpp-seq，不依赖 bpp-phyl）。

上游构建两个目标（`bpp-raa-static` / `bpp-raa-shared`，OUTPUT_NAME 均为 `bpp-raa`，
SOVERSION=12）；**上游没有 test/ 目录、没有任何测试目标**（无 enable_testing /
BUILD_TESTING / add_test），因此本配方不做上游测试执行，仅以 test_package 的
消费者断言验证链接与公开符号。

依赖：
* `libbpp-seq/2.4.1`（`find_package(bpp-seq 12.0.0 REQUIRED)`）——已发布，包内合并了 bpp-core
* `zlib/1.3.1.1`（`find_package(ZLIB REQUIRED)`）——用 **1.3.1.1**（OHOS -fPIC 重建版），
  否则上游 `bpp-raa-shared` 链接 zlib 静态对象时因非 PIC 报重定位失败

沿用的同族结论（libbpp-phyl / libbpp-seq 逐条踩过）：
* `cmake_minimum_required(2.8.11)` 需 `CMAKE_POLICY_VERSION_MINIMUM=3.5`
* 上游 `set(CMAKE_CXX_FLAGS …)` 会覆盖 Conan 注入的 --target/--sysroot，交叉编译时
  必须改用 `CMAKE_<LANG>_COMPILER_TARGET` / `CMAKE_SYSROOT` 注入（见 E543）
* libbpp-seq 包的 CMake 导出文件引用已被裁剪的 shared .so → 下游 find_package 报错，
  需在构建内做一份剔除 shared 目标的 shim（不改依赖缓存）
* Conan 包名用 `libbpp-raa` 前缀，避免 CMakeDeps 产物遮蔽上游 bpp-raa-config.cmake
"""

import os
import re
import shutil
import subprocess

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.files import (apply_conandata_patches, copy,
                               export_conandata_patches, get)


class LibbppRaaConan(ConanFile):
    name = "libbpp-raa"
    version = "2.4.1"
    description = "Bio++ RAA: ACNUC sequence database access library"
    license = "CECILL-2.1"
    homepage = "https://github.com/BioPP/bpp-raa"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "library"

    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}

    def export_sources(self):
        export_conandata_patches(self)

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def requirements(self):
        # 公开头包含 Bpp/Seq 头，消费者编译时会用到
        self.requires("libbpp-seq/2.4.1",
                      transitive_headers=True, transitive_libs=True)
        # 上游 find_package(ZLIB)；1.3.1.1 是 OHOS -fPIC 重建版
        self.requires("zlib/1.3.1.1", transitive_headers=True, transitive_libs=True)

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.cache_variables["BUILD_SHARED_LIBS"] = bool(self.options.shared)
        tc.cache_variables["CMAKE_POSITION_INDEPENDENT_CODE"] = (
            bool(self.options.shared)
            or bool(self.options.get_safe("fPIC", True)))
        tc.cache_variables["CMAKE_POLICY_VERSION_MINIMUM"] = "3.5"
        tc.cache_variables["CMAKE_INSTALL_RPATH"] = "$ORIGIN"

        # ★ 交叉编译关键（见 E543）：上游 set(CMAKE_CXX_FLAGS …) 覆盖 --target/--sysroot
        cxxflags = self.conf.get("tools.build:cxxflags", default=[], check_type=list) or []
        cflags = self.conf.get("tools.build:cflags", default=[], check_type=list) or []
        target = next((f.split("=", 1)[1] for f in (cxxflags + cflags)
                       if f.startswith("--target=")), None)
        sysroot = next((f.split("=", 1)[1] for f in (cxxflags + cflags)
                        if f.startswith("--sysroot=")), None)
        if target:
            tc.cache_variables["CMAKE_C_COMPILER_TARGET"] = target
            tc.cache_variables["CMAKE_CXX_COMPILER_TARGET"] = target
        if sysroot:
            tc.cache_variables["CMAKE_SYSROOT"] = sysroot

        # find_package(ZLIB) 走 CMake 内置 FindZLIB 模块，用 ZLIB_ROOT 指到 conan zlib
        zlib = self.dependencies["zlib"].package_folder
        tc.cache_variables["ZLIB_ROOT"] = zlib.replace("\\", "/")
        tc.cache_variables["ZLIB_INCLUDE_DIR"] = os.path.join(zlib, "include").replace("\\", "/")
        tc.cache_variables["ZLIB_LIBRARY"] = os.path.join(zlib, "lib", "libz.a").replace("\\", "/")

        # find_package(bpp-seq) 走上游包配置（libbpp-seq 包的导出文件需先做 shim）
        seq_dir = self._bpp_seq_cmake_dir()
        if seq_dir:
            tc.cache_variables["bpp-seq_DIR"] = seq_dir
            core_dir = getattr(self, "_shim_core_dir", None)
            if core_dir:
                tc.cache_variables["bpp-core_DIR"] = core_dir
        tc.generate()
        CMakeDeps(self).generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    # ── 依赖 CMake 导出 shim（同 libbpp-phyl：不改依赖缓存）────────────────

    def _bpp_seq_cmake_dir(self):
        shim = self._prepare_cmake_shim()
        if not shim:
            return None
        preferred = os.path.join(shim, "lib", "cmake", "bpp-seq")
        if os.path.isfile(os.path.join(preferred, "bpp-seq-config.cmake")):
            self._shim_core_dir = os.path.join(shim, "lib", "cmake", "bpp-core").replace("\\", "/")
            return preferred.replace("\\", "/")
        for root, _dirs, files in os.walk(shim):
            if "bpp-seq-config.cmake" in files:
                return root.replace("\\", "/")
        return None

    def _prepare_cmake_shim(self):
        dep = self.dependencies["libbpp-seq"]
        source = getattr(dep, "package_folder", None)
        if not source:
            return None
        shim = os.path.join(self.build_folder, "libbpp-seq-shim")
        if os.path.isdir(shim):
            shutil.rmtree(shim, ignore_errors=True)
        shutil.copytree(source, shim)
        stripped = 0
        for name in ("bpp-core", "bpp-seq"):
            directory = os.path.join(shim, "lib", "cmake", name)
            if not os.path.isdir(directory):
                continue
            for entry in os.listdir(directory):
                if not entry.endswith(".cmake"):
                    continue
                path = os.path.join(directory, entry)
                if entry == f"{name}-config.cmake":
                    if self._strip_shared_from_config(path, name):
                        stripped += 1
                elif entry.startswith(f"{name}-targets"):
                    if self._strip_shared_target(path, name):
                        stripped += 1
        self.output.info(
            f"cmake shim: copied dependency package to {shim}, "
            f"stripped shared targets in {stripped} export file(s)")
        return shim

    @staticmethod
    def _strip_shared_target(path, name):
        with open(path, encoding="utf-8") as handle:
            text = handle.read()
        original = text
        text = re.sub(rf"(\bIN ITEMS\s+{re.escape(name)}-static)\s+{re.escape(name)}-shared\)",
                      r"\1)", text)
        text = re.sub(
            rf'# Create imported target {re.escape(name)}-shared\n.*?\n\)\n',
            "", text, flags=re.S)
        text = re.sub(
            rf'# Import target "{re.escape(name)}-shared".*?list\(APPEND _cmake_import_check_files_for_{re.escape(name)}-shared[^\n]*\n',
            "", text, flags=re.S)
        if text != original:
            with open(path, "w", encoding="utf-8", newline="\n") as handle:
                handle.write(text)
            return True
        return False

    @staticmethod
    def _strip_shared_from_config(path, name):
        with open(path, encoding="utf-8") as handle:
            lines = handle.readlines()
        kept = [line for line in lines if f"TARGET {name}-shared" not in line]
        kept = [line.replace(f"{name}-shared", f"{name}-static") for line in kept]
        if kept != lines:
            with open(path, "w", encoding="utf-8", newline="\n") as handle:
                handle.writelines(kept)
            return True
        return False

    # ── package ───────────────────────────────────────────────────────────

    def package(self):
        copy(self, "COPYING*", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))
        copy(self, "LICENSE*", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))
        copy(self, "LICENSES/*", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))
        cmake = CMake(self)
        cmake.install()
        self._prune_unrequested_variant()

    def _prune_unrequested_variant(self):
        import glob
        patterns = (("*.so", "*.so.*"),) if not self.options.shared else (("*.a",),)
        for libdir in (os.path.join(self.package_folder, "lib"),
                       os.path.join(self.package_folder, "lib64")):
            if not os.path.isdir(libdir):
                continue
            for group in patterns:
                for pattern in group:
                    for victim in glob.glob(os.path.join(libdir, pattern)):
                        try:
                            os.remove(victim)
                            self.output.info(
                                f"package: pruned {os.path.basename(victim)}")
                        except OSError as error:
                            self.output.warning(f"package: cannot prune {victim} ({error})")

    def package_info(self):
        self.cpp_info.libs = ["bpp-raa"]
        self.cpp_info.set_property("cmake_file_name", "libbpp-raa")
        self.cpp_info.set_property("cmake_target_name", "libbpp-raa::libbpp-raa")
        self.cpp_info.set_property("pkg_config_name", "libbpp-raa")
        self.cpp_info.requires = ["libbpp-seq::libbpp-seq", "zlib::zlib"]
        if self.settings.os in ("Linux", "OHOS"):
            self.cpp_info.system_libs.append("m")
