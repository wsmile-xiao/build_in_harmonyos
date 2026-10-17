#!/usr/bin/env python3
"""freetype 2.14.3.2.1 — HarmonyOS PC 适配（autotools）。

版本说明：main 已有 2.14.3 / 2.14.3.1 两版归档且已入制品仓（R37），
本版递增为 2.14.3.2.1，上游源码仍为 freetype 2.14.3 发行包。
"""
import os

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class FreetypeConan(ConanFile):
    name = "freetype"
    version = "2.14.3.2.1"
    description = "Free, high-quality font rendering engine supporting TrueType, OpenType, CFF and others"
    license = "FreeType-License OR GPL-2.0"
    homepage = "https://freetype.org/"
    url = ""  # CI fills this

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": True}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # 零外部依赖：zlib/bzip2/png/brotli/harfbuzz 全部禁用。
        # harfbuzz 与 freetype 循环依赖，必须先建无 hb 版 freetype（软件级 README 既定策略）。
        pass

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        if not self.options.shared:
            tc.configure_args.append("--enable-static")
            tc.configure_args.append("--disable-shared")
        # OHOS: freetype 的 builds/unix/detect.mk 自动检测用默认 cc 而非
        # clang（CI #29062: "C compiler cannot create executables" Error 77）。
        # 参照 libxext 先例注入编译器/工具环境变量。
        if str(self.settings.os) == "OHOS":
            env = tc.environment()
            shell = "/data/service/hnp/bin/bash"
            env.define_path("SHELL", shell)
            env.define_path("CONFIG_SHELL", shell)
            env.define_path("CC", "/data/service/hnp/bin/clang")
            env.define_path("CXX", "/data/service/hnp/bin/clang++")
            env.define_path("LD", "/data/service/hnp/bin/ld.lld")
            env.define_path("AR", "/data/service/hnp/bin/llvm-ar")
            env.define_path("RANLIB", "/data/service/hnp/bin/llvm-ranlib")
            env.define_path("STRIP", "/data/service/hnp/bin/llvm-strip")
            env.define_path("NM", "/data/service/hnp/bin/llvm-nm")
            # toybox install（ELF）：AC_PROG_INSTALL 找到它即 INSTALL=/system/bin/install -c，
            # 避免回退到 install-sh 脚本（HMDFS 禁止直接 exec 脚本，见 build() 注释）
            env.append_path("PATH", "/system/bin")
        # 禁全部可选依赖（与 main 既有两版归档一致的零依赖叶子策略）
        tc.configure_args.append("--with-zlib=no")
        tc.configure_args.append("--with-bzip2=no")
        tc.configure_args.append("--with-png=no")
        tc.configure_args.append("--with-harfbuzz=no")
        tc.configure_args.append("--with-brotli=no")
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        # HMDFS 用户存储禁止直接 exec shebang 脚本（与 x 位无关，chmod 也不生效，
        # E046 同源）：conan 的 autotools.configure() 直接 exec 顶层 configure 会报
        # Error 126 Permission denied。改为经 sh 显式调用；configure 链路的后续
        # 脚本调用点（detect.mk 内层 configure、libtool）由 patches/0004-0005 统一
        # 改为 $(SHELL) 前缀（与 libtool 官方标准形式一致），config.guess/config.sub/
        # config.status 上游本身即经 $SHELL 调用，不受影响。
        # 参数与 conan Autotools.configure() 默认完全一致。
        cfg = os.path.join(self.source_folder, "configure")
        # conan 的 autotools.install() 以 DESTDIR=<package_folder> 执行 make install，
        # 故 configure 的 prefix 必须是 /（与 conan Autotools 默认一致），
        # 否则安装路径翻倍（DESTDIR+prefix 嵌套，头/库落错位置）
        args = ["--prefix=/"]
        args += ["'--bindir=${prefix}/bin'", "'--sbindir=${prefix}/bin'",
                 "'--libdir=${prefix}/lib'", "'--includedir=${prefix}/include'",
                 "'--oldincludedir=${prefix}/include'"]
        if self.options.shared:
            args += ["--enable-shared", "--disable-static"]
        else:
            args += ["--enable-static", "--disable-shared"]
        # 禁全部可选依赖（与 generate() 的 configure_args 一致）
        args += ["--with-zlib=no", "--with-bzip2=no", "--with-png=no",
                 "--with-harfbuzz=no", "--with-brotli=no"]
        self.run("sh '{}' {}".format(cfg, " ".join(args)), env="conanbuild")
        autotools = Autotools(self)
        # 固定 -j1 串行构建：真机 GNU Make 4.4.1 并行编译会静默失败（无诊断退出）
        autotools.make(args=["-j1"])

    def package(self):
        autotools = Autotools(self)
        # -j1 同 build()：真机 make -jN 会走 jobserver mkfifo（HMDFS EPERM）+ 并行静默失败
        autotools.install(args=["-j1"])

    def package_info(self):
        self.cpp_info.libs = ["freetype"]
        # freetype 头装在 include/freetype2/（ft2build.h + freetype/*.h），非标准 include/ 根。
        self.cpp_info.includedirs = ["include/freetype2", "include"]
        # freetype2.pc 的 Version 是 libtool 号（version_info=26:6:20 → 26.6.20），
        # 非 release 2.14.3；fontconfig/cairo 按此判 `freetype2 >= 21.0.15`，
        # conan 默认写 recipe 版本 2.14.3.2.1 会判假。
        self.cpp_info.set_property("system_package_version", "26.6.20")
        self.cpp_info.set_property("cmake_file_name", "freetype")
        self.cpp_info.set_property("cmake_target_name", "freetype::freetype")
        self.cpp_info.set_property("pkg_config_name", "freetype2")
