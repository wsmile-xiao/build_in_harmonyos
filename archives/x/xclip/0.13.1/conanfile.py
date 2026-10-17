#!/usr/bin/env python3
"""Conan recipe — xclip 0.13.1 (X11 剪贴板命令行工具)

Build system: autotools (bootstrap + configure + make)
License: GPL-2.0-only
Homepage: https://github.com/astrand/xclip

依赖说明: X11 库为 conan 依赖（libx11/6.4.0 已发布制品仓，含 libxcb 传输层），
libXmu/libXt 仅提供 stub 满足 configure 检测（xclip 未直接调用 XmuClientWindow）。
不依赖本机预编译路径（CI worker 无本机 X11，R36 依赖必须从制品仓拉取）。

版本说明 (R37): 0.13 已在 main（PR1470, status=built, 从未 upload）。
本版本 0.13.1 为同一上游源码 (tag 0.13) 的适配修复版本：
  - 源码 URL 改为官方 codeload（原 savannah URL 已 404）
  - 修复 xclip.c 缺少 <X11/Xresource.h>（新版 libX11 6.4.0 将 Xrm 类型移入独立头文件）
  - X11 头文件/库改为 conan 依赖 libx11 + libiconv（CI worker 可拉取，R36）
  - build() 使用 Conan Toolchain 编译器编译 stub（R33，不依赖 shell 环境变量）
  - E011: HMDFS umask 077 → 022 修复（config.status 临时目录写入）
"""
import os

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import AutotoolsToolchain
from conan.tools.layout import basic_layout


class XclipConan(ConanFile):
    name = "xclip"
    version = "0.13.1"
    description = "Command line interface to X selections (clipboard)"
    license = "GPL-2.0-only"
    homepage = "https://github.com/astrand/xclip"
    url = "https://github.com/astrand/xclip"

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # X11 头文件与库来自制品仓 conan 包（CI worker 无本机预编译 X11）
        self.requires("libx11/6.4.0")
        self.requires("libiconv/1.17")
        # 显式声明传递依赖 xorgproto（R36: 已在制品仓），避免依赖 libx11 的
        # transitive_headers 行为；build() 直接访问其 include 路径（X11/X.h）
        self.requires("xorgproto/2025.1")

    def layout(self):
        basic_layout(self)

    def source(self):
        # filename 显式指定 .tar.gz: codeload URL 无扩展名, get() 无法推断格式
        get(self, **self.conan_data["sources"], strip_root=True,
            filename="xclip-0.13.tar.gz")
        # 创建 libXmu/libXt stub 头文件以满足 configure 检测（xclip 未直接调用 Xmu）
        os.makedirs("include/X11/Xmu", exist_ok=True)
        with open("include/X11/Xmu/Atoms.h", "w") as f:
            f.write('#ifndef _XMU_ATOMS_H_\n#define _XMU_ATOMS_H_\n')
            f.write('#include <X11/Xlib.h>\n#include <X11/Xatom.h>\n')
            f.write('#define XA_CLIPBOARD(dpy)  XInternAtom((dpy), "CLIPBOARD", False)\n')
            f.write('#define XA_UTF8_STRING(dpy) XInternAtom((dpy), "UTF8_STRING", False)\n')
            f.write('#endif\n')
        with open("include/X11/Intrinsic.h", "w") as f:
            f.write('#ifndef _X11_INTRINSIC_H_\n#define _X11_INTRINSIC_H_\n')
            f.write('#include <X11/Xlib.h>\n#include <X11/Xutil.h>\n')
            f.write('typedef struct _WidgetRec *Widget;\n')
            f.write('#endif\n')
        # stub libXmu.a 源文件（编译在 build() 中完成，使用 Conan Toolchain 编译器）
        os.makedirs("lib", exist_ok=True)
        with open("lib/xmu_stub.c", "w") as f:
            f.write('#include <X11/Xlib.h>\n')
            f.write('Window XmuClientWindow(Display *dpy, Window win) {\n')
            f.write('    (void)dpy; return win;\n')
            f.write('}\n')

    def generate(self):
        tc = AutotoolsToolchain(self)
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        src = self.source_folder
        x11 = self.dependencies["libx11"]
        x11_inc = os.path.join(x11.package_folder, x11.cpp_info.includedirs[0])
        x11_lib = os.path.join(x11.package_folder, x11.cpp_info.libdirs[0])
        # X11/X.h 等协议头在 xorgproto 包（libx11 依赖），xclip Makefile 编译
        # 只用 @CFLAGS@ + @X_CFLAGS@（X_CFLAGS 仅含 --x-includes 的 libx11），
        # 故需把 xorgproto include 追加到 CFLAGS
        xorg = self.dependencies["xorgproto"]
        xorg_inc = os.path.join(xorg.package_folder, xorg.cpp_info.includedirs[0])
        # 编译 stub libXmu.a（R33: 编译器/AR 来自 Conan Toolchain 的 conanbuild 环境；
        # include 路径显式从 conan 依赖收集，不依赖 $CPPFLAGS 等未定义 shell 变量）
        dep_incs = " ".join(
            f"-I{os.path.join(dep.package_folder, inc)}"
            for dep in self.dependencies.values()
            for inc in dep.cpp_info.includedirs
        )
        self.run(
            f'cd "{src}/lib" && $CC -c {dep_incs} -I"{src}/include" '
            f'xmu_stub.c -o xmu_stub.o && $AR rcs libXmu.a xmu_stub.o',
            env="conanbuild",
        )
        # codeload 源码包不含 configure，用 autoconf 直接生成
        # （configure.ac 为纯 autoconf 项目，无 automake 宏，无需 aclocal/automake；
        #   避免 autoreconf -i 依赖 CI worker 缺失的 aclocal，也避免 conan perl 工具包 ABI 冲突）
        self.run(f'cd "{src}" && autoconf', env="conanbuild")
        # E011: HMDFS 上 config.status 临时目录因 umask 077 不可写 → 改 022
        self.run(f'sed -i "s/umask 077/umask 022/g" "{src}/configure"', env="conanbuild")
        # 在源码目录内构建（xclip Makefile 不支持 VPATH 分离构建）
        # X11 include/lib 显式指向 conan 依赖 libx11（否则 X_CFLAGS 为空，make 找不到 X11/Xlib.h）
        # xclip Makefile 编译只用 @CFLAGS@ + @X_CFLAGS@（不用 @CPPFLAGS@），
        # 故全部依赖 include（libx11/xorgproto 等，含 stub 头文件）必须追加到 CFLAGS，
        # 依赖 lib 路径追加到 LDFLAGS，libXmu stub 路径也追加
        dep_libs = " ".join(
            f"-L{os.path.join(dep.package_folder, libdir)}"
            for dep in self.dependencies.values()
            for libdir in dep.cpp_info.libdirs
        )
        self.run(
            f'cd "{src}" && '
            f'CFLAGS="$CFLAGS {dep_incs} -I{src}/include" '
            f'LDFLAGS="$LDFLAGS {dep_libs} -L{src}/lib" '
            f'LIBS="-liconv" '
            f'./configure --prefix=/ --x-includes={x11_inc} --x-libraries={x11_lib} '
            f'&& make -j1',
            env="conanbuild",
        )

    def package(self):
        destdir = self.package_folder
        self.run(
            f'cd "{self.source_folder}" && make install DESTDIR="{destdir}"',
            env="conanbuild",
        )

    def package_info(self):
        # 终端工具，无可链接库；只提供 bin/（R38）
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libs = []
        self.cpp_info.includedirs = []
