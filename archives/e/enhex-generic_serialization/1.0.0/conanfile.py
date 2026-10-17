#!/usr/bin/env python3
"""Conan recipe — generic_serialization 1.0.0 (header-only, 无构建打包族).

上游官方配方同样标注 header-only（package_id 使用 header_only()）。
本库无编译产物：include/gs/*.h 纯头文件模板库，C++17。
"""
import os
from pathlib import Path

from conan import ConanFile
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get, copy
from conan.tools.layout import basic_layout


class GenericSerializationConan(ConanFile):
    name = "enhex-generic_serialization"
    version = "1.0.0"
    description = "Lightweight and extensible generic serialization library"
    license = "MIT"
    homepage = "https://github.com/Enhex/generic_serialization"
    url = ""  # CI fills this

    package_type = "header-library"

    settings = "os", "compiler", "build_type", "arch"

    no_copy_source = True

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        # header-only: 无编译产物。校验官方头文件清单完整且非空（R34：
        # 不得伪造编译日志；此检查确认真实源树就绪，供 package()/test 使用）。
        root = Path(self.source_folder)
        expected = [
            "include/gs/binary.h",
            "include/gs/serializer.h",
            "include/gs/traits.h",
            "include/gs/binary/FILE.h",
            "include/gs/binary/fstream.h",
            "include/gs/forward/serializer.h",
        ]
        for rel in expected:
            p = root / rel
            if not p.is_file() or p.stat().st_size == 0:
                raise RuntimeError(f"missing or empty upstream header: {rel}")

    def package(self):
        # 变体 A: header-only 库（源 include/ 结构原样保留）
        copy(self, "*.h",
             src=os.path.join(self.source_folder, "include"),
             dst=os.path.join(self.package_folder, "include"),
             keep_path=True)
        copy(self, "*.hpp",
             src=os.path.join(self.source_folder, "include"),
             dst=os.path.join(self.package_folder, "include"),
             keep_path=True)
        copy(self, "LICENSE*",
             src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"),
             keep_path=False)

    def package_id(self):
        self.info.clear()  # 无构建依赖 os/compiler → 单一 package_id

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "GenericSerialization")
        self.cpp_info.set_property("cmake_target_name", "GenericSerialization::GenericSerialization")
        self.cpp_info.bindirs = []
        self.cpp_info.libdirs = []
