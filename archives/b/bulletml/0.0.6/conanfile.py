#!/usr/bin/env python3
"""Conan recipe — bulletml 0.0.6 (libBulletML)

C++ library to handle BulletML (Bullet Markup Language), the format used to
describe bullet patterns in shooting games.

Build system: plain Makefile (no configure). The Makefile lives in src/ and:
  - compiles library objects with $(CC)/$(CXX)
  - recurses into tinyxml/ (bundled) to build its objects
  - archives libbulletml.a with $(AR)

The tinyxml sub-Makefile hardcodes `LD := g++`; passing LD=<cxx> on the make
command line overrides it, so no source patch is required for the OHOS toolchain.
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import copy, get, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class BulletmlConan(ConanFile):
    name = "bulletml"
    version = "0.0.6"
    description = "C++ library to handle BulletML (Bullet Markup Language) — bullet patterns for shooting games"
    license = "custom:libbulletml"
    homepage = "http://shinh.skr.jp/libbulletml/index_en.html"
    url = ""  # CI fills this

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    # R32: OHOS platform compatibility
    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(f"Unsupported OS: {self.settings.os}")
        # Upstream ships only a static libbulletml.a (no shared target)
        if self.options.shared:
            raise ConanInvalidConfiguration("bulletml/0.0.6 provides only a static library (no shared target upstream)")

    def requirements(self):
        pass

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        # 上游 tarball 把真正的库放在顶层目录的 src/ 子目录（顶层只有 README/
        # bulletml.h/*.dsp 等）。init-build/refresh-patch 以 src/ 内容为工作根生成
        # 补丁路径，这里把 src/ 内容上移一层，使补丁路径与解包布局一致。
        src_dir = os.path.join(self.source_folder, "src")
        if os.path.isdir(src_dir):
            for item in os.listdir(src_dir):
                src_item = os.path.join(src_dir, item)
                dst_item = os.path.join(self.source_folder, item)
                if os.path.exists(dst_item):
                    os.remove(dst_item)
                os.rename(src_item, dst_item)
            os.rmdir(src_dir)

    def build(self):
        apply_conandata_patches(self)
        # R33: get compilers from Conan conf, never bare shell env vars
        comp_execs = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)
        cc = comp_execs.get("c") or "clang"
        cxx = comp_execs.get("cpp") or "clang++"
        self.run(f'make -C "{self.source_folder}" -j1 CC="{cc}" CXX="{cxx}" LD="{cxx}"')

    def package(self):
        src = self.source_folder
        copy(self, "*.a", src=src, dst=os.path.join(self.package_folder, "lib"))
        # Public headers (README.en documents include "bulletml/bulletmlparser.h")
        for hdr in ("bulletmlparser.h", "bulletmlparser-tinyxml.h", "bulletmlparser-xerces.h",
                    "bulletmlparser-ygg.h", "bulletmlrunner.h", "bulletmlrunnerimpl.h",
                    "bulletmltree.h", "bulletmlcommon.h", "bulletmlerror.h", "calc.h",
                    "formula.h", "formula-variables.h", "tree.h", "auto_ptr_fix.h"):
            copy(self, hdr, src=src, dst=os.path.join(self.package_folder, "include", "bulletml"))
        # Public header bulletmlrunner.h uses boost::shared_ptr; ship the bundled
        # minimal boost headers so consumers can compile without an external boost.
        copy(self, "*.hpp", src=os.path.join(src, "boost"), dst=os.path.join(self.package_folder, "include", "boost"))
        copy(self, "*.h", src=os.path.join(src, "boost"), dst=os.path.join(self.package_folder, "include", "boost"))
        copy(self, "config", src=os.path.join(src, "boost"), dst=os.path.join(self.package_folder, "include", "boost"))
        copy(self, "detail", src=os.path.join(src, "boost"), dst=os.path.join(self.package_folder, "include", "boost"))
        # Public headers bulletmlparser-tinyxml.h / bulletmlparser-ygg.h include
        # "tinyxml/tinyxml.h" / "ygg/ygg.h"; ship the bundled parser headers too.
        copy(self, "tinyxml.h", src=os.path.join(src, "tinyxml"), dst=os.path.join(self.package_folder, "include", "tinyxml"))
        copy(self, "ygg.h", src=os.path.join(src, "ygg"), dst=os.path.join(self.package_folder, "include", "ygg"))

    def package_info(self):
        self.cpp_info.libs = ["bulletml"]