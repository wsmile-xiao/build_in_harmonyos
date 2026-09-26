#!/usr/bin/env python3
"""Conan recipe for cmake-extras 1.1 — 纯 CMake 模块集合数据包。

cmake-extras 是 Lomiri/UBports 生态（上游源自 Canonical，见 debian/copyright 的
Source 字段）的 CMake 附加模块集合。1.1 的 CMakeLists.txt 装两份东西：

  * src/ 下 11 个 find_package() "config" 扩展机制模块 → ${DATADIR}/cmake/
  * modules/ 下 5 个 deprecated include shim        → ${CMAKE_ROOT}/Modules/

第二条的 DESTINATION 是**正在运行的 CMake 自身安装目录**的绝对路径，staged
install 时会绕过 CMAKE_INSTALL_PREFIX/DESTDIR 写到包外（在 conan 的只读包目录里
根本不可写）。上游在 1.1 之后用 commit 14eeaf8ed50b（"Drop deprecated macros"，
进入 1.4 的 debian/changelog）直接删掉了这条安装规则和 modules/；更早的
c6ca8632b55b 已经把 Find*.cmake 迁到非版本化的 cmake 目录。本配方按同一方向把
5 个 shim 与 src/ 同置于 share/cmake/——消费者只需一个 CMAKE_MODULE_PATH 就能
include(UseDoxygen)，一个 CMAKE_PREFIX_PATH 就能 find_package(DoxygenBuilder)。
纯数据包、无编译、无源码补丁。
"""
import os
import shutil
import stat

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import get, copy, export_conandata_patches, apply_conandata_patches

# 上游 CMakeLists.txt 的 install(DIRECTORY src/ ... USE_SOURCE_PERMISSIONS)
# 保留源文件权限位，check_copyright.sh / include_checker.py 必须以可执行位交付。
_EXECUTABLE_MODULES = ("CopyrightTest/check_copyright.sh",
                       "IncludeChecker/include_checker.py")


class CmakeExtrasConan(ConanFile):
    name = "cmake-extras"
    version = "1.1"
    package_type = "application"
    license = "LGPL-3.0-or-later"
    homepage = "https://gitlab.com/ubports/development/core/cmake-extras"
    description = ("cmake-extras 1.1 — Lomiri/UBports CMake 附加模块集合"
                   "（11 个 find_package config 模块 + 5 个 deprecated include shim，"
                   "纯 CMake 数据包，无编译）")
    topics = ("cmake", "modules", "lomiri", "ubports", "header-only-data")
    settings = "os", "arch", "compiler", "build_type"
    exports_sources = "patches/*"

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"cmake-extras does not support os={self.settings.os}")

    def export_sources(self):
        export_conandata_patches(self)

    def source(self):
        # URL 末段是 .tar.gz，get() 能自行判定解包类型；无需显式 filename=
        get(self, **self.conan_data["sources"], strip_root=True,
            keep_permissions=True)

    def build(self):
        # 纯数据包——无编译。apply_conandata_patches 在无补丁时是空操作。
        apply_conandata_patches(self)

    @staticmethod
    def _copy_keep_mode(src, dst):
        """拷贝单个文件并把源权限位原样打到目标（对齐 USE_SOURCE_PERMISSIONS）。

        不用 shutil.copy2：它只复制 mode 但受 umask 影响的场景（解包后
        权限已被 conan/文件系统改写过）不可靠，这里显式 chmod。
        """
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        shutil.copyfile(src, dst)
        os.chmod(dst, os.stat(src).st_mode & 0o7777)

    def _copy_tree_keep_mode(self, src_root, dst_root):
        for dirpath, _dirnames, filenames in os.walk(src_root):
            for fn in filenames:
                s = os.path.join(dirpath, fn)
                rel = os.path.relpath(s, src_root).replace(os.sep, "/")
                self._copy_keep_mode(s, os.path.join(dst_root, rel))

    def package(self):
        src_root = os.path.join(self.source_folder, "src")
        modules_root = os.path.join(self.source_folder, "modules")
        dst = os.path.join(self.package_folder, "share", "cmake")
        if not os.path.isdir(src_root):
            raise ConanInvalidConfiguration(
                f"src/ not found in source: {src_root}")

        # 1) src/ 下 11 个模块目录 → share/cmake/<Module>/
        for name in sorted(os.listdir(src_root)):
            s = os.path.join(src_root, name)
            if os.path.isdir(s):
                self._copy_tree_keep_mode(s, os.path.join(dst, name))

        # 2) modules/ 下 5 个 deprecated shim → share/cmake/（与模块目录平级）
        if os.path.isdir(modules_root):
            for name in sorted(os.listdir(modules_root)):
                s = os.path.join(modules_root, name)
                if os.path.isfile(s):
                    self._copy_keep_mode(s, os.path.join(dst, name))

        # 3) 许可证文本：1.1 的源码树里没有 LICENSE 文件，许可证全文只存在于
        #    debian/copyright（LGPL-3, or at your option any later version）。
        copy(self, "copyright",
             src=os.path.join(self.source_folder, "debian"),
             dst=os.path.join(self.package_folder, "licenses"))

        # 4) 兜底：解包/文件系统若吃掉了可执行位，按上游 USE_SOURCE_PERMISSIONS
        #    的语义给这两个脚本补回 +x（消费者 add_test 里是直接执行的）。
        for rel in _EXECUTABLE_MODULES:
            target = os.path.join(dst, rel)
            if os.path.isfile(target) and not os.access(target, os.X_OK):
                os.chmod(target, os.stat(target).st_mode | stat.S_IXUSR | stat.S_IXGRP |
                         stat.S_IXOTH)

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.includedirs = []
