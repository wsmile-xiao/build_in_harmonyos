#!/usr/bin/env python3
"""Conan recipe — uvwasi 0.0.23 (cmake)

OHOS 适配要点：
- 依赖 libuv/1.52.1@ohpcd/stable（已发布）。补丁 0001 让上游 CMakeLists 改用
  Conan 的 libuv config 目标（libuv::libuv），绕开其自带 FindLIBUV.cmake +
  FetchContent 网络回退，离线消费已发布的 libuv。
- 补丁 0002 把 HarmonyOS 与 Linux 同等对待，补上 _GNU_SOURCE / _POSIX_C_SOURCE
  特性宏（OHOS 下 conan 不写 CMAKE_SYSTEM_NAME=Linux）。
- 补丁 0003 仅构建静态库 uvwasi_a，避免 OHOS 共享库代码签名要求。
"""
from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.cmake import CMake, CMakeToolchain, CMakeDeps, cmake_layout


class UvwasiConan(ConanFile):
    name = "uvwasi"
    version = "0.0.23"
    description = "WASI syscall API implementation built atop libuv"
    license = "MIT"
    homepage = "https://github.com/nodejs/uvwasi"
    package_type = "library"

    settings = "os", "arch", "compiler", "build_type"
    # 补丁 0003 已移除上游 SHARED 目标，实际只产出静态库 libuvwasi.a，
    # 故 shared 限定为 False（声明与实际产物一致）；fPIC 默认开启，静态库
    # 仍可能被链入共享库，故不随 shared 移除。
    options = {"shared": [False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("libuv/1.52.1")

    def layout(self):
        cmake_layout(self, src_folder=".")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        CMakeDeps(self).generate()
        tc = CMakeToolchain(self)
        # 不构建上游 test/test-*.c（需独立测试框架，且无需打入产物）
        tc.variables["BUILD_TESTING"] = False
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        self.cpp_info.libs = ["uvwasi"]
        self.cpp_info.set_property("cmake_file_name", "uvwasi")
        self.cpp_info.set_property("cmake_target_name", "uvwasi::uvwasi")
