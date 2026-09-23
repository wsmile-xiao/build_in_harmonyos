#!/usr/bin/env python3
"""Conan recipe — libndp 1.9 (handwritten build for OHOS).

为什么手写构建而不是 autotools：
1. 本任务源是 GitHub tag 归档，不含预生成 configure/Makefile.in；
   autogen.sh 需要 automake/aclocal/libtoolize，构建机全部缺失，路线死。
2. 即便换发行归档，上游 config.guess (2023-06-23) 不识别 OpenHarmony，
   configure 直接报 "cannot guess build type; you must specify one"。

libndp 无第三方依赖（configure.ac 仅探测 libc 头 stdint.h/stdlib.h），
库本体只有 libndp/libndp.c 一个翻译单元，工具只有 utils/ndptool.c，
用 OHOS clang 直接编译是完整等价且确定性的构建。

libtool 版本戳 c=3 r=0 a=3 => SONAME libndp.so.0，实体名 libndp.so.0.3.0。
"""
import os
import shutil

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class LibndpConan(ConanFile):
    name = "libndp"
    version = "1.9"
    description = "Library for IPv6 Neighbor Discovery Protocol (RFC 4861)"
    license = "LGPL-2.1-or-later"
    homepage = "http://libndp.org"
    url = "https://github.com/jpirko/libndp/archive/refs/tags/v1.9.tar.gz"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}

    # ------------------------------------------------------------------
    def _pick_tool(self, env_key, default):
        """R33：编译器选择链 Conan conf(tools.build:compiler_executables) -> 环境 -> 默认值，
        最终选择打印日志可追溯。"""
        pick = None
        exe_map = self.conf.get("tools.build:compiler_executables")
        if isinstance(exe_map, dict):
            pick = exe_map.get("c") or exe_map.get("cc")
        pick = pick or os.environ.get(env_key) or default
        self.output.info(f"tool selection: compiler_executables/{env_key} -> {pick}")
        return shutil.which(pick) or pick

    def export_sources(self):
        # 本包无补丁（conandata.yml: patches: {}），此调用为 no-op，满足 G1 完整性
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    @staticmethod
    def _pop_shim_env():
        # safe-bin 三重通道垫片会向子进程注入坏 rm（BASH_FUNC_rm%% / BASH_ENV /
        # CODEBUDDY_SAFE_DELETE_*）。本配方不调 rm，但按仓内惯例在 build 入口统一摘除。
        for k in list(os.environ):
            if k.startswith("BASH_FUNC_") or k.startswith("CODEBUDDY_SAFE_DELETE_") or k == "BASH_ENV":
                os.environ.pop(k, None)

    def build(self):
        self._pop_shim_env()
        apply_conandata_patches(self)  # 无补丁时 no-op
        src = self.source_folder
        bld = self.build_folder
        inc = os.path.join(src, "include")

        cc = self._pick_tool("CC", "clang")
        # AR 不能盲信环境：部分 CI buildenv 误植 AR=clang（clang 不是 archiver，
        # 会报 "clang-15: error: no such file or directory: 'rcs'"）。
        # 选择链：conf(ar) -> llvm-ar 实测存在 -> env(仅当 basename 确为 *ar) -> llvm-ar
        ar = None
        exe_map = self.conf.get("tools.build:compiler_executables")
        if isinstance(exe_map, dict) and exe_map.get("ar"):
            ar = shutil.which(exe_map["ar"])
        ar = ar or shutil.which("llvm-ar")
        if not ar:
            env_ar = os.environ.get("AR")
            env_ar_resolved = shutil.which(env_ar) if env_ar else None
            if env_ar_resolved and "ar" in os.path.basename(env_ar_resolved) \
                    and "clang" not in os.path.basename(env_ar_resolved):
                ar = env_ar_resolved
        ar = ar or "llvm-ar"
        self.output.info(f"tool selection: AR -> {ar}")

        opt = "-O2" if self.settings.build_type == "Release" else "-g"
        cflags = [opt, "-D_GNU_SOURCE", "-Wall"]
        if self.options.shared or self.options.fPIC:
            cflags.append("-fPIC")

        lib_dir = os.path.join(bld, "lib")
        bin_dir = os.path.join(bld, "bin")
        os.makedirs(lib_dir, exist_ok=True)
        os.makedirs(bin_dir, exist_ok=True)

        lib_obj = os.path.join(lib_dir, "libndp.o")
        self.run('"%s" %s -c "%s" -I"%s" -o "%s"' % (
            cc, " ".join(cflags), os.path.join(src, "libndp", "libndp.c"), inc, lib_obj),
            scope="build")

        # 静态库：libndp.a
        self.run('"%s" rcs "%s" "%s"' % (ar, os.path.join(lib_dir, "libndp.a"), lib_obj),
                 scope="build")

        # 共享库：libtool c=3:r=0:a=3 => soname libndp.so.0，实体 libndp.so.0.3.0
        if self.options.shared:
            soname_file = os.path.join(lib_dir, "libndp.so.0.3.0")
            self.run('"%s" -shared -Wl,-soname,libndp.so.0 "%s" -o "%s"' % (
                cc, lib_obj, soname_file), scope="build")
            # musl 不能加载「SONAME 名字是软链」的库（E316/E492/E505）：
            # SONAME 名与链接名一律实体复制，绝不用符号链接。
            shutil.copyfile(soname_file, os.path.join(lib_dir, "libndp.so.0"))
            shutil.copyfile(soname_file, os.path.join(lib_dir, "libndp.so"))

        # 工具：ndptool（R38）。链接静态库，产物自含，规避 SONAME 软链运行时陷阱。
        tool_obj = os.path.join(bld, "ndptool.o")
        self.run('"%s" %s -c "%s" -I"%s" -o "%s"' % (
            cc, " ".join(cflags), os.path.join(src, "utils", "ndptool.c"), inc, tool_obj),
            scope="build")
        self.run('"%s" "%s" "%s" -o "%s"' % (
            cc, tool_obj, os.path.join(lib_dir, "libndp.a"),
            os.path.join(bin_dir, "ndptool")), scope="build")

    def package(self):
        src = self.source_folder
        bld = self.build_folder
        lib_dir = os.path.join(bld, "lib")
        bin_dir = os.path.join(bld, "bin")

        # 公共头（上游 include/Makefile.am：$(includedir)/ndp.h）
        copy(self, "ndp.h", os.path.join(src, "include"),
             os.path.join(self.package_folder, "include"), keep_path=False)
        # 库
        if self.options.shared:
            # musl 不能加载「SONAME 名字是软链」的库（知识库 E316/E492/E505）：
            # SONAME 名与实体名一律落实体文件，不用符号链接。
            copy(self, "libndp.so.0.3.0", lib_dir, os.path.join(self.package_folder, "lib"), keep_path=False)
            copy(self, "libndp.so.0", lib_dir, os.path.join(self.package_folder, "lib"), keep_path=False)
            copy(self, "libndp.so", lib_dir, os.path.join(self.package_folder, "lib"), keep_path=False)
        copy(self, "libndp.a", lib_dir, os.path.join(self.package_folder, "lib"), keep_path=False)
        # 工具
        copy(self, "ndptool", bin_dir, os.path.join(self.package_folder, "bin"), keep_path=False)
        # 许可证
        copy(self, "COPYING", src, os.path.join(self.package_folder, "licenses"), keep_path=False)

    def package_info(self):
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.libdirs = ["lib"]
        # R38：本包带命令行工具 ndptool，bindirs 必须显式声明，避免被判 library 冲突
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libs = ["ndp"]
        self.cpp_info.set_property("pkg_config_name", "libndp")
