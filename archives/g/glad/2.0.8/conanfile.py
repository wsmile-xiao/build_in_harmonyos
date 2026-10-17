#!/usr/bin/env python3
"""Conan recipe — glad 2.0.8 (generator → C loader library).

glad 2.0.8 官方仓库本质是 PyPI 工具包（glad2）：用内置的 Khronos XML specs
（glad/files/*.xml 随 tarball 携带）在构建期离线生成 C loader
（include/glad/gl.h + include/KHR/khrplatform.h + src/gl.c），
再用 OHOS 工具链把生成的 gl.c 编译为静态库 libglad.a 交付。

本配方在 build() 中调用官方生成器（python3 -m glad）产出 C 源码，因此
conandata 只声明官方 HTTPS 源（R39），生成器输出可复现（--reproducible）。
"""
import os

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches, copy
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class GladConan(ConanFile):
    name = "glad"
    version = "2.0.8"
    description = "Multi-Language GL/GLES/EGL/GLX/VK/WGL Loader-Generator (2.0 branch, generated C loader)"
    license = "MIT"
    homepage = "https://github.com/Dav1dde/glad"
    url = ""  # CI fills this

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    exports_sources = "CMakeLists.txt"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def layout(self):
        cmake_layout(self)

    def source(self):
        # 官方 HTTPS 源 + SHA-256 校验（conandata.yml）
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        # R26: 静态构建（生成器输出为单 C 源，静态库交付最稳）
        tc.variables["BUILD_SHARED_LIBS"] = "ON" if self.options.shared else "OFF"
        # 生成器输出目录（build() 中先生成再 configure）
        tc.variables["GLAD_GEN_DIR"] = os.path.join(self.build_folder, "generated")
        tc.generate()

    def _generate_c_loader(self):
        """调用官方生成器离线产出 C loader（内置 specs，--reproducible 不联网拉最新）。"""
        gen_dir = os.path.join(self.build_folder, "generated")
        # API：gl core 4.6（含全部扩展），与官方 c-generator 默认一致
        self.run(
            "python3 -m glad --api=gl:core=4.6 --out-path={out} --reproducible c".format(out=gen_dir),
            cwd=self.source_folder,
        )
        if not os.path.isfile(os.path.join(gen_dir, "include", "glad", "gl.h")):
            raise RuntimeError("glad 生成器未产出 include/glad/gl.h")
        if not os.path.isfile(os.path.join(gen_dir, "src", "gl.c")):
            raise RuntimeError("glad 生成器未产出 src/gl.c")

    def build(self):
        apply_conandata_patches(self)
        self._generate_c_loader()
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()
        # 头文件（生成器输出）：glad/gl.h 与 KHR/khrplatform.h
        gen_dir = os.path.join(self.build_folder, "generated")
        copy(self, "*.h", os.path.join(gen_dir, "include"), os.path.join(self.package_folder, "include"))
        # 库文件
        copy(self, "*.a", os.path.join(self.build_folder), os.path.join(self.package_folder, "lib"), keep_path=False)
        copy(self, "*.so", os.path.join(self.build_folder), os.path.join(self.package_folder, "lib"), keep_path=False)

    def package_info(self):
        self.cpp_info.libs = ["glad"]