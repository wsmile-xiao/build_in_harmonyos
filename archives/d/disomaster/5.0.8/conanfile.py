#!/usr/bin/env python3
"""Conan recipe for disomaster 5.0.8 - Qt wrapper for optical disc operations.

disomaster is a deepin Qt wrapper library for optical-disc image creation,
burning, erasing, and media inspection. Upstream uses libisoburn C API
directly, but OHOS only provides the xorriso executable (from PR !831)
without development headers. This recipe applies a patch that replaces
the libisoburn backend with a QProcess-based xorriso CLI backend.

Build system: qmake (upstream) -> CMake (custom)
License: GPL-3.0-or-later
"""

import os

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
)


class DisomasterConan(ConanFile):
    name = "disomaster"
    version = "5.0.8"
    description = "Qt wrapper for optical-disc image creation, burning, erasing, and media inspection"
    license = "GPL-3.0-or-later"
    homepage = "https://github.com/linuxdeepin/disomaster"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "shared-library"

    settings = "os", "compiler", "build_type", "arch"

    # 导出自定义 CMakeLists.txt（补丁通过 conandata 导出）
    exports_sources = "CMakeLists.txt"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("qt5-qtbase/5.15.2")

    def validate(self):
        # R32: 支持 Linux 和 OHOS
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"disomaster only supports Linux and OHOS, got {self.settings.os}"
            )
        # OHOS 仅支持 armv8 架构
        if self.settings.os == "OHOS" and self.settings.arch != "armv8":
            raise ConanInvalidConfiguration(
                f"disomaster on OHOS only supports armv8, got {self.settings.arch}"
            )

    def layout(self):
        cmake_layout(self)

    def source(self):
        # 下载上游 disomaster 源码
        source_data = self.conan_data["sources"]
        urls = source_data["url"]
        if isinstance(urls, str):
            urls = [urls]
        for url in urls:
            try:
                get(self, url=url, sha256=source_data["sha256"], strip_root=True)
                break
            except ConanException as error:
                self.output.warning(
                    f"Failed to download disomaster source from {url}: {error}"
                )
        else:
            raise ConanException(
                "Unable to download disomaster source from all mirrors"
            )

        # 下载 xorriso 预构建包（source() 中不能访问 self.settings，无条件下载）
        xorriso_data = self.conan_data["xorriso_prebuilt"]
        get(
            self,
            url=xorriso_data["url"],
            sha256=xorriso_data["sha256"],
            destination=os.path.join(self.source_folder, "xorriso_prebuilt"),
            strip_root=False,
            keep_permissions=True,
        )

    def generate(self):
        # CMakeDeps 生成 Qt5Core 等依赖的 CMake 配置文件
        deps = CMakeDeps(self)
        deps.generate()

        tc = CMakeToolchain(self)

        # E092: CMake 不识别 HarmonyOS 平台名，映射为 OHOS
        if self.settings.os == "OHOS":
            tc.blocks["generic_system"].values["cmake_system_name"] = "OHOS"
            tc.blocks["generic_system"].values["cmake_system_processor"] = "aarch64"

        # 传入源码目录和 moc 生成文件路径
        tc.cache_variables["DISOMASTER_SOURCE_DIR"] = self.source_folder
        tc.cache_variables["DISOMASTER_MOC_SOURCE"] = os.path.join(
            self.build_folder, "moc_disomaster.cpp"
        )

        # 手动传递 Qt5 include 目录（CMakeDeps 组件级 includedirs 在此环境未正确传递）
        qt5 = self.dependencies["qt5-qtbase"]
        tc.cache_variables["QT5_INCLUDE_DIR"] = os.path.join(qt5.package_folder, "include")
        tc.cache_variables["QT5_CORE_INCLUDE_DIR"] = os.path.join(qt5.package_folder, "include", "QtCore")
        tc.generate()

    def build(self):
        # 应用补丁（创建 disomaster_cli.cpp）
        apply_conandata_patches(self)

        # 使用 qt5-qtbase 的 moc 工具生成元对象源码
        qt5_base = self.dependencies["qt5-qtbase"].package_folder
        moc_path = os.path.join(qt5_base, "bin", "moc")
        if not os.path.isfile(moc_path):
            raise ConanException(
                "qt5-qtbase/5.15.2 does not provide the required bin/moc tool"
            )

        source_dir = self.source_folder
        header_path = os.path.join(source_dir, "libdisomaster", "disomaster.h")
        moc_output = os.path.join(self.build_folder, "moc_disomaster.cpp")

        # 构建 moc 命令（包含 Qt5 和源码头文件路径）
        moc_cmd = [moc_path]
        for inc in [
            os.path.join(qt5_base, "include"),
            os.path.join(qt5_base, "include", "QtCore"),
            os.path.join(source_dir, "libdisomaster"),
        ]:
            moc_cmd.extend(["-I", inc])
        moc_cmd.extend([header_path, "-o", moc_output])

        self.run(" ".join(f'"{x}"' for x in moc_cmd))

        # CMake 配置和构建
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()

        # 安装 LICENSE
        copy(
            self,
            "LICENSE",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
            keep_path=False,
        )

        # OHOS 平台：签名共享库 + 安装 xorriso
        if self.settings.os == "OHOS":
            self._sign_shared_libs()

            # 安装 xorriso 可执行文件
            xorriso_dir = os.path.join(self.source_folder, "xorriso_prebuilt")
            # 在可能的位置查找 xorriso 二进制文件
            for candidate in [
                os.path.join(xorriso_dir, "bin", "xorriso"),
                os.path.join(xorriso_dir, "xorriso"),
            ]:
                if os.path.isfile(candidate):
                    copy(
                        self,
                        "xorriso",
                        src=os.path.dirname(candidate),
                        dst=os.path.join(self.package_folder, "bin"),
                        keep_path=False,
                    )
                    # 修复可执行文件权限
                    xorriso_pkg = os.path.join(self.package_folder, "bin", "xorriso")
                    if os.path.isfile(xorriso_pkg):
                        os.chmod(xorriso_pkg, 0o755)
                    break

    def _sign_shared_libs(self):
        """OHOS 平台对 .so 文件进行代码签名（ML-0043）"""
        import glob
        libdir = os.path.join(self.package_folder, "lib")
        sos = glob.glob(os.path.join(libdir, "**", "*.so"), recursive=True)
        sos += glob.glob(os.path.join(libdir, "**", "*.so.*"), recursive=True)
        if not sos:
            return
        objcopy = "/data/service/hnp/bin/llvm-objcopy"
        signer = "/data/service/hnp/bin/binary-sign-tool"
        for so in sos:
            if os.path.islink(so):
                continue
            self.run(f'{objcopy} --remove-section .codesign "{so}" 2>/dev/null || true')
            self.run(f'{signer} sign -inFile "{so}" -outFile "{so}" -selfSign 1')

    def package_info(self):
        self.cpp_info.libs = ["disomaster"]
        self.cpp_info.includedirs = ["include/disomaster"]
        self.cpp_info.set_property("cmake_file_name", "disomaster")
        self.cpp_info.set_property("cmake_target_name", "disomaster::disomaster")
        self.cpp_info.set_property("pkg_config_name", "libdisomaster")

        # 如果包含 xorriso 可执行文件，设置运行时环境变量
        xorriso_bin = os.path.join(self.package_folder, "bin", "xorriso")
        if os.path.isfile(xorriso_bin):
            self.runenv_info.prepend_path(
                "PATH", os.path.join(self.package_folder, "bin")
            )
            self.runenv_info.define("DISOMASTER_XORRISO", xorriso_bin)
