#!/usr/bin/env python3
"""Conan recipe — extra-cmake-modules (ECM) 6.26.0 on HarmonyOS PC (aarch64).

ECM (Extra CMake Modules) is a collection of additional CMake modules from KDE.
It is a pure CMake module package — no binary code is compiled or linked; it
only installs .cmake / .py scripts under share/ECM/.

Downstream KDE Frameworks 6 libraries (kitemviews / kcodecs / kconfig / kpackage
etc., all 6.26.0) consume it via find_package(ECM) / tool_requires.

OHOS-specific adaptations (aligned with the published extra-cmake-modules 6.28.0
/ 6.29.0 recipes — same package-name series; the ecm/* recipes are the alias
series referencing the same upstream tarball):
  - package_type = "build-scripts": ECM ships only CMake modules.
  - package_id() uses self.info.clear() to avoid package-ID variation from
    compiler/build_type settings (no compiled artifacts).
  - BUILD_TESTING=OFF at configure time: upstream tests are optional and
    Qt/Python dependent; the module set itself has no runtime deps.
  - R32: no os == "Linux" comparison needed (no os-specific branches).
  - R33: no reliance on undefined shell $CC/$CFLAGS (cmake-only; all flags come
    from the Conan CMakeToolchain).
  - package() uses cmake.install(): upstream CMakeLists.txt has full install
    rules covering modules / kde-modules / find-modules / toolchain /
    test-modules / cmake config dir (incl. .in templates), so the downstream
    include(ECMUninstallTarget) / ECMQmlModule paths stay intact.
"""
from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class ExtraCMakeModulesConan(ConanFile):
    name = "extra-cmake-modules"
    version = "6.26.0"
    description = "Extra CMake Modules — additional CMake modules from KDE"
    license = "BSD-3-Clause"
    homepage = "https://kde.org/products/frameworks/"
    url = "https://invent.kde.org/frameworks/extra-cmake-modules"

    package_type = "build-scripts"

    # ECM 无编译产物；settings 仅用于 conan create 验证可移植性
    settings = "os", "compiler", "build_type", "arch"

    def package_id(self):
        # No compiled artifacts: a single package ID across toolchains.
        self.info.clear()

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        tc = CMakeToolchain(self)
        # ECM 是 LANGUAGES NONE 的纯 cmake 模块包；跳过编译器检查，
        # 避免 OHOS 环境下 clang 交叉编译器检测失败
        tc.cache_variables["CMAKE_C_COMPILER_WORKS"] = "1"
        tc.cache_variables["CMAKE_CXX_COMPILER_WORKS"] = "1"
        # 上游测试静态库需要 C++ 编译器 + Qt5/Qt6/Python3 前置，
        # 与模块安装物无关 → CI 构建路径关闭
        tc.cache_variables["BUILD_TESTING"] = "OFF"
        tc.cache_variables["BUILD_DOCUMENTATION"] = "OFF"
        tc.user_presets_path = False
        tc.generate()

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        # cmake-only 模块包：configure 生成 ECMConfig.cmake，build 无实际产物
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        # 上游 install() 规则完整覆盖 share/ECM/{modules,kde-modules,
        # find-modules,toolchain,test-modules,cmake}（含 .in 模板与
        # ECMConfig.cmake/ECMConfigVersion.cmake）
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        # 下游通过 find_package(ECM) 消费；无 cpp_info.libs（cmake-only 模块包）
        self.cpp_info.set_property("cmake_file_name", "ECM")
        self.cpp_info.set_property("cmake_target_name", "ECM::ECM")
        self.cpp_info.builddirs = ["share/ECM/cmake"]
