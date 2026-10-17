#!/usr/bin/env python3
"""Conan recipe for libgmpxx 6.3.0 — GMP 的 C++ 绑定（静态专用）.

libgmpxx 是 GMP 源码树内 C++ 接口（gmpxx.h + cxx/*.cc 非内联实现）的打包名，
不是独立上游项目，源码与 gmp 6.3.0 为同一份官方 tarball。C 接口由 gmp/6.3.0
提供，本包只安装 gmpxx.h / libgmpxx.a / libgmpxx.pc，不重复安装 libgmp 本体。
cxx/*.cc 全部 include 内部头 gmp-impl.h，必须完整 configure 后随树构建。
"""
from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class LibgmpxxConan(ConanFile):
    name = "libgmpxx"
    version = "6.3.0"
    description = "C++ bindings (mpz_class/mpq_class/mpf_class) for the GNU Multiple Precision Arithmetic Library"
    license = "LGPLv3"
    homepage = "https://gmplib.org/"
    url = "https://gmplib.org/"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    # Conan 2 要求 library 型包声明 shared 选项；本包实际静态专用：
    # libgmpxx.so 需要 libgmp.so 配套，而依赖 gmp/6.3.0 仅发布静态库，
    # 共享链需求由已发布的 gmp/6.3.0.1（--enable-cxx + shared=True）覆盖。
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def configure(self):
        if self.options.shared:
            raise ConanInvalidConfiguration(
                "libgmpxx/6.3.0 is static-only: dependency gmp/6.3.0 ships a "
                "static libgmp only, so no usable libgmpxx.so can be linked; "
                "use gmp/6.3.0.1 (--enable-cxx + shared) for the shared chain")

    def requirements(self):
        # gmpxx.h 是公开头且 #include <gmp.h>：gmp 的头文件对下游可见（visible），
        # 否则 Conan 2 CMakeDeps 对传递依赖不生成 include 目录，下游编译找不到 gmp.h
        self.requires("gmp/6.3.0", headers=True, libs=True, visible=True)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        apply_conandata_patches(self)

    def generate(self):
        tc = AutotoolsToolchain(self)
        # 与 gmp/6.3.0 完全同构的配置项 + --enable-cxx，保证 config.h 与
        # 内部符号 ABI 同源一致（cxx 对象会引用 libgmp 内部符号）
        tc.configure_args.append("--enable-static")
        tc.configure_args.append("--disable-shared")
        tc.configure_args.append("--with-pic")
        tc.configure_args.append("ABI=64")
        tc.configure_args.append("--enable-cxx")
        tc.generate()

    def build(self):
        autotools = Autotools(self)
        autotools.configure()
        # -j1：HMDFS 禁止 make 4.4 jobserver 的 mkfifo（E446 同类限制），
        # 与 archives/g/gmp/6.3.0 的先例一致
        autotools.make(args=["-j1"])
        # R51：上游 tests/cxx 22 程序在设备上以直接静态链接 harness 实跑通过
        # （22/22）；HMDFS getcwd(2) 缺陷使 libtool 链接测试可执行文件确定性失败
        # （cannot determine absolute directory name），故不纳入 in-build check，
        # 实跑记录见 reports/upstream-tests-cxx-log.md

    def package(self):
        autotools = Autotools(self)
        autotools.install()
        # 只保留 C++ 绑定产物：libgmp 本体属于 gmp/6.3.0 包，禁止双份安装；
        # .la 烤死 libdir 绝对路径，会把下游 libtool 引到 //lib 死路（gmp 6.3.0.1 同法）
        import os
        for junk in (
            os.path.join(self.package_folder, "lib", "libgmp.a"),
            os.path.join(self.package_folder, "lib", "libgmp.la"),
            os.path.join(self.package_folder, "include", "gmp.h"),
            os.path.join(self.package_folder, "lib", "pkgconfig", "gmp.pc"),
        ):
            if os.path.isfile(junk):
                os.remove(junk)
        lib_dir = os.path.join(self.package_folder, "lib")
        for root, _dirs, files in os.walk(lib_dir):
            for f in files:
                if f.endswith(".la"):
                    os.remove(os.path.join(root, f))

    def package_info(self):
        self.cpp_info.libs = ["gmpxx"]
        self.cpp_info.set_property("cmake_file_name", "gmpxx")
        self.cpp_info.set_property("cmake_target_name", "gmpxx::gmpxx")
        self.cpp_info.set_property("pkg_config_name", "gmpxx")
        # gmpxx 对象引用 libgmp 内部符号，消费方链接时必须同时链接同源 gmp
        self.cpp_info.requires = ["gmp::gmp"]
