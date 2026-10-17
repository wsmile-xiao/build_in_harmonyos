#!/usr/bin/env python3
"""Conan recipe — librtmp 2.4_git20190330 (raw Makefile project).

libRTMP is the RTMP/RTMPE/RTMPS/RTMPT client library of the rtmpdump
toolkit. Upstream builds with plain Makefiles (no configure step); this
recipe drives librtmp/Makefile with Conan-provided toolchain parameters
and packages the library only (the rtmpdump command line tools are out
of scope for this package).

Source: rtmpdump git master snapshot c5f04a58fc2aeea6296ca7c44ee4734c18401aa3
(upstream VERSION=v2.4, dated 2019-03-30).
"""
import os

from conan import ConanFile
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.layout import basic_layout


class LibrtmpConan(ConanFile):
    name = "librtmp"
    version = "2.4_git20190330"
    description = "RTMP client library (RTMP/RTMPE/RTMPS/RTMPT) from the rtmpdump toolkit"
    license = "LGPL-2.1-or-later"
    homepage = "https://rtmpdump.mplayerhq.hu/"
    url = "https://git.ffmpeg.org/rtmpdump.git"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
    }
    default_options = {"shared": False, "fPIC": True}

    def export_sources(self):
        export_conandata_patches(self)

    def config_options(self):
        if self.settings.os == "Windows":
            del self.options.fPIC

    def configure(self):
        if self.options.shared:
            del self.options.fPIC

    def requirements(self):
        # RTMPE/RTMPS 加密握手(CRYPTO=OPENSSL 分支)与 SWF 哈希的 SHA256
        self.requires("openssl/3.5.6")
        # hashswf.c 的 SWF 文件 zlib 解压(inflate)
        self.requires("zlib/1.3.1")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def _cc(self):
        # R33: 编译器来自 Conan conf,禁止依赖 shell 环境变量
        comp = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)
        return comp.get("c") or "clang"

    def _ar(self):
        comp = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)
        return comp.get("ar") or "ar"

    def _dep_flags(self, dep_name):
        """依赖的 include/lib 目录,直接取自 conan 依赖图(不走 pkg-config)。"""
        try:
            dep = self.dependencies[dep_name]
            cflags = " ".join(f"-I{d}" for d in dep.cpp_info.includedirs)
            ldflags = " ".join(f"-L{d}" for d in dep.cpp_info.libdirs)
            return cflags, ldflags
        except Exception:
            return "", ""

    def build(self):
        apply_conandata_patches(self)

        src = self.source_folder
        ssl_cflags, ssl_ldflags = self._dep_flags("openssl")
        zlib_cflags, zlib_ldflags = self._dep_flags("zlib")
        xcflags = f"{ssl_cflags} {zlib_cflags}".strip()
        xldflags = f"{ssl_ldflags} {zlib_ldflags}".strip()
        if not self.options.shared and self.options.fPIC:
            xcflags = f"{xcflags} -fPIC".strip()

        # 上游 Makefile 显式赋值 CC/AR/SHARED,会覆盖环境变量,必须以
        # make 命令行变量传入(放在 make 之后;VAR=x make 形式会输给
        # Makefile 内的 = 赋值,实测回退到内置规则的 gcc → Error 127)。
        # XCFLAGS/XLDFLAGS 是 Makefile 预留的追加通道,无 Makefile 内赋值。
        # R9: 仅 5 个翻译单元,-j1 足够且可复现。
        make_vars = (f"CC={self._cc()} AR={self._ar()} "
                     f"SHARED={'yes' if self.options.shared else 'no'} "
                     f"XCFLAGS=\"{xcflags}\" XLDFLAGS=\"{xldflags}\"")
        self.run(f"cd {src}/librtmp && make -j1 {make_vars} all")

    def package(self):
        src = os.path.join(self.source_folder, "librtmp")
        inc = os.path.join(self.package_folder, "include", "librtmp")
        lib = os.path.join(self.package_folder, "lib")

        # 与上游 install_base 一致:公开头文件只有这四个
        for header in ("amf.h", "http.h", "log.h", "rtmp.h"):
            copy(self, header, src, inc)

        copy(self, "librtmp.a", src, lib, keep_path=False)
        if self.options.shared:
            # librtmp.so.1(SO_VERSION=1)+ librtmp.so 链接符号链接
            copy(self, "librtmp.so*", src, lib, keep_path=False)

        copy(self, "COPYING", src, os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        # 上游 librtmp.pc 的 Cflags 为 -I{includedir}/librtmp,消费者
        # #include "rtmp.h"(头文件互相以同目录相对路径引用)
        self.cpp_info.includedirs = ["include/librtmp"]
        self.cpp_info.libs = ["rtmp"]
        # 静态消费者须继承加密与压缩依赖;OHOS 上 socket 系统调用在 libc,无额外系统库
        self.cpp_info.requires = ["openssl::openssl", "zlib::zlib"]
        self.cpp_info.set_property("cmake_file_name", "librtmp")
        self.cpp_info.set_property("cmake_target_name", "librtmp::librtmp")
        self.cpp_info.set_property("pkg_config_name", "librtmp")
