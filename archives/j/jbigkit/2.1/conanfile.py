#!/usr/bin/env python3
"""Conan recipe — jbigkit 2.1 (Makefile, 静态库)"""
import os

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class JbigkitConan(ConanFile):
    name = "jbigkit"
    version = "2.1"
    description = "JBIG-KIT lossless image compression library (ITU-T T.82)"
    license = "GPL-2.0-or-later"
    homepage = "https://www.cl.cam.ac.uk/~mgk25/jbigkit/"
    package_type = "static-library"
    settings = "os", "compiler", "build_type", "arch"
    options = {"fPIC": [True, False]}
    default_options = {"fPIC": True}

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def layout(self):
        basic_layout(self, src_folder=".")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        # jbigkit 是手写 Makefile（非 cmake/autotools/meson）：libjbig/ 下 make 出 libjbig.a（jbig.o+jbig_ar.o，静态）。
        # 两处 OHOS 适配：① Makefile 里 ar/ranlib 是硬编码（非 $(AR)），须替成 hnp 的 llvm-ar/llvm-ranlib；
        # ② CC 走 conan conf（hnp clang），CFLAGS 命令行覆盖并加 -fPIC（静态库要能链进 libtiff.so 等共享库）。
        apply_conandata_patches(self)
        cc = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict).get(
            "c", "/data/service/hnp/bin/clang")
        libjbig = os.path.join(self.source_folder, "libjbig")
        mk = os.path.join(libjbig, "Makefile")
        with open(mk, encoding="utf-8") as f:
            txt = f.read()
        txt = (txt.replace("ar rc", "/data/service/hnp/bin/llvm-ar rc")
                  .replace("ranlib ", "/data/service/hnp/bin/llvm-ranlib "))
        with open(mk, "w", encoding="utf-8") as f:
            f.write(txt)
        # 只编 libjbig.a（跳过 jbig85 / tstcodec 测试程序；libtiff 只用 T.82 的 libjbig）
        self.run('make -C "{}" CC="{}" CFLAGS="-fPIC -O2" libjbig.a'.format(libjbig, cc))

    def package(self):
        libjbig = os.path.join(self.source_folder, "libjbig")
        copy(self, "libjbig.a", src=libjbig, dst=os.path.join(self.package_folder, "lib"))
        for h in ("jbig.h", "jbig_ar.h"):
            copy(self, h, src=libjbig, dst=os.path.join(self.package_folder, "include"))

    def package_info(self):
        self.cpp_info.libs = ["jbig"]
        self.cpp_info.includedirs = ["include"]
        # libtiff 走 find_package(JBIG)
        self.cpp_info.set_property("cmake_file_name", "JBIG")
        self.cpp_info.set_property("cmake_target_name", "JBIG::JBIG")
