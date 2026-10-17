#!/usr/bin/env python3
"""Conan recipe for kup-backup 0.10.0 on HarmonyOS PC.

kup 是 KDE 备份方案（KF6/Qt6，GPL-2.0-or-later）：kup-daemon 调度 bup/
rsync 备份计划、kup-filedigger 浏览/恢复 bup 归档、kio_bup KIO worker、
kup-purger 清理旧备份。上游 0.10.0 无 tests/ 目录（MANIFEST 如实申报
0 用例），本配方为应用包（package_type=application）。

OHOS 适配要点（patches/0001-0003 + 配方层）：
  - 裁减面（patch 0001）：Plasma/Plasma5Support 不在 ohpcd 发布 →
    plasmoid 小组件与 plasma dataengine 删除；kcmutils 仅有 6.26 线
    （与 kio 6.14 完整构建闭包冲突）→ KCM 模块删除；KDEClangFormat/
    KDEGitCommitHooks/ki18n_install(po) 移除（clang-format/git hook 与
    lconvert 翻译处理非必需，kjobwidgets 6.14.0 先例）。保留核心交付：
    kup-daemon / kup-filedigger / kio_bup / kup-purger / hicolor 图标。
  - 双 Qt 图（kglobalacceld 6.7.2 先例）：Qt6::DBus 唯一提供者是
    qtbase-sql-dbus/6.11.1（裸 qtbase/6.11.1 为 FEATURE_dbus=OFF 构建）。
    daemon 链接 Qt::DBus → sql-dbus 的 lib/cmake 前缀必须在
    conan_cmakedeps_paths.cmake 里最后 PREPEND（= 查找顺序最前），确保
    find_package(Qt6) 命中含 DBus 的构建；其余 KF6 6.14 线包钉
    qtbase/6.11.1，同为 6.11.1 源 ABI 一致，运行时按 SONAME 加载单份。
  - kio/6.14.0：唯一交付 KF6::KIOFileWidgets 的 kio 构建（ohpcd 6.18+
    线均为 KIOCORE_ONLY），daemon/filedigger 的目录浏览/文件选择依赖它。
  - libgit2/1.9.0：ohpcd 预构建二进制钉 openssl/1.1.1w + zlib/1.3.1，
    与 kio 闭包（karchive→openssl/3.5.6 + zlib/1.3.1.1.1）版本冲突 →
    本配方 override 对齐 kio 线，libgit2 的 package_id 随依赖版本变化、
    由 --build=missing 触发源码重建（其静态库 INTERFACE_LINK_LIBRARIES
    还烤死了发布机绝对路径，重建同时修复）。链接 target 为
    libgit2::libgit2package（包自带 libgit2Config.cmake 导出，
    CONFIG 模式；patch 0002/0003 将上游 LibGit2::LibGit2 改名）。
  - KFormat 自 KF6 起在 KCoreAddons 内（kcoreaddons 6.14.0 提供，
    无独立 kformat 依赖）。
  - KF_IGNORE_PLATFORM_CHECK=TRUE（OHOS 不在 KDE 平台列表）；
    CMAKE_INSTALL_LIBDIR=lib（GNUInstallDirs 对 OHOS triplet 会选 lib64）。
  - lld 链接：-Wl,-z,max-page-size=0x1000（默认 0x10000 会把
    .dynsym/.dynstr 分裂进高地址 RW LOAD 段，OHOS musl loader 拒绝
    mmap —— ksystemlog 26.04.0 先例）；SONAME flag 手工提供（CMake 无
    Platform/HarmonyOS 模块，generic fallback 丢 SONAME，kgraphviewer
    26.04.0 先例）。
  - ECM_MODULE_PATH 手工注入（CMakeDeps 生成的 ECMConfig.cmake 不传播
    该变量）+ conan_cmakedeps_paths.cmake 手工写（KF6/Qt 包均为
    cmake_find_mode=none，CMakeDeps 不上 CMAKE_PREFIX_PATH；本配方不启用
    CMakeDeps 生成器，文件由 conan_toolchain.cmake 的 include 钩子加载）。
  - 主二进制 RPATH：CMAKE_BUILD_RPATH/CMAKE_INSTALL_RPATH 注入全部依赖
    lib 目录（KF6 发布包自身 RPATH 烤死过期绝对路径，主二进制 DT_RPATH
    优先命中正确路径 —— kteatime 26.04.0 / CI #60939 先例）。
  - 构建期 host 工具（uic/moc/qtpaths，OHOS 二进制）需依赖 lib 目录 +
    OHOS SDK llvm/lib（lld 依赖 libxml2.so.16）+ /system/lib64（兼容
    libc++_shared.so 遮蔽修复）的 LD_LIBRARY_PATH（ksystemlog 先例）。
"""
import glob
import os

from conan import ConanFile
from conan.tools.env import Environment
from conan.tools.files import (
    apply_conandata_patches,
    export_conandata_patches,
    get,
)
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class KupBackupConan(ConanFile):
    name = "kup-backup"
    version = "0.10.0"
    description = (
        "KDE backup solution - bup/rsync backup scheduler daemon, bup "
        "archive browser, KIO worker and purger for HarmonyOS PC"
    )
    license = "GPL-2.0-or-later"
    homepage = "https://invent.kde.org/system/kup"
    url = "https://invent.kde.org/system/kup"

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # Qt6::DBus 唯一提供者（daemon 链接 Qt::DBus；KDBusService 来自
        # kdbusaddons 6.14.0 同样钉 sql-dbus）。双 Qt 图先例
        # kglobalacceld 6.7.2：sql-dbus 前缀在 paths 文件里排查找最前。
        self.requires("qtbase-sql-dbus/6.11.1")
        # KF6 6.14 线（kio 6.14 是唯一含 KIOFileWidgets 的构建）。
        self.requires("kconfig/6.14.0")
        # KFormat 自 KF6 起随 KCoreAddons 发布。
        self.requires("kcoreaddons/6.14.0")
        self.requires("ki18n/6.14.0")
        self.requires("knotifications/6.14.0")
        self.requires("solid/6.14.0")
        self.requires("kidletime/6.14.0")
        self.requires("kjobwidgets/6.14.0")
        self.requires("kwidgetsaddons/6.14.0")
        self.requires("kxmlgui/6.14.0")
        self.requires("kio/6.14.0")
        self.requires("kdbusaddons/6.14.0")
        # libgit2（静态链接进 filedigger/kio_bup）：override 对齐 kio 线
        # → package_id 变化 → --build=missing 源码重建（详见类 docstring）。
        self.requires("libgit2/1.9.0")
        self.requires("openssl/3.5.6", override=True)
        self.requires("zlib/1.3.1.1.1", override=True)
        # OHOS SDK lld 链接期依赖 libxml2.so.16（worker 环境可能缺失，
        # 声明以便 LD_LIBRARY_PATH 注入 —— kio/ksystemlog 先例）。
        self.requires("libxml2/2.15.3")

    def build_requirements(self):
        self.tool_requires("ecm/6.26.0")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["BUILD_TESTING"] = "OFF"
        tc.variables["KF_IGNORE_PLATFORM_CHECK"] = "TRUE"
        # ki18n_wrap_ui 的 poqm 处理路径会调 lconvert（本平台加载
        # libQt6Core 失败，kteatime/kjobwidgets 先例）；.qm 非必需。
        tc.variables["KF_SKIP_PO_PROCESSING"] = "ON"
        tc.variables["CMAKE_INSTALL_LIBDIR"] = "lib"
        tc.variables["CMAKE_INSTALL_BINDIR"] = "bin"
        # kio_bup MODULE 插件安装位（KIO worker 协议发现路径
        # <prefix>/lib/plugins/kf6/kio）。
        tc.variables["KDE_INSTALL_PLUGINDIR"] = "lib/plugins"
        # lld 页尺寸对齐（OHOS musl loader 拒绝 0x10000 段分裂）。
        tc.variables["CMAKE_EXE_LINKER_FLAGS_INIT"] = (
            "-Wl,-z,max-page-size=0x1000")
        tc.variables["CMAKE_SHARED_LINKER_FLAGS_INIT"] = (
            "-Wl,-z,max-page-size=0x1000")
        tc.variables["CMAKE_MODULE_LINKER_FLAGS_INIT"] = (
            "-Wl,-z,max-page-size=0x1000")
        # SONAME flag 手工提供（CMake 无 Platform/HarmonyOS 模块）。
        tc.variables["CMAKE_SHARED_LIBRARY_SONAME_CXX_FLAG"] = "-Wl,-soname,"
        tc.variables["CMAKE_SHARED_LIBRARY_SONAME_C_FLAG"] = "-Wl,-soname,"
        # 主二进制 RPATH：全部依赖 lib 目录（kteatime #60939 先例）。
        dep_lib_dirs = [
            os.path.join(d.package_folder, "lib")
            for d in self.dependencies.values()
            if d.package_folder
            and os.path.isdir(os.path.join(d.package_folder, "lib"))
        ]
        if dep_lib_dirs:
            rpath = os.pathsep.join(dep_lib_dirs)
            tc.variables["CMAKE_BUILD_RPATH"] = rpath
            tc.variables["CMAKE_INSTALL_RPATH"] = rpath
        # ECM_MODULE_PATH 手工注入（CMakeDeps 不传播）。
        ecm = self.dependencies.build.get("ecm")
        if ecm and ecm.package_folder:
            ecm_share = os.path.join(ecm.package_folder, "share", "ECM")
            tc.variables["ECM_MODULE_PATH"] = ";".join(
                os.path.join(ecm_share, rel)
                for rel in ("modules", "find-modules", "kde-modules")
            )
        tc.generate()
        self._write_cmake_paths(ecm)

    def _write_cmake_paths(self, ecm):
        # qtbase/qtbase-sql-dbus/KF6 包均 cmake_find_mode=none（且本配方
        # 不启用 CMakeDeps 生成器）→ conan_cmakedeps_paths.cmake 手工写，
        # 由 conan_toolchain.cmake 的 include 钩子（EXISTS 检查）加载。
        lines = ["set(CMAKE_FIND_PACKAGE_PREFER_CONFIG ON)"]
        for dep in self.dependencies.values():
            if dep and dep.package_folder:
                lines.append(
                    'list(PREPEND CMAKE_PREFIX_PATH '
                    f'"{dep.package_folder}/lib/cmake")')
                lines.append(
                    'list(PREPEND CMAKE_LIBRARY_PATH '
                    f'"{dep.package_folder}/lib")')
                lines.append(
                    'list(PREPEND CMAKE_INCLUDE_PATH '
                    f'"{dep.package_folder}/include")')
        # 双 Qt 排序：qtbase-sql-dbus 最后 PREPEND（= 查找顺序最前），
        # find_package(Qt6) 命中含 DBus 的构建（kglobalacceld 先例）。
        sqldbus = self.dependencies.get("qtbase-sql-dbus")
        if sqldbus and sqldbus.package_folder:
            lines.append(
                'list(PREPEND CMAKE_PREFIX_PATH '
                f'"{sqldbus.package_folder}/lib/cmake")')
            lines.append(
                'list(PREPEND CMAKE_LIBRARY_PATH '
                f'"{sqldbus.package_folder}/lib")')
            lines.append(
                'list(PREPEND CMAKE_INCLUDE_PATH '
                f'"{sqldbus.package_folder}/include")')
        if ecm and ecm.package_folder:
            ecm_share = os.path.join(ecm.package_folder, "share", "ECM")
            lines.extend([
                f'list(PREPEND CMAKE_PREFIX_PATH "{ecm_share}/cmake")',
                f'list(PREPEND CMAKE_MODULE_PATH "{ecm_share}/modules")',
                f'list(PREPEND CMAKE_MODULE_PATH '
                f'"{ecm_share}/find-modules")',
                f'list(PREPEND CMAKE_MODULE_PATH '
                f'"{ecm_share}/kde-modules")',
            ])
        lines.extend([
            'list(PREPEND CMAKE_PREFIX_PATH "${CMAKE_CURRENT_LIST_DIR}")',
            'list(PREPEND CMAKE_MODULE_PATH "${CMAKE_CURRENT_LIST_DIR}")',
        ])
        paths_file = os.path.join(
            self.generators_folder, "conan_cmakedeps_paths.cmake")
        with open(paths_file, "w") as f:
            f.write("\n".join(lines) + "\n")

    def _cmake_build_env(self):
        # host 工具（uic/moc/rcc/qtpaths，OHOS 二进制）运行需要依赖库 +
        # SDK llvm/lib + /system/lib64（ksystemlog 26.04.0 先例）。
        build_env = Environment()
        for dep in self.dependencies.values():
            if dep and dep.package_folder:
                build_env.prepend_path(
                    "LD_LIBRARY_PATH",
                    os.path.join(dep.package_folder, "lib"))
        if self.settings.os == "OHOS":
            for llvm_lib in sorted(glob.glob(
                    "/data/service/hnp/ohos-sdk.org/"
                    "ohos-sdk_*/ohos/native/llvm/lib")):
                build_env.prepend_path("LD_LIBRARY_PATH", llvm_lib)
            build_env.prepend_path("LD_LIBRARY_PATH", "/system/lib64")
        return build_env

    def build(self):
        # 平台保护：裁剪补丁仅 OHOS 生效。
        if self.settings.os == "OHOS":
            apply_conandata_patches(self)
        cmake = CMake(self)
        with self._cmake_build_env().vars(self).apply():
            # RPATH 双保险：generate() 已写 toolchain 变量，这里再以
            # configure 缓存变量注入（kteatime 先例）。
            dep_lib_dirs = [
                os.path.join(d.package_folder, "lib")
                for d in self.dependencies.values()
                if d.package_folder
                and os.path.isdir(os.path.join(d.package_folder, "lib"))
            ]
            variables = None
            if dep_lib_dirs:
                rpath = os.pathsep.join(dep_lib_dirs)
                variables = {"CMAKE_BUILD_RPATH": rpath,
                             "CMAKE_INSTALL_RPATH": rpath}
            cmake.configure(variables=variables)
            cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        # 应用包：bin/ 三个可执行 + lib/plugins/kf6/kio/kio_bup.so。
        self.cpp_info.libs = []
        self.cpp_info.includedirs = []
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.set_property("cmake_find_mode", "none")
        self.runenv_info.prepend_path(
            "LD_LIBRARY_PATH", os.path.join(self.package_folder, "lib"))
