#!/usr/bin/env python3
"""Conan recipe for cqrlib 1.1.4 (CQRlib, Herbert J. Bernstein / yayahjb).

CQRlib 是四元数/旋转计算 C 库（外加 #ifdef __cplusplus 下的 header-only C++
模板实现）：四元数创建/乘除/共轭/范数/插值(SLERP/HLERP)/轴角转换等。纯 C99，
仅依赖 libm，零第三方依赖（W0 预检通过）。

OHOS 适配要点：
- 上游无 CMake/autotools，只有一份面向 libtool 的手写 Makefile（依赖 libtool
  + 默认装到 $HOME，不适合沙箱）。本配方不走上游 Makefile，直接在 build()
  内用 conan conf 的编译器编译 cqrlib.c 并打包（与仓内零构建系统小库同模式）。
- 上游测试：make tests = 编译运行 CQRlibTest.c（C API，自检 errorcount 返回）
  与 CPPQRTest.cpp（C++ header 模板，不链库）并 diff 期望输出；但 tarball 内
  *_orig.lst 是 0 字节占位 → diff 判据不可用，实质判据为程序自检返回值。
  build() 内直接编译实跑这两个测试（exit!=0 即失败）。
- CPPQRTest 按上游 Makefile 语义不链接库（模板实现全在头文件）。
"""
from conan import ConanFile
from conan.tools.files import copy, get
import os


class CqrlibConan(ConanFile):
    name = "cqrlib"
    version = "1.1.4"
    description = "CQRlib - an ANSI C API for quaternion arithmetic and rotation"
    license = "LGPL-2.1-or-later"
    homepage = "https://github.com/yayahjb/cqrlib"
    url = ""  # CI fills this
    topics = ("quaternion", "rotation", "math", "crystallography")

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}

    def config_options(self):
        if self.settings.os == "Windows":
            del self.options.fPIC

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")
        self.settings.rm_safe("compiler.cppstd")
        self.settings.rm_safe("compiler.libcxx")

    def layout(self):
        pass

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def _cc(self, lang="c"):
        compilers = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)
        default = "clang" if lang == "c" else "clang++"
        return compilers.get(lang, default) if compilers else default

    def build(self):
        src = self.source_folder
        fpic = "-fPIC" if self.options.get_safe("fPIC") else ""
        cc = self._cc("c")
        cxx = self._cc("cpp")
        # 库本体（绕过上游 libtool Makefile，直接编译）
        self.run(f"{cc} -O2 {fpic} -I{src} -c {os.path.join(src, 'cqrlib.c')} -o cqrlib.o")
        if self.options.shared:
            self.run(f"{cc} -shared -o libCQRlib.so cqrlib.o -lm")
        else:
            self.run("ar rcs libCQRlib.a cqrlib.o")
        # 层1 上游官方测试实跑（exit 自检，errorcount!=0 即非零返回）
        libdir = os.path.abspath(self.build_folder)
        libname = "CQRlib.so" if self.options.shared else "CQRlib.a"
        self.run(
            f"{cc} -O2 -I{src} {os.path.join(src, 'CQRlibTest.c')} "
            f"{os.path.join(libdir, 'lib' + libname)} -lm -o CQRlibTest"
        )
        self.run("./CQRlibTest")
        # C++ 模板测试：按上游 Makefile 语义不链库（实现全在 cqrlib.h 模板内）
        self.run(f"{cxx} -O2 {fpic} -I{src} {os.path.join(src, 'CPPQRTest.cpp')} -lm -o CPPQRTest")
        self.run("./CPPQRTest")

    def package(self):
        copy(self, "cqrlib.h", src=self.source_folder, dst=os.path.join(self.package_folder, "include"))
        copy(self, "lgpl.txt", src=self.source_folder, dst=os.path.join(self.package_folder, "licenses"))
        copy(self, "*.a", src=self.build_folder, dst=os.path.join(self.package_folder, "lib"), keep_path=False)
        copy(self, "*.so", src=self.build_folder, dst=os.path.join(self.package_folder, "lib"), keep_path=False)

    def package_info(self):
        self.cpp_info.libs = ["CQRlib"]
        self.cpp_info.system_libs = ["m"]
