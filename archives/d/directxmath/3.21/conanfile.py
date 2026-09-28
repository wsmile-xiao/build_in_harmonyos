#!/usr/bin/env python3
"""Conan recipe — directxmath 3.21 (header-only SIMD C++ math library).

DirectXMath is Microsoft's header-only SIMD C++ math library for
DirectX-style XMVECTOR/XMMATRIX linear algebra. Nothing is compiled:
the official LIBRARY_HEADERS (Inc/*.h + Inc/*.inl) are installed as-is,
matching upstream CMake `install(FILES ${LIBRARY_HEADERS})`.

No patches are required: the header set is platform-neutral C/C++ and
works with clang 15 (aarch64-linux-ohos) out of the box.
"""
from conan import ConanFile
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.layout import basic_layout
import os


class DirectXMathConan(ConanFile):
    name = "directxmath"
    version = "3.21"
    description = "DirectXMath SIMD C++ math library (header-only, XMVECTOR/XMMATRIX linear algebra)"
    license = "MIT"
    homepage = "https://github.com/microsoft/DirectXMath"
    url = "https://github.com/microsoft/DirectXMath"

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
        # 无编译阶段（header-only）：仅应用补丁后由 package() 拷贝头文件。
        # 不得伪造编译日志（R34）。
        apply_conandata_patches(self)

    def package(self):
        # 与上游 CMakeLists.txt 的 LIBRARY_HEADERS 集合完全一致
        headers = [
            "DirectXCollision.h", "DirectXCollision.inl",
            "DirectXColors.h",
            "DirectXMath.h",
            "DirectXMathConvert.inl", "DirectXMathMatrix.inl",
            "DirectXMathMisc.inl", "DirectXMathVector.inl",
            "DirectXPackedVector.h", "DirectXPackedVector.inl",
        ]
        inc_dir = os.path.join(self.package_folder, "include")
        for h in headers:
            copy(self, h, src=os.path.join(self.source_folder, "Inc"), dst=inc_dir)
        copy(self, "LICENSE", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"), keep_path=False)

    def package_id(self):
        # 无编译产物，不依赖 os/compiler 二进制差异
        self.info.clear()

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "directxmath")
        self.cpp_info.set_property("cmake_target_name", "Microsoft::DirectXMath")
        self.cpp_info.set_property("pkg_config_name", "directxmath")
        self.cpp_info.bindirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.includedirs = ["include"]
