#!/usr/bin/env python3
"""Conan recipe — libvarlink 24.0.1 (Varlink C library + varlink CLI tool).

libvarlink 是 Varlink 协议的 C 实现（Apache-2.0/BSD-3-Clause），Meson 构建：
  - libvarlink.so.0（库）+ varlink.h（公开头）+ libvarlink.pc
  - varlink 命令行工具（R38: tool 类型，软件级 commands.json 已声明）
  - 依赖：仅系统 libm（cc.find_library('m')），无第三方 Conan 依赖

OHOS 适配（与本地 Step 2 一致，CI 可复现）：
  1. open_memstream 平台怪癖：OHOS libc 在 fclose 前必须显式 fflush，
     否则缓冲不终化（空输出）。已在 patches/ 对 scanner.c、interface.c、
     type.c、object.c、test-json.c 施加最小 fflush 补丁（见 0001-*.patch）。
  2. tool 的 program_invocation_short_name 是 GNU 扩展，OHOS libc 无声明
     也无链接符号：cli.h 增加 extern 声明、cli.c 提供 fallback 定义、
     main.c 从 argv[0] 播种（见 0001-*.patch 内 tool/ 部分）。
  Meson 工具类不加载自定义 env → build() 手动执行 meson（PATH + CC/AR）。
"""
import os

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class LibvarlinkConan(ConanFile):
    name = "libvarlink"
    version = "24.0.1"
    description = "Varlink protocol C library and command line tool (varlink.org)"
    license = ("Apache-2.0", "BSD-3-Clause")
    homepage = "https://github.com/varlink/libvarlink"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    topics = ("varlink", "rpc", "ipc", "json", "c")

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}

    def export_sources(self):
        export_conandata_patches(self)

    def config_options(self):
        if self.settings.os == "Windows":
            del self.options.fPIC

    def layout(self):
        basic_layout(self)

    def build_requirements(self):
        self.tool_requires("meson/1.11.0")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        # meson 检测 compiler/archiver 需 PATH 含 clang/llvm-ar；Meson 工具类
        # 不加载自定义 env → 由 build() 内 self.run 显式注入 PATH/CC/AR
        pass

    def build(self):
        apply_conandata_patches(self)
        self.run(
            "PATH=/data/service/hnp/bin:$PATH "
            "CC=/data/service/hnp/bin/clang "
            "AR=/data/service/hnp/bin/llvm-ar "
            "RANLIB=/data/service/hnp/bin/llvm-ranlib "
            f"meson setup {self.build_folder} {self.source_folder} "
            "--buildtype=release --prefix=/usr",
            cwd=self.build_folder,
            env="conanbuild",
        )
        self.run(
            f"PATH=/data/service/hnp/bin:$PATH meson compile -C {self.build_folder}",
            env="conanbuild",
        )

    def package(self):
        # 手动复制产物，绕开 meson install 的 HMDFS 符号链接坑
        include_dst = os.path.join(self.package_folder, "include")
        lib_dst = os.path.join(self.package_folder, "lib")
        bin_dst = os.path.join(self.package_folder, "bin")
        pcdir = os.path.join(lib_dst, "pkgconfig")
        os.makedirs(include_dst, exist_ok=True)
        os.makedirs(lib_dst, exist_ok=True)
        os.makedirs(bin_dst, exist_ok=True)
        os.makedirs(pcdir, exist_ok=True)

        src = self.source_folder
        build = self.build_folder

        copy(self, "varlink.h", src=os.path.join(src, "lib"), dst=include_dst, keep_path=False)
        # 库：libvarlink.so.0 + libvarlink.so 符号链接（构建目录内）
        for f in ("libvarlink.so.0", "libvarlink.so"):
            p = os.path.join(build, "lib", f)
            if os.path.exists(p):
                copy(self, f, src=os.path.join(build, "lib"), dst=lib_dst, keep_path=False)
        # 静态库（shared=False 时存在）
        p = os.path.join(build, "lib", "libvarlink.a")
        if os.path.exists(p):
            copy(self, "libvarlink.a", src=os.path.join(build, "lib"), dst=lib_dst, keep_path=False)
        # CLI 工具（R38）
        p = os.path.join(build, "tool", "varlink")
        if os.path.exists(p):
            copy(self, "varlink", src=os.path.join(build, "tool"), dst=bin_dst, keep_path=False)
        # pkg-config 文件
        p = os.path.join(build, "lib", "libvarlink.pc")
        if os.path.exists(p):
            copy(self, "libvarlink.pc", src=os.path.join(build, "lib"), dst=pcdir, keep_path=False)
        copy(self, "LICENSE", src=src,
             dst=os.path.join(self.package_folder, "licenses"), keep_path=False)

    def package_info(self):
        self.cpp_info.libs = ["varlink"]
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.set_property("pkg_config_name", "libvarlink")
        lib_path = os.path.join(self.package_folder, "lib")
        bin_path = os.path.join(self.package_folder, "bin")
        if os.path.isdir(bin_path):
            self.runenv_info.append_path("PATH", bin_path)
            self.buildenv_info.append_path("PATH", bin_path)
        if os.path.isdir(lib_path):
            # 消费者运行期需能加载 libvarlink.so.0（test_package env="conanrun"）
            self.runenv_info.append_path("LD_LIBRARY_PATH", lib_path)
            self.buildenv_info.append_path("LD_LIBRARY_PATH", lib_path)
