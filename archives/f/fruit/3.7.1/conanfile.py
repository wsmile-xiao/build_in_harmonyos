#!/usr/bin/env python3
"""Conan recipe — fruit 3.7.1 (CMake, compiled C++ dependency injection framework).

google/fruit: compile-time, dependency-free C++ dependency injection framework.
CMake build produces libfruit (static/shared). On OHOS:
  - CMake has no HarmonyOS platform module; force the Linux branch (E092
    pattern) so upstream CMake feature probes run against the OHOS toolchain.
  - FRUIT_USES_BOOST=OFF: uses std::unordered_map/set instead of
    boost::unordered_* (upstream-supported, slightly slower injection but
    avoids a Boost dependency in the OHOS registry chain).
  - FRUIT_IS_BEING_BUILT_BY_CONAN=YES: skip upstream examples/tests targets
    inside `conan create`; upstream pytest suite is enumerated/run in the
    adaptation gate (separate CMake build + pytest), recipe ships a real
    consumer test in test_package.
"""
from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get


class FruitConan(ConanFile):
    name = "fruit"
    version = "3.7.1"
    description = "C++ dependency injection framework (compile-time, dependency-free)"
    license = "Apache-2.0"
    homepage = "https://github.com/google/fruit"
    url = "https://github.com/google/fruit"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"

    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        # 上游源码根目录含 Bazel BUILD 文件；构建/生成器目录若命名为 build/
        # 会在大小写不敏感文件系统上与之冲突（NotADirectoryError），改用 conan-build。
        self.folders.source = "."
        self.folders.build = "conan-build"
        self.folders.generators = "conan-build/generators"

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        if self.settings.os == "OHOS":
            # CMake has no HarmonyOS platform module; treat as Linux so the
            # upstream feature probes use the OHOS clang/libc++ toolchain.
            tc.variables["CMAKE_SYSTEM_NAME"] = "Linux"
        tc.variables["CMAKE_POLICY_VERSION_MINIMUM"] = "3.5"
        tc.cache_variables["CMAKE_POLICY_VERSION_MINIMUM"] = "3.5"
        # 注意：不设 FRUIT_IS_BEING_BUILT_BY_CONAN=YES。上游 CMakeLists 在该
        # 变量为 YES 时会 include 已废弃的 Conan 1 conanbuildinfo.cmake /
        # conan_basic_setup()（Conan 2 无此机制，configure 直接失败）。保持
        # 未设置则 Release 下 examples/tests 子目录被加入，但 ALL 默认只构建
        # libfruit（tests 的 pytest 套件仅注册不构建，单独在适配门禁运行）。
        tc.variables["FRUIT_USES_BOOST"] = "OFF"
        tc.variables["BUILD_SHARED_LIBS"] = "ON" if self.options.shared else "OFF"
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
        self.cpp_info.libs = ["fruit"]