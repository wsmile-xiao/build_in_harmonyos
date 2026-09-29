#!/usr/bin/env python3
"""Conan recipe — kweathercore 26.04.0 (CMake + ECM)

KDE weather data-access library (KWeatherCore). Cross build for HarmonyOS PC
(OHOS aarch64, clang 15, libc++).

Real upstream dependencies (kweathercore-26.04.0/CMakeLists.txt):
  - ECM >= 6.3.0 (NO_MODULE, build-time)
  - Qt6 >= 6.5.0 CONFIG REQUIRED: Core Network Positioning Qml
  - KF6 >= 6.3.0 REQUIRED COMPONENTS: I18n, Holidays
pkg-config/cmake name: KWeatherCore.
"""
import glob
import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get


class KWeatherCoreConan(ConanFile):
    name = "kweathercore"
    version = "26.04.0"
    description = "KDE Weather Core Library (kweathercore)"
    license = "LGPL-2.0-or-later"
    homepage = "https://invent.kde.org/libraries/kweathercore"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": True}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # kweathercore 26.04.0 CMakeLists.txt:
        #   find_package(Qt6 6.5.0 CONFIG REQUIRED Core Network Positioning Qml)
        #   find_package(KF6 6.3.0 REQUIRED COMPONENTS I18n Holidays)
        # 制品仓：qtbase/6.11.1（Core/Network）、qtdeclarative/6.11.1（Qml）、
        # qtpositioning/6.11.1（Positioning）、ki18n/6.26.0（I18n）、
        # kholidays/6.28.0（Holidays）。
        self.requires("qtbase/6.11.1")
        self.requires("qtdeclarative/6.11.1")
        self.requires("qtpositioning/6.11.1")
        self.requires("ki18n/6.26.0")
        self.requires("kholidays/6.28.0")

    def build_requirements(self):
        self.tool_requires("ecm/6.26.0")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        # 上游 CMakeLists.txt:10 强制 CMAKE_CXX_STANDARD 20
        # （src 使用 std::ranges 等特性）。host profile 默认 cppstd=17，
        # ConanToolchain 会写 set(CMAKE_CXX_STANDARD 17) 覆盖上游 ——
        # 直接在工具链变量层面改回 20。
        self.conf.define("tools.build:compiler_cppstd", "20")
        tc = CMakeToolchain(self)
        # OHOS SDK 的 libc++（clang 15）在未定义 _LIBCPP_ENABLE_EXPERIMENTAL
        # 时于 __config 定义 _LIBCPP_HAS_NO_INCOMPLETE_RANGES，禁用
        # std::ranges 算法（any_of 等，最小探针实测复现）；上游源码使用
        # std::ranges::any_of（capalertinfo.cpp:159），须显式启用实验段。
        tc.variables["CMAKE_CXX_FLAGS"] = (
            tc.variables.get("CMAKE_CXX_FLAGS", "") + " -D_LIBCPP_ENABLE_EXPERIMENTAL"
        ).strip()
        tc.variables["CMAKE_CXX_STANDARD"] = "20"
        tc.variables["CMAKE_CXX_STANDARD_REQUIRED"] = "ON"
        tc.variables["BUILD_SHARED_LIBS"] = "ON"
        # 上游 autotests/ 有 ECM 测试注册，conan 构建跳过上游测试
        # （test_package 用消费者视角验证）。
        tc.variables["BUILD_TESTING"] = "OFF"
        # OHOS 不在 KDE 平台列表，绕过平台检测（ki18n 先例）。
        tc.variables["KF_IGNORE_PLATFORM_CHECK"] = "TRUE"

        # ECM_MODULE_PATH 手动设置（CMakeDeps 生成的 ECMConfig.cmake 不传播
        # 该变量，ki18n 先例同款）。
        ecm = self.dependencies.build.get("ecm")
        if ecm:
            ecm_share = os.path.join(ecm.package_folder, "share", "ECM")
            tc.variables["ECM_MODULE_PATH"] = ";".join([
                os.path.join(ecm_share, "modules"),
                os.path.join(ecm_share, "find-modules"),
                os.path.join(ecm_share, "kde-modules"),
            ])

        # qtbase 用 cmake_find_mode=none 时 CMakeDeps 不会把其 lib/cmake
        # 加入 CMAKE_PREFIX_PATH，手工生成路径注入文件（ki18n 先例同款）。
        prefixes = []
        libraries = []
        includes = []
        qtbase = self.dependencies.get("qtbase")
        if qtbase and qtbase.package_folder:
            qt_pkg = qtbase.package_folder
            prefixes.append(os.path.join(qt_pkg, "lib", "cmake"))
            prefixes.append(qt_pkg)
            libraries.append(os.path.join(qt_pkg, "lib"))
            includes.append(os.path.join(qt_pkg, "include"))
        # 其余 Qt 模块与 KF6 依赖：Config 文件在各包 lib/cmake/ 下。
        for dep_name in ("qtdeclarative", "qtpositioning", "ki18n", "kholidays"):
            dep = self.dependencies.get(dep_name)
            if dep and dep.package_folder:
                prefixes.append(os.path.join(dep.package_folder, "lib", "cmake"))
                prefixes.append(dep.package_folder)
                libraries.append(os.path.join(dep.package_folder, "lib"))
                includes.append(os.path.join(dep.package_folder, "include"))
        ecm = self.dependencies.build.get("ecm")
        if ecm and ecm.package_folder:
            ecm_share = os.path.join(ecm.package_folder, "share", "ECM")
            prefixes.append(os.path.join(ecm_share, "cmake"))

        lines = [
            "set(CMAKE_FIND_PACKAGE_PREFER_CONFIG ON)",
            'set(CMAKE_PREFIX_PATH "{};${{CMAKE_PREFIX_PATH}}")'.format(";".join(prefixes)),
            'set(CMAKE_LIBRARY_PATH "{};${{CMAKE_LIBRARY_PATH}}")'.format(";".join(libraries)),
            'set(CMAKE_INCLUDE_PATH "{};${{CMAKE_INCLUDE_PATH}}")'.format(";".join(includes)),
            'list(PREPEND CMAKE_PREFIX_PATH "${CMAKE_CURRENT_LIST_DIR}")',
            'list(PREPEND CMAKE_MODULE_PATH "${CMAKE_CURRENT_LIST_DIR}")',
        ]
        paths_file = os.path.join(
            self.generators_folder, "conan_cmakedeps_paths.cmake"
        )
        with open(paths_file, "w") as f:
            f.write("\n".join(lines) + "\n")

        # 双管齐下（kdeclarative 6.26.0 先例）：
        # 1) QT_ADDITIONAL_PACKAGES_PREFIX_PATH —— Qt6 的 find_package 对
        #    组件 Qml/Positioning 会在 qtbase 前缀下找，分包发布的
        #    qtdeclarative/qtpositioning 需经此变量补入；
        # 2) CMAKE_PROJECT_TOP_LEVEL_INCLUDES —— 在 project() 时即加载
        #    路径注入（ECMQmlModule 在 include 阶段就要 Qt6::Qml）。
        qt_extra = []
        for dep_name in ("qtdeclarative", "qtpositioning"):
            dep = self.dependencies.get(dep_name)
            if dep and dep.package_folder:
                qt_extra.append(dep.package_folder)
        if qt_extra:
            tc.variables["QT_ADDITIONAL_PACKAGES_PREFIX_PATH"] = ";".join(qt_extra)
        tc.variables["CMAKE_PROJECT_TOP_LEVEL_INCLUDES"] = paths_file

        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        with self._cmake_build_env().vars(self).apply():
            cmake.configure()
            cmake.build()

    def _cmake_build_env(self):
        """构建期环境：host 工具（qmltyperegistrar/qtpaths 等）在 musl 下
        dlopen Qt 依赖库需要 LD_LIBRARY_PATH（kdeclarative 6.26.0 先例同款）。"""
        from conan.tools.env import Environment

        env = Environment()
        deps = list(self.dependencies.values()) + list(self.dependencies.build.values())
        for dep in deps:
            if dep and dep.package_folder:
                env.prepend_path("LD_LIBRARY_PATH",
                                 os.path.join(dep.package_folder, "lib"))
                env.prepend_path("LD_LIBRARY_PATH",
                                 os.path.join(dep.package_folder, "bin"))
        # OHOS SDK 的 llvm lib（libc++_shared.so 等）与系统库目录
        if self.settings.os == "OHOS":
            for llvm_lib in sorted(glob.glob(
                    "/data/service/hnp/ohos-sdk.org/ohos-sdk_*/ohos/native/llvm/lib")):
                env.prepend_path("LD_LIBRARY_PATH", llvm_lib)
            env.prepend_path("LD_LIBRARY_PATH", "/system/lib64")
        return env

    def package(self):
        cmake = CMake(self)
        cmake.install()
        # 上游 GenerateExportHeader 生成的头用 <kweathercore/kweathercore_export.h>
        # 小写裸前缀 include（locationqueryresult.h 等全部公共头均如此），
        # 但 ECM 安装布局只给出 include/KWeatherCore/KWeatherCore/（驼峰）。
        # 包内补一层相对符号链接 include/kweathercore -> KWeatherCore/KWeatherCore，
        # 使 <kweathercore/kweathercore_export.h> 原样可解析。
        include_dir = os.path.join(self.package_folder, "include")
        lc_link = os.path.join(include_dir, "kweathercore")
        if not os.path.exists(lc_link):
            os.symlink(os.path.join("KWeatherCore", "KWeatherCore"), lc_link)

    def package_info(self):
        # 上游安装自带的 KWeatherCoreConfig.cmake，用 cmake_find_mode=none
        # 避免 CMakeDeps 遮蔽（ki18n 先例同款）。
        self.cpp_info.set_property("cmake_find_mode", "none")
        self.cpp_info.builddirs = [os.path.join("lib", "cmake")]
        # 上游安装布局：include/KWeatherCore/KWeatherCore/*.h +
        # include/kweathercore_version.h，用法 #include <KWeatherCore/...>；
        # package() 另补 include/kweathercore 符号链接供小写裸前缀 include。
        self.cpp_info.includedirs = ["include", "include/KWeatherCore"]
        # 实际产出库为 libKWeatherCore.so（非 KF6KWeatherCore）。
        self.cpp_info.libs = ["KWeatherCore"]
