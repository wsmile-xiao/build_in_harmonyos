#!/usr/bin/env python3
"""Conan recipe — blur 1.1.3（deepin blur-effect 离屏高斯模糊工具，OHOS 适配）

上游: https://github.com/sonald/blur-effect tag 1.1.3
产物: blur_image 命令行工具（bin/blur_image，OpenGL ES 3.0 离屏渲染）

OHOS 适配要点（详见 notes.md）:
- 上游走 GBM+DRM 离屏渲染路径，OHOS 无 /dev/dri 与 libgbm——补丁 0002 改为
  EGL_DEFAULT_DISPLAY + pbuffer surface（EGL 标准 API，Linux 上同样合法）
- EGL/GLESv3 链接 OpenHarmony 平台库（clang 默认 sysroot 含头文件与 stub，
  无需 conan 依赖注入）
- gdk-pixbuf（传递 glib/libpng/libjpeg-turbo/libtiff/libwebp）来自 conan 制品仓
- 上游 cmake_minimum_required(2.8.11) 被 cmake 4.x 拒绝——补丁 0001 升至 3.10
- shader 适配 OpenHarmony GLES 严格模式（#version 首行 / texture2D→texture）
- 上游 1.1.3 无测试（N=0，清点证据见 notes.md R51 节），鸿蒙侧测试在
  test_package/（R51/R34：实际执行被测包二进制）
"""
from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import PkgConfigDeps


class BlurConan(ConanFile):
    name = "blur"
    version = "1.1.3"
    description = "Off-screen Gaussian blur image tool using OpenGL ES 3.0 (deepin blur-effect)"
    license = "GPL-3.0-or-later"
    homepage = "https://github.com/sonald/blur-effect"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # 图像编解码（PNG/JPEG 读写）经 gdk-pixbuf；传递依赖 glib/libpng/
        # libjpeg-turbo/libtiff/libwebp/zstd/zlib 由 conan 自动解析
        self.requires("gdk-pixbuf/2.44.6.1")

    def validate(self):
        # R32: 平台判断必须 in ("Linux", "OHOS")，不能 == "Linux"
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"blur supports Linux/OHOS only, got {self.settings.os}"
            )

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        # 上游 CMakeLists 用 pkg_check_modules 发现 gdk-pixbuf-2.0：
        # PkgConfigDeps 生成依赖 .pc 并将 generators 目录注入 PKG_CONFIG_PATH
        PkgConfigDeps(self).generate()
        tc = CMakeToolchain(self)
        tc.generate()

    def build(self):
        # 补丁先于 configure 应用（0001 修改 CMakeLists.txt 本身）
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()
        # 上游 1.1.3 无测试目标（CMakeLists 无 enable_testing/add_test，
        # R51 清点证据见 notes.md）——无 cmake.test() 可调

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        # application 包：仅 bin/blur_image 可执行文件，无导出库
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libs = []
