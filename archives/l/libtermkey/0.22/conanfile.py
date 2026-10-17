#!/usr/bin/env python3
"""Conan recipe for libtermkey 0.22 on HarmonyOS PC (aarch64).

libtermkey is a small library for processing terminal key input, supporting
both CSI sequences and the legacy 'xterm' terminfo encoding.  It uses
unibilium to read terminfo data (HAVE_UNIBILIUM path).

Build: upstream provides a plain Makefile + libtool.  CI worker has no
libtool, so this recipe compiles the three .c sources directly with the
conan-provided compiler (clang) and archives with llvm-ar — no make/libtool
dependency (consistent with libXext manual-build precedent in this repo).
Backend is pinned to unibilium (matches centerim5's dependency chain).
"""
import os

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.files import get, copy, save, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class LibtermkeyConan(ConanFile):
    name = "libtermkey"
    version = "0.22"
    description = "Terminal key handling library (CSI + terminfo backends)"
    license = "MIT"
    homepage = "https://www.leonerd.org.uk/code/libtermkey/"
    url = "https://github.com/neovim/libtermkey"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # unibilium 提供 terminfo 解析（方案 A：主后端）
        self.requires("unibilium/2.1.2")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def _unibilium_include_dir(self) -> str:
        """unibilium 包内 include 目录（编译期 -I）。"""
        dep = self.dependencies["unibilium"]
        inc = os.path.join(dep.package_folder, "include")
        if not os.path.isdir(inc):
            raise ConanException(f"unibilium include dir not found: {inc}")
        return inc

    def build(self):
        apply_conandata_patches(self)

        # R33: 从 conan conf 取编译器，不用 shell 的 ${CC}
        compilers = self.conf.get("tools.build:compiler_executables", {}, check_type=dict)
        cc = compilers.get("c", "clang")
        cc_dir = os.path.dirname(cc)
        ar = os.path.join(cc_dir, "llvm-ar") if cc_dir else "llvm-ar"
        ranlib = os.path.join(cc_dir, "llvm-ranlib") if cc_dir else "llvm-ranlib"

        inc_dir = self._unibilium_include_dir()
        src = self.source_folder

        # 手动编译三个源文件（与上游 Makefile 等价，但不依赖 libtool/make）
        cflags = f"-fPIC -O2 -Wall -std=c99 -I{inc_dir} -DHAVE_UNIBILIUM"
        objs = []
        for name in ("termkey.c", "driver-csi.c", "driver-ti.c"):
            base = name.rsplit(".", 1)[0]
            self.run(
                f"{cc} {cflags} -c {os.path.join(src, name)} -o {os.path.join(src, base + '.o')}",
                cwd=src,
            )
            objs.append(os.path.join(src, base + ".o"))

        # 归档为静态库（默认 shared=False）
        self.run(f"{ar} rcs {os.path.join(src, 'libtermkey.a')} {' '.join(objs)}", cwd=src)
        self.run(f"{ranlib} {os.path.join(src, 'libtermkey.a')}", cwd=src)

        # 可选共享库（shared=True 时）
        if self.options.shared:
            self.run(
                f"{cc} -shared -fPIC {' '.join(objs)} "
                f"-L{os.path.join(self.dependencies['unibilium'].package_folder, 'lib')} "
                f"-lunibilium -o {os.path.join(src, 'libtermkey.so')}",
                cwd=src,
            )

    def package(self):
        # 头文件
        copy(self, "termkey.h", self.source_folder,
             os.path.join(self.package_folder, "include"))
        # 静态库
        copy(self, "libtermkey.a", self.source_folder,
             os.path.join(self.package_folder, "lib"))
        # 共享库（可选）
        if self.options.shared:
            copy(self, "libtermkey.so*", self.source_folder,
                 os.path.join(self.package_folder, "lib"))
        # pkg-config 文件（手工生成等价内容）
        libdir = os.path.join(self.package_folder, "lib")
        pc = "".join([
            f"libdir={libdir}\n",
            f"includedir={os.path.join(self.package_folder, 'include')}\n",
            "\n",
            "Name: termkey\n",
            "Description: Abstract terminal key input library\n",
            f"Version: {self.version}\n",
            "Libs: -L${libdir} -ltermkey\n",
            "Cflags: -I${includedir}\n",
        ])
        save(self, os.path.join(libdir, "pkgconfig", "termkey.pc"), pc)

    def package_info(self):
        self.cpp_info.libs = ["termkey"]
        self.cpp_info.includedirs = ["include"]
        # 与 test_package/CMakeLists.txt 的 find_package(libtermkey) /
        # libtermkey::libtermkey 保持一致
        self.cpp_info.set_property("cmake_file_name", "libtermkey")
        self.cpp_info.set_property("cmake_target_name", "libtermkey::libtermkey")
        self.cpp_info.set_property("pkg_config_name", "termkey")
