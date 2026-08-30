#!/usr/bin/env python3
"""Conan recipe for libhubbub 0.3.8 (NetSurf HTML5/XML parsing library).

libhubbub 是 NetSurf 浏览器组件库，上游使用 NetSurf 自有构建系统
（Makefile include $(NSSHARED)/makefiles/Makefile.tools），本平台无
netsurf-buildsystem 包。补丁 0001-Makefile.patch 将顶层 Makefile 替换为
standalone Makefile（保留原编译标志、去除 -Werror 以兼容 clang 15，
与 libparserutils 0.2.5 / libwapcaplet 0.4.3 历史适配一致）。

构建：make && make install PREFIX=<package_folder>
依赖：libparserutils（编译期头文件 + 链接期 -lparserutils）
测试：make test 编译驱动上游 test/*.c（entities/csdetect/parser/tokeniser/
tree/tree2/tree-buf 7 个测试程序，1721 断言全过；tokeniser2/tokeniser3
依赖 json-c 本平台无，跳过）。
"""
from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class LibhubbubConan(ConanFile):
    name = "libhubbub"
    version = "0.3.8"
    description = "HTML5 compliant parsing library (NetSurf project)"
    license = "MIT"
    homepage = "https://www.netsurf-browser.org/projects/hubbub/"
    url = ""  # CI fills this

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("libparserutils/0.2.5")

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration("libhubbub is supported only on Linux/OHOS")
        if self.settings.arch != "armv8" and self.settings.os == "OHOS":
            raise ConanInvalidConfiguration("OHOS builds require armv8/aarch64")

    def layout(self):
        basic_layout(self)
        # standalone Makefile builds in-source (objects next to sources)
        self.folders.build = "."

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)

        # R33: Get compiler/linker from Conan conf, never from shell env vars
        compilers = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)
        cc = compilers.get("c", "clang") if compilers else "clang"
        ar = compilers.get("ar", "llvm-ar") if compilers else "llvm-ar"
        ranlib = compilers.get("ranlib", "llvm-ranlib") if compilers else "llvm-ranlib"

        # libparserutils dependency: pass headers (compile) and libs (test link)
        dep = self.dependencies["libparserutils"]
        pu_cflags = " ".join(f"-I{d}" for d in dep.cpp_info.includedirs) if dep.cpp_info.includedirs else ""
        pu_ldflags = " ".join(f"-L{d}" for d in dep.cpp_info.libdirs) if dep.cpp_info.libdirs else ""
        pu_libs = " ".join(f"-l{l}" for l in dep.cpp_info.libs) if dep.cpp_info.libs else ""
        # R9: -j1 (HMDFS 上 make -j>1 jobserver mkfifo 报 EPERM, E074)
        self.run(
            f"make CC={cc} AR={ar} RANLIB={ranlib} "
            f"PARSERUTILS_CFLAGS='{pu_cflags}' "
            f"PARSERUTILS_LIBS='{pu_ldflags} {pu_libs}' -j1"
        )

    def package(self):
        # The standalone Makefile install target honours PREFIX/DESTDIR
        self.run(f"make install PREFIX={self.package_folder}")

    def package_info(self):
        self.cpp_info.libs = ["hubbub"]
        self.cpp_info.requires = ["libparserutils::libparserutils"]
        self.cpp_info.set_property("cmake_file_name", "LibHubbub")
        self.cpp_info.set_property("cmake_target_name", "LibHubbub::hubbub")
        self.cpp_info.set_property("pkg_config_name", "libhubbub")
