#!/usr/bin/env python3
"""Conan recipe — xclip 0.13 (X11 剪贴板命令行工具)

Build system: autotools (configure + make)
License: GPL-2.0-only
Homepage: https://github.com/astrand/xclip

R26: 终端工具强制静态链接
依赖说明: X11 库（libX11、libXmu）和 libiconv 来自预编译包（cmd-pkgs）。
libXmu/libXt 仅作为 stub 满足 configure 检测（xclip 未直接调用）。
"""
import os

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class XclipConan(ConanFile):
    name = "xclip"
    version = "0.13"
    description = "Command line interface to X selections (clipboard)"
    license = "GPL-2.0-only"
    homepage = "https://github.com/astrand/xclip"
    url = "https://github.com/astrand/xclip"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # X11 库和 iconv 为系统预编译包，非 conan 依赖
        pass

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        # 创建 libXmu/libXt stub 头文件以满足 configure 检测
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
        # 创建 stub libXmu.a
        os.makedirs("lib", exist_ok=True)
        with open("lib/xmu_stub.c", "w") as f:
            f.write('#include <X11/Xlib.h>\n')
            f.write('Window XmuClientWindow(Display *dpy, Window win) {\n')
            f.write('    (void)dpy; return win;\n')
            f.write('}\n')
        # 编译 stub libXmu.a
        self.run("cd lib && ${CC} -c -I../include -I${DEFAULT_PREFIX}/include xmu_stub.c -o xmu_stub.o && "
                 "${AR} rcs libXmu.a xmu_stub.o")

    def generate(self):
        tc = AutotoolsToolchain(self)
        # R26: 终端工具静态链接 — 但预编译 X11 库仅有 .so（无 .a），故跳过
        # 指定 X11 头文件和库路径（预编译包位置）
        sys_prefix = os.environ.get("DEFAULT_PREFIX", "/storage/Users/currentUser/usr/local")
        tc.configure_args.append(f"--x-includes={sys_prefix}/include")
        tc.configure_args.append(f"--x-libraries={sys_prefix}/lib")
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        src_include = os.path.join(self.source_folder, "include")
        stub_lib = os.path.join(self.source_folder, "lib")
        # 通过 os.environ 传递 stub 路径和链接参数
        os.environ.setdefault("CFLAGS", "")
        os.environ["CFLAGS"] = f"-I{src_include} {os.environ['CFLAGS']}"
        os.environ.setdefault("LDFLAGS", "")
        os.environ["LDFLAGS"] = f"-L{stub_lib} {os.environ['LDFLAGS']}"
        os.environ["LIBS"] = "-liconv"
        # 在源码目录中构建（xclip Makefile 不支持 VPATH 分离构建）
        cfg_args = self._configure_args()
        self.run(f'cd "{self.source_folder}" && make clean 2>/dev/null; '
                 f'./configure {cfg_args} && make -j1', cwd=self.source_folder)

    def package(self):
        destdir = self.package_folder
        self.run(f'cd "{self.source_folder}" && make install DESTDIR="{destdir}"', cwd=self.source_folder)

    def _configure_args(self):
        sys_prefix = os.environ.get("DEFAULT_PREFIX", "/storage/Users/currentUser/usr/local")
        return f'--prefix=/ --x-includes={sys_prefix}/include --x-libraries={sys_prefix}/lib'

    def package_info(self):
        # 终端工具，无可链接库
        self.cpp_info.libs = []
        self.cpp_info.includedirs = []
        self.cpp_info.bindirs = ["bin"]
