#!/usr/bin/env python3
"""Conan recipe — libpar2 0.2 (Autotools, HarmonyOS PC / aarch64-linux-ohos)."""
import os

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import Autotools, AutotoolsToolchain, PkgConfigDeps
from conan.tools.layout import basic_layout


class Libpar2Conan(ConanFile):
    name = "libpar2"
    version = "0.2"
    description = "libpar2 0.2 — PAR2 (Reed-Solomon) file verification and repair library"
    license = "GPL-2.0"
    homepage = "https://github.com/parchive/libpar2"
    url = ""  # CI fills this

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("libsigc/2.12.1")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        # libpar2 configure 用 PKG_CHECK_MODULES(SIGC, sigc++-2.0) 与
        # AC_CHECK_LIB(sigc-2.0) 检查依赖，必须生成 .pc 并注入路径
        PkgConfigDeps(self).generate()
        tc = AutotoolsToolchain(self)
        # R26: System-name libraries default to static
        if not self.options.shared:
            tc.configure_args.append("--enable-static")
            tc.configure_args.append("--disable-shared")
        # 依赖注入：用 cpp_info 标准接口，不硬编码 conan 缓存路径（CI 上
        # 包目录 hash 不同，glob 会 miss）。sigc++-2.0 头目录含子目录，
        # 同时注入 include 根与 sigc++-2.0 子目录，lib 目录注入 LDFLAGS。
        _cpps = []
        _lds = []
        if "libsigc" in self.dependencies:
            _dep = self.dependencies["libsigc"]
            _pf = getattr(_dep, "package_folder", None) or ""
            for _inc in _dep.cpp_info.includedirs:
                _p = _inc if (os.path.isabs(_inc) or not _pf) else os.path.join(_pf, _inc)
                _cpps.append(_p)
            for _lib in _dep.cpp_info.libdirs:
                _p = _lib if (os.path.isabs(_lib) or not _pf) else os.path.join(_pf, _lib)
                _lds.append(_p)
        if _cpps:
            tc.configure_args.append("CPPFLAGS={}".format(
                " ".join("-I{}".format(i) for i in _cpps)))
        if _lds:
            tc.configure_args.append("LDFLAGS={}".format(
                " ".join("-L{}".format(i) for i in _lds)))
        # PkgConfigDeps 生成的 .pc 在 generators_folder，conanbuild env 未自动
        # 注入 PKG_CONFIG_PATH，显式指向 generators_folder 供 PKG_CHECK_MODULES
        _gens = self.generators_folder
        tc.configure_args.append("PKG_CONFIG_PATH={}".format(_gens))
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        autotools = Autotools(self)
        autotools.configure()
        autotools.make(args=["-j1"])

    def package(self):
        autotools = Autotools(self)
        autotools.install()
        # 上游 Makefile.am 用 `library_include_HEADERS = *.h` 的 glob 安装
        # 头文件，libtool/automake 在 OHOS 构建环境下未实际展开该 glob，
        # 导致包内 include/libpar2/ 只有 config.h，消费者无法 include
        # <libpar2/par2cmdline.h>（实测）。显式安装全部公开头文件。
        from conan.tools.files import copy
        dst = os.path.join(self.package_folder, "include", "libpar2")
        copy(self, "*.h", self.source_folder, dst, keep_path=False)

    def package_info(self):
        # autotools lib_LTLIBRARIES = libpar2.la → 产物 libpar2.a，库名是 par2
        # （find_library 会补 "lib" 前缀，填 libpar2 会错误查找 liblibpar2.a）
        self.cpp_info.libs = ["par2"]
        # 公开头文件（libpar2/par2cmdline.h 等）直接 include <sigc++/sigc++.h>，
        # libsigc 是接口依赖，必须传给下游消费者（实测缺失时消费者编译报
        # sigc++/sigc++.h not found）
        self.cpp_info.requires = ["libsigc::libsigc"]
