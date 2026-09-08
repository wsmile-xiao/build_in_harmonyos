#!/usr/bin/env python3
"""Conan recipe for libdom 0.4.2 (NetSurf W3C DOM library).

libdom 是 NetSurf 浏览器组件库，上游使用 NetSurf 自有构建系统
（Makefile include $(NSSHARED)/makefiles/Makefile.tools），本平台无
netsurf-buildsystem 包。补丁 0001-Makefile.patch 将顶层 Makefile 替换为
standalone Makefile（保留原编译标志、去除 -Werror 以兼容 clang 15，
与 libparserutils / libwapcaplet / libhubbub 历史适配一致）。

Bindings 编译进同一个 libdom.a（与上游 NetSurf 构建一致）：
  - WITH_HUBBUB_BINDING=yes   -> bindings/hubbub/parser.c（HTML5 解析）
  - WITH_LIBXML_BINDING=yes   -> bindings/xml/libxml_xmlparser.c（libsvgtiny
                                  依赖 dom_xml_parser_* API；本平台无 expat，
                                  故用 libxml2 实现 XML 解析 binding）

构建：make && make install PREFIX=<package_folder>
依赖：libparserutils / libwapcaplet / libhubbub / libxml2
测试：test_package 调用 dom 核心 API + dom_xml_parser（XML binding，
      libsvgtiny 同款用法）+ dom_hubbub_parser（hubbub binding）。
"""
from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class LibdomConan(ConanFile):
    name = "libdom"
    version = "0.4.2"
    description = "W3C DOM implementation (NetSurf project)"
    license = "MIT"
    homepage = "https://www.netsurf-browser.org/projects/libdom/"
    url = ""  # CI fills this

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("libparserutils/0.2.5")
        # libwapcaplet 0.4.3.1 — 与 archives/l/libwapcaplet/0.4.3.1 对齐
        # （archives 无 0.4.3 配方；下游 libsvgtiny #7540 直接 requires 0.4.3.1）
        self.requires("libwapcaplet/0.4.3.1")
        self.requires("libhubbub/0.3.8")
        self.requires("libxml2/2.15.3.1")

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration("libdom is supported only on Linux/OHOS")
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
        compilers = self.conf.get("tools.build:compiler_executables",
                                  default={}, check_type=dict)
        cc = compilers.get("c", "clang") if compilers else "clang"
        ar = compilers.get("ar", "llvm-ar") if compilers else "llvm-ar"
        ranlib = compilers.get("ranlib", "llvm-ranlib") if compilers else "llvm-ranlib"

        # Inject dependency headers (compile time) from cpp_info
        pu = self.dependencies["libparserutils"].cpp_info
        wc = self.dependencies["libwapcaplet"].cpp_info
        hb = self.dependencies["libhubbub"].cpp_info
        xml = self.dependencies["libxml2"].cpp_info

        pu_cflags = " ".join(f"-I{d}" for d in pu.includedirs) if pu.includedirs else ""
        wc_cflags = " ".join(f"-I{d}" for d in wc.includedirs) if wc.includedirs else ""
        hb_cflags = " ".join(f"-I{d}" for d in hb.includedirs) if hb.includedirs else ""
        xml_cflags = " ".join(f"-I{d}" for d in xml.includedirs) if xml.includedirs else ""

        # R9: -j1 (HMDFS 上 make -j>1 jobserver mkfifo 报 EPERM, E074)
        self.run(
            f"make CC={cc} AR={ar} RANLIB={ranlib} "
            f"PARSERUTILS_CFLAGS='{pu_cflags}' "
            f"WAPCAPLET_CFLAGS='{wc_cflags}' "
            f"HUBBUB_CFLAGS='{hb_cflags}' "
            f"LIBXML2_CFLAGS='{xml_cflags}' -j1"
        )

    def package(self):
        # The standalone Makefile install target honours PREFIX/DESTDIR
        self.run(f"make install PREFIX={self.package_folder}")

    def package_info(self):
        self.cpp_info.libs = ["dom"]
        # Static libdom.a references symbols from all four deps
        self.cpp_info.requires = [
            "libparserutils::libparserutils",
            "libwapcaplet::libwapcaplet",
            "libhubbub::libhubbub",
            "libxml2::libxml2",
        ]
        self.cpp_info.set_property("cmake_file_name", "LibDom")
        self.cpp_info.set_property("cmake_target_name", "LibDom::dom")
        self.cpp_info.set_property("pkg_config_name", "libdom")
