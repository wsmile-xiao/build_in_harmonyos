#!/usr/bin/env python3
"""Conan recipe for kteatime 26.04.0 on HarmonyOS PC.

KTeaTime 是 KDE Gear 泡茶计时器（tea timer，纯 Qt Widgets GUI）。

OHOS 适配要点：
  - Qt6 DBus 未发布到 ohpcd（qtbase FEATURE_dbus=OFF）：KF6::StatusNotifierItem
    本质是 StatusNotifierWatcher 的 DBus 客户端、且 OHOS 无系统托盘；
    KF6::NotifyConfig（KNotifyConfigWidget 通知配置对话框）同样依赖 DBus。
    二者以 0001 补丁裁减：TopLevel 基类 KStatusNotifierItem → QWidget，
    托盘 API 为 no-op、移除『配置通知』菜单项（通知由 KNotification 承担，
    knotifications/6.14.0 在仓内，无 DBus 时优雅降级）。
  - KF_IGNORE_PLATFORM_CHECK=TRUE（OHOS 不在 KDE 平台列表）
  - USE_DBUS=OFF（Qt6 DBus 未发布）
  - KF_SKIP_PO_PROCESSING=ON（lconvert 在本平台加载 libQt6Core 失败，
    .qm 翻译目录非必需，同 ktextwidgets 配方）
  - BUILD_TESTING=OFF：上游 kteatime 无任何测试目标（无 tests/ 目录），
    MANIFEST 如实申报 0 用例；新增 test_package 冒烟验证。
  - ECM_MODULE_PATH 手工设置（CMakeDeps 生成的 ECMConfig.cmake 不传播
    ECM_MODULE_PATH，KDEInstallDirs/KDECMakeSettings 等 KDE cmake 模块依赖它）
  - conan_cmakedeps_paths.cmake（qtbase 用 cmake_find_mode=none，需手工把
    lib/cmake 等加入 CMAKE_PREFIX_PATH 才能 find_package(Qt6 CONFIG)）
"""
import os

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class KteatimeConan(ConanFile):
    name = "kteatime"
    version = "26.04.0"
    description = "KDE tea time reminder - tea timer for HarmonyOS PC"
    license = "GPL-2.0-or-later"
    homepage = "https://invent.kde.org/utilities/kteatime"

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("qtbase/6.11.1")
        self.requires("kconfig/6.14.0")
        self.requires("kcoreaddons/6.14.0")
        self.requires("kcrash/6.14.0")
        self.requires("kguiaddons/6.14.0")
        self.requires("ki18n/6.14.0")
        self.requires("kiconthemes/6.14.0")
        self.requires("knotifications/6.14.0")
        self.requires("ktextwidgets/6.14.0")
        self.requires("kxmlgui/6.14.0")

    def build_requirements(self):
        self.tool_requires("ecm/6.20.0")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["BUILD_TESTING"] = "OFF"
        tc.variables["KF_IGNORE_PLATFORM_CHECK"] = "TRUE"
        # Qt6 DBus 未发布到 ohpcd；托盘/通知配置依赖 DBus，禁用。
        tc.variables["USE_DBUS"] = "OFF"
        # lconvert 在本平台加载 libQt6Core 失败，.qm 翻译目录非必需（同 ktextwidgets）。
        tc.variables["KF_SKIP_PO_PROCESSING"] = "ON"

        # ECM 安装的 ECMConfig.cmake 会设置 ECM_MODULE_PATH，但 CMakeDeps 生成的
        # ECMConfig.cmake 不传播；手工设置（同 kxmlgui 配方）。
        ecm = self.dependencies.build.get("ecm")
        if ecm:
            ecm_share = os.path.join(ecm.package_folder, "share", "ECM")
            tc.variables["ECM_MODULE_PATH"] = ";".join([
                os.path.join(ecm_share, "modules"),
                os.path.join(ecm_share, "find-modules"),
                os.path.join(ecm_share, "kde-modules"),
            ])

        qtbase = self.dependencies.get("qtbase")
        if qtbase:
            qt_pkg = qtbase.package_folder
            lines = []
            lines.append(f'list(PREPEND CMAKE_PREFIX_PATH "{qt_pkg}/lib/cmake")')
            lines.append(f'list(PREPEND CMAKE_LIBRARY_PATH "{qt_pkg}/lib")')
            lines.append(f'list(PREPEND CMAKE_INCLUDE_PATH "{qt_pkg}/include")')
            if ecm:
                ecm_cmake = os.path.join(ecm.package_folder, "share", "ECM", "cmake")
                lines.append(f'list(PREPEND CMAKE_MODULE_PATH "{ecm_cmake}")')
                lines.append(f'list(PREPEND CMAKE_PREFIX_PATH "{ecm_cmake}")')
            # 所有依赖的 lib/cmake 目录加入查找路径，find_package(KF6*)
            # 与传递 find_dependency() 链均可解析（同 kxmlgui 配方）。
            for dep in self.dependencies.values():
                if dep and dep.package_folder:
                    lines.append(
                        f'list(PREPEND CMAKE_PREFIX_PATH '
                        f'"{dep.package_folder}/lib/cmake")'
                    )
                    lines.append(
                        f'list(PREPEND CMAKE_LIBRARY_PATH '
                        f'"{dep.package_folder}/lib")'
                    )
                    lines.append(
                        f'list(PREPEND CMAKE_INCLUDE_PATH '
                        f'"{dep.package_folder}/include")'
                    )
            lines.append(
                f'list(PREPEND CMAKE_MODULE_PATH '
                f'"${{CMAKE_CURRENT_LIST_DIR}}")'
            )
            lines.append(
                f'list(PREPEND CMAKE_PREFIX_PATH '
                f'"${{CMAKE_CURRENT_LIST_DIR}}")'
            )
            lines.append('set(CMAKE_FIND_PACKAGE_PREFER_CONFIG ON)')
            lines.append(f'set(CONAN_RUNTIME_LIB_DIRS "{qt_pkg}/lib")')
            paths_file = os.path.join(
                self.generators_folder, "conan_cmakedeps_paths.cmake"
            )
            with open(paths_file, "w") as f:
                f.write("\n".join(lines) + "\n")

        # OHOS 加载器只认 DT_RPATH（LD_LIBRARY_PATH 不搜，#60939 实测 KF6
        # 传递依赖加载失败：libKF6CoreAddons.so 走 .conan2 过期路径、
        # libKF6SonnetCore.so 等走 ../../bin 相对路径——均为 KF6 包构建时
        # CONAN_HOME 不同而烤死的自身 RPATH）。主二进制 auto-RPATH 只含
        # 直接依赖目录，传递依赖目录缺失 → 加载器落入 KF6 .so 自身坏 RPATH。
        # 修复：CMAKE_BUILD_RPATH + CMAKE_INSTALL_RPATH 注入全部依赖 lib
        # 目录（主二进制 DT_RPATH 优先命中正确路径，坏条目不再触达）。
        dep_lib_dirs = [os.path.join(d.package_folder, "lib")
                        for d in self.dependencies.values()
                        if d.package_folder
                        and os.path.isdir(os.path.join(d.package_folder, "lib"))]
        if dep_lib_dirs:
            rpath = os.pathsep.join(dep_lib_dirs)
            tc.variables["CMAKE_BUILD_RPATH"] = rpath
            tc.variables["CMAKE_INSTALL_RPATH"] = rpath

        tc.generate()

    def build(self):
        # 平台保护：仅 OHOS 应用 0001 裁减补丁，其它平台不受影响。
        if self.settings.os == "OHOS":
            apply_conandata_patches(self)
        cmake = CMake(self)
        # RPATH 双保险：generate() 已写 toolchain 变量，这里再以 configure
        # 缓存变量注入（cache 变量确保 CMake RPATH 机制真正生效）。
        dep_lib_dirs = [os.path.join(d.package_folder, "lib")
                        for d in self.dependencies.values()
                        if d.package_folder
                        and os.path.isdir(os.path.join(d.package_folder, "lib"))]
        rpath = os.pathsep.join(dep_lib_dirs) if dep_lib_dirs else None
        cmake.configure(variables={"CMAKE_BUILD_RPATH": rpath,
                                   "CMAKE_INSTALL_RPATH": rpath} if rpath else None)
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        # 应用包：无可链接库；保留 minimal cpp_info。
        self.cpp_info.libs = []
