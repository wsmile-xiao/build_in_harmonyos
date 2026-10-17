#!/usr/bin/env python3
"""Conan recipe for libnpy 1.0.1 — header-only C++ reader/writer for .npy files.

libnpy is header-only: the root meson.build only calls declare_dependency()
(no build targets, no install rules — meson install would be empty), so
package() copies include/npy.hpp into the standard include/ layout directly
(same approach as CLI11 2.7.2).

Upstream tests (tests/: Catch2 test-read + smoke test-write, meson project)
are run natively per workflow Step 2 (`cd tests && meson setup builddir &&
meson test -C builddir`), evidence archived in reports/ — see notes.md.
build() is intentionally a no-op (there is no library to compile); consumer
verification is test_package (8 named checks: write/read roundtrip, magic
bytes, descr, fortran_order, scalar/empty shapes).
"""
import os

from conan import ConanFile
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.layout import basic_layout


class LibnpyConan(ConanFile):
    name = "libnpy"
    version = "1.0.1"
    description = "libnpy — header-only C++14 reader and writer for the NumPy .npy format"
    license = "MIT"
    homepage = "https://github.com/llohse/libnpy"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "header-library"
    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        # header-only：根 meson.build 仅 declare_dependency()，无编译目标。
        # 上游 tests/（Catch2）按 SKILL Step 2 原生运行，证据见 notes.md 与 PR 正文。
        # patches 为空，apply_conandata_patches 为 no-op（G1 完整性要求保留调用）。
        apply_conandata_patches(self)

    def package(self):
        # root meson.build has no install_headers() — copy the single header
        copy(self, "npy.hpp",
             src=os.path.join(self.source_folder, "include"),
             dst=os.path.join(self.package_folder, "include"))
        copy(self, "LICENSE",
             src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "libnpy")
        self.cpp_info.set_property("cmake_target_name", "libnpy::libnpy")
        self.cpp_info.libs = []
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.bindirs = []
        self.cpp_info.libdirs = []
