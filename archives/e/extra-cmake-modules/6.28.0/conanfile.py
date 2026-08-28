#!/usr/bin/env python3
"""Conan recipe — extra-cmake-modules (ECM) 6.28.0.

ECM 是纯 CMake 模块包（无 C/C++ 编译产物），只安装 .cmake/.py 脚本到 share/ECM/。
下游 KDE Frameworks 6 库（bluez-qt/ki18n/karchive/kdoctools 等）通过 find_package(ECM) 引用。

构建系统：CMake（cmake-only，无 compiler）
平台：OHOS / Linux / macOS / Windows
依赖：零运行时依赖（构建时可选 Sphinx/Qt5/Qt6/Python3 仅用于文档/测试）
"""
import os

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class ExtraCMakeModulesConan(ConanFile):
    name = "extra-cmake-modules"
    version = "6.28.0"
    description = "Extra CMake Modules — KDE 社区扩展 CMake 模块包，提供 find_package/find_modules/common build settings"
    license = "BSD-3-Clause"
    homepage = "https://invent.kde.org/frameworks/extra-cmake-modules"
    url = ""

    # R32: settings.os 判断必须 in ("Linux", "OHOS")，但 ECM 无编译产物，
    # settings 仅用于 conan create 验证可移植性
    settings = "os", "compiler", "build_type", "arch"

    # ECM 是 cmake-only 模块包，无编译产物 → 不声明 options/shared
    generators = "CMakeDeps"

    # 无编译产物 → 不声明 cpp_info.libs（R26 系统同名库隔离不适用）
    # 无运行时依赖 → requirements() 为空

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass  # ECM 无运行时依赖

    def layout(self):
        cmake_layout(self)

    def generate(self):
        tc = CMakeToolchain(self)
        # ECM 是纯 cmake 模块包（LANGUAGES NONE），不编译任何代码
        # 跳过编译器检查以避免 OHOS 环境下 clang 编译器检测失败
        tc.cache_variables["CMAKE_C_COMPILER_WORKS"] = "1"
        tc.cache_variables["CMAKE_CXX_COMPILER_WORKS"] = "1"
        # 禁用测试和文档构建——ECM 的测试静态库需要 C++ 编译器，
        # 在 OHOS 环境下 clang++ 编译器检测失败
        tc.cache_variables["BUILD_TESTING"] = "OFF"
        tc.cache_variables["BUILD_DOCUMENTATION"] = "OFF"
        tc.user_presets_path = False
        tc.generate()

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        # ECM 是 cmake-only 模块包：configure 只用于生成 ECMConfig.cmake
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        # ECM 产物是 share/ECM/ 下的 .cmake/.py/.in 脚本，无 bin/lib/include
        # 注意：必须完整复制目录（含 .in 模板），否则下游 KDE 库 find_package(ECM) 后
        # include(ECMUninstallTarget)/ECMQmlModule 等会因模板缺失而配置失败
        for _dir in ("modules", "kde-modules", "find-modules", "toolchain", "cmake"):
            _src = os.path.join(self.source_folder, _dir)
            _dst = os.path.join(self.package_folder, "share/ECM", _dir)
            if os.path.isdir(_src):
                copy(self, "*", _src, _dst)
        # ECMConfig.cmake + ECMConfigVersion.cmake 由 cmake.configure() 生成在 self.build_folder
        copy(self, "ECMConfig.cmake", self.build_folder,
             os.path.join(self.package_folder, "share/ECM/cmake"))
        copy(self, "ECMConfigVersion.cmake", self.build_folder,
             os.path.join(self.package_folder, "share/ECM/cmake"))

    def package_info(self):
        # ECM 是 CMake 模块包，下游通过 find_package(ECM) 引用，
        # 不通过 cpp_info.libs / cpp_info.includedirs 链接
        ecm_share = os.path.join(self.package_folder, "share", "ECM")
        self.cpp_info.set_property("cmake_file", os.path.join(ecm_share, "cmake", "ECMConfig.cmake"))
        self.cpp_info.set_property("cmake_target_name", "ECM")
        self.cpp_info.builddirs.append(os.path.join(ecm_share, "cmake"))
        self.cpp_info.builddirs.append(os.path.join(ecm_share, "modules"))
        self.cpp_info.builddirs.append(os.path.join(ecm_share, "kde-modules"))
        self.cpp_info.builddirs.append(os.path.join(ecm_share, "find-modules"))
        self.cpp_info.builddirs.append(os.path.join(ecm_share, "toolchain"))
