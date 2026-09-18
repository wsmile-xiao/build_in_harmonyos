#!/usr/bin/env python3
"""Conan recipe — liborigin 3.0.4 (CMake).

liborigin 是读取 OriginLab 项目文件（.opj）的 C++ 库（GPL-3.0-or-later，
Stefan Gerlach 维护，GitHub gerlachs/liborigin）。上游 CMake ≥ 3.16，C++17，
无第三方依赖（tree.hh / endianfstream.hh 为源码自带）。产物：
liborigin.{a,so.3.0.4} 与公共头文件，外加 bin/opj2dat（.opj → .dat 导出工具）。

适配要点（证据见 notes.md 与 reports/）：
- os=OHOS 时 Conan 默认把 CMAKE_SYSTEM_NAME 设为 HarmonyOS，而 SDK CMake 只有
  Modules/Platform/OHOS.cmake（内容为 include(Platform/Linux)），没有
  Platform/HarmonyOS.cmake。名字对不上时平台变量留空，
  CMAKE_SHARED_LIBRARY_SONAME_C_FLAG 缺失 → .so 无 DT_SONAME、无版本软链。
  按归档 fmt 11.1.3 的做法显式设 cmake_system_name=OHOS；设备实测
  SONAME=liborigin.so.3、liborigin.so.3 → liborigin.so.3.0.4 软链齐全。
- 上游默认同时构建静态与动态库（BUILD_STATIC_LIBS、BUILD_SHARED_LIBS 均为 ON，
  两个目标同名安装），本配方用 shared 选项映射为二选一，保证 package_id 与
  实际产物一致；opj2dat 随之链接对应实现。
- 上游 CMakeLists 在 find_package(Doxygen) 命中时会向 ALL 添加 doc 目标，
  显式关闭以保证任意构建机上结果一致。
- 上游安装的 lib/pkgconfig/liborigin.pc 内嵌 configure 期 prefix，删除并由
  pkg_config_name 交给 Conan 生成。
- OHOS 上 ELF 必须携带有效 .codesign；安装阶段 CMake 清掉可执行文件的构建期
  RUNPATH 会使原签名失效（共享版 bin/opj2dat 实测 rc=126 EPERM），
  package() 里对包内 ELF 重新自签名。
"""
import os
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
    rmdir,
)


class LiboriginConan(ConanFile):
    name = "liborigin"
    version = "3.0.4"
    description = ("C++ library for reading OriginLab project files (.opj), "
                   "with the opj2dat data export tool")
    license = "GPL-3.0-or-later"
    homepage = "https://github.com/gerlachs/liborigin"
    url = "https://atomgit.com/OpenHarmonyPCDeveloper/build_in_harmonyos/tree/main/archives/l/liborigin/3.0.4"
    topics = ("origin", "opj", "scientific-data", "file-format")
    package_type = "library"
    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}

    def export_sources(self):
        export_conandata_patches(self)

    def config_options(self):
        if self.settings.os == "Windows":
            del self.options.fPIC

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"{self.name} is validated for Linux/OHOS, not {self.settings.os}")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        if self.settings.os == "OHOS":
            # 见文件头：SDK 只有 Platform/OHOS.cmake。缺 SONAME 会传染给下游。
            tc.blocks["generic_system"].values["cmake_system_name"] = "OHOS"
            tc.blocks["generic_system"].values["cmake_system_processor"] = "aarch64"
        tc.variables["BUILD_SHARED_LIBS"] = "ON" if self.options.shared else "OFF"
        tc.variables["BUILD_STATIC_LIBS"] = "OFF" if self.options.shared else "ON"
        tc.variables["CMAKE_DISABLE_FIND_PACKAGE_Doxygen"] = "ON"
        # 64 位平台上 GNUInstallDirs 可能改写为 lib64，而 cpp_info.libdirs 默认 lib。
        tc.variables["CMAKE_INSTALL_LIBDIR"] = "lib"
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()
        copy(self, "COPYING", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))
        # 上游 .pc 内嵌 configure 期 prefix，消费方路径由 Conan 生成。
        rmdir(self, os.path.join(self.package_folder, "lib", "pkgconfig"))
        self._sign_package_elfs()

    def _sign_package_elfs(self):
        """OHOS 上 ELF 需带有效 .codesign 才能执行/加载。

        安装阶段 CMake 会把可执行文件的构建期 RUNPATH 清掉，字节一变
        .codesign 即失效——设备实测直接执行共享版 bin/opj2dat 报
        "Operation not permitted"（rc=126），重新签名后恢复正常。
        对包内 bin/、lib/ 下的真实 ELF（跳过版本化 .so 软链）去旧签名段后
        自签名，与归档 fmt 11.1.3 同一做法。非 OHOS 直接返回。
        """
        if self.settings.os != "OHOS":
            return
        targets = []
        for folder in (os.path.join(self.package_folder, "bin"),
                       os.path.join(self.package_folder, "lib")):
            if not os.path.isdir(folder):
                continue
            for root, _dirs, names in os.walk(folder):
                for name in names:
                    path = os.path.join(root, name)
                    if not os.path.islink(path) and self._is_elf(path):
                        targets.append(path)
        if not targets:
            return
        objcopy = self._resolve_sign_tool(
            "/data/service/hnp/bin/llvm-objcopy", "llvm-objcopy")
        signer = self._resolve_sign_tool(
            "/data/service/hnp/bin/binary-sign-tool", "binary-sign-tool")
        for path in sorted(targets):
            self.run(f'"{objcopy}" --remove-section .codesign "{path}" '
                     f'2>/dev/null || true')
            self.run(f'"{signer}" sign -inFile "{path}" -outFile "{path}" '
                     f'-selfSign 1')

    @staticmethod
    def _is_elf(path):
        try:
            with open(path, "rb") as handle:
                return handle.read(4) == b"\x7fELF"
        except OSError:
            return False

    @staticmethod
    def _resolve_sign_tool(hardcoded, name):
        # CI 机器工具在 /data/service/hnp/bin；开发机同款工具在 PATH 中。
        if os.path.exists(hardcoded):
            return hardcoded
        return shutil.which(name) or hardcoded

    def package_info(self):
        self.cpp_info.libs = ["origin"]
        # 头文件安装在 include/liborigin/，与上游 .pc 的 Cflags 一致。
        self.cpp_info.includedirs = [os.path.join("include", "liborigin")]
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.set_property("cmake_file_name", "liborigin")
        self.cpp_info.set_property("cmake_target_name", "liborigin::liborigin")
        self.cpp_info.set_property("pkg_config_name", "liborigin")
