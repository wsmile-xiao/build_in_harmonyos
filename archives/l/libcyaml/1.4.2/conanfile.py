#!/usr/bin/env python3
"""Conan recipe for libcyaml 1.4.2 — plain Makefile build (no configure).

libcyaml is a C11 YAML parsing/serialising library built with a raw Makefile.
It depends on libyaml (pkg-config name yaml-0.1). The Makefile only invokes
pkg-config when PKG_CONFIG is set; we instead inject the dependency include
and library paths via CPPFLAGS/LDFLAGS (R49: build-folder private prefix).

R32: os check must use `in ("Linux", "OHOS")`, not `== "Linux"`.
"""
import os

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class LibcyamlConan(ConanFile):
    name = "libcyaml"
    version = "1.4.2"
    description = "YAML schema validation and parsing/serialising in C"
    license = "ISC"
    homepage = "https://github.com/tlsa/libcyaml"
    url = "https://github.com/tlsa/libcyaml"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("libyaml/0.2.5")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        libyaml = self.dependencies["libyaml"]
        inc = os.path.join(libyaml.package_folder, libyaml.cpp_info.includedirs[0])
        libd = os.path.join(libyaml.package_folder, libyaml.cpp_info.libdirs[0])
        cppflags = f"-I{inc}"
        ldflags = f"-L{libd} -lyaml"
        # Raw Makefile build; CPPFLAGS/LDFLAGS carry the libyaml dependency
        # (R49: build-folder private prefix). Run in the source folder where
        # the Makefile lives (basic_layout puts the build cwd in build-release/),
        # and no -j jobserver (mkfifo restricted on this filesystem).
        # Injection via environment, NOT make command line: the Makefile uses
        # `CPPFLAGS += $(VERSION_FLAGS)`; a command-line CPPFLAGS would override
        # the += and drop -DVERSION_* defines. Env vars are appended to instead.
        self.run(
            f"CPPFLAGS='{cppflags}' LDFLAGS='{ldflags}' "
            f"make -C {self.source_folder} VARIANT=release CC=clang AR=llvm-ar")

    def package(self):
        dest = self.package_folder
        build_dir = os.path.join(self.source_folder, "build/release")
        copy(self, "cyaml/*.h", os.path.join(self.source_folder, "include"),
             os.path.join(dest, "include"))
        if self.options.shared:
            copy(self, "*.so*", build_dir, os.path.join(dest, "lib"))
        else:
            copy(self, "libcyaml.a", build_dir, os.path.join(dest, "lib"))
        # libcyaml.pc 由上游 Makefile 在 install 时生成，纯 make 构建不产出；
        # 包内元数据由 cpp_info 提供，无需手工 copy .pc

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "libcyaml")
        self.cpp_info.set_property("cmake_target_name", "libcyaml::libcyaml")
        self.cpp_info.libs = ["cyaml"]
        if self.settings.os in ("OHOS", "Linux"):
            self.cpp_info.system_libs = ["m"]