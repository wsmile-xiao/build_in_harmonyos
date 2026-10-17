#!/usr/bin/env python3
"""Conan recipe — qdiskinfo 0.4-git20251119.

QDiskInfo 是 smartctl（smartmontools）的 Qt6 图形前端，以 CrystalDiskInfo
风格展示 ATA / NVMe 磁盘的 S.M.A.R.T. 数据。上游为 CMake + Qt6 Widgets
的桌面可执行程序。

OHOS 适配要点：
- HarmonyOS PC 没有 polkit / pkexec：上游在有 / 无特权两种路径上都用
  ``pkexec`` 提权（scanDevices / initiateSelfTest / cancelSelfTest /
  mainwindow 的 --ascii-view）。``QProcess::start("pkexec", ...)`` 在
  pkexec 不存在时启动失败，``exitCode()`` 返回 0 且 ``isOpen()`` 为假，
  上层只会看到“空结果”——既没有报错也没有数据（静默失败）。
  补丁 0001 增加运行时探测：pkexec 存在则继续用 pkexec 提权（保持
  Linux 行为不变），不存在则直接执行命令（OHOS 场景，权限由调用方决定），
  并在找不到 smartctl 时明确报错。
- 上游关于对话框把平台写成 "Linux"，补丁 0002 改为通用表述。
- smartctl 为运行时依赖（上游 AppImage 也把 smartctl 一起打包），
  因此这里声明 ``requires("smartmontools/7.4")``，``conan install`` 后
  smartctl 即在 PATH 中，``getSmartctlPath()`` 可直接找到。
- 翻译（ENABLE_TRANSLATIONS）保持上游默认 OFF：qtbase 包不提供
  Qt6LinguistTools 组件（OHOS 无 lupdate/lrelease 原生工具链），
  上游官方 AppImage 构建同样未开启该选项。
- OHOS 内核只加载带有效 ``.codesign`` 段的 ELF，而 ``cmake --install``
  为去掉构建期 RPATH 会重写 ELF、使链接器写入的签名失效（真机执行报
  EPERM，构建树内却可直接执行）。``package()`` 在安装后按 E077 四步
  重新自签名。
"""
import os
import shutil

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.env import Environment
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get


class QdiskinfoConan(ConanFile):
    name = "qdiskinfo"
    version = "0.4-git20251119"
    description = ("QDiskInfo 0.4 — smartctl 的 Qt6 图形前端，"
                   "以 CrystalDiskInfo 风格展示 ATA/NVMe 磁盘 S.M.A.R.T. 数据")
    license = "GPL-3.0-or-later"
    homepage = "https://github.com/edisionnano/QDiskInfo"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "application"
    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("qtbase/6.11.1.3")
        # 运行时依赖：QDiskInfo 通过 QProcess 调用 smartctl（smartctl -x --json=o）。
        # 上游 AppImage 同样把 smartctl 随应用一起分发。
        self.requires("smartmontools/7.4")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        apply_conandata_patches(self)

    def generate(self):
        tc = CMakeToolchain(self)
        # Qt6 + 上游默认：不启用翻译（无 Qt6LinguistTools 组件）
        tc.variables["QT_VERSION_MAJOR"] = 6
        tc.variables["ENABLE_TRANSLATIONS"] = "OFF"
        tc.generate()
        CMakeDeps(self).generate()
        # qtbase 以 cmake_find_mode=none 导出自身的 Qt6Config.cmake，
        # 需要把它的包目录放进 CMAKE_PREFIX_PATH 才能被 find_package 命中。
        env = Environment()
        env.append_path("CMAKE_PREFIX_PATH",
                        self.dependencies["qtbase"].package_folder)
        env.vars(self, scope="build").save_script("conan_qt6_prefix")

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    @staticmethod
    def _is_elf(path):
        try:
            with open(path, "rb") as handle:
                return handle.read(4) == b"\x7fELF"
        except OSError:
            return False

    def _sign_ohos_elfs(self):
        """对 package 目录内的 ELF 重新做 OHOS 自签名（E077）。

        HarmonyOS 内核只加载带有效 ``.codesign`` 段的 ELF；而
        ``cmake --install`` 会为去掉构建期 RPATH 而改写 ELF
        （"Set non-toolchain portion of runtime path ... to ''"），
        使链接器写入的签名失效 → 真机执行报 EPERM（Operation not
        permitted）。因此安装完成后必须按“去签名 → 自签名 → 恢复执行位”
        的顺序重新签名。
        """
        if str(self.settings.os) != "OHOS":
            return
        objcopy = shutil.which("llvm-objcopy") or "llvm-objcopy"
        signer = next((c for c in (shutil.which("binary-sign-tool"),
                                   "/data/service/hnp/bin/binary-sign-tool",
                                   "/data/app/bin/binary-sign-tool")
                       if c and os.path.isfile(c)), None)
        if not signer:
            raise ConanException(
                "OHOS 需要 binary-sign-tool 对包内 ELF 签名（PATH 与 hnp bin 均未找到）")
        signed = 0
        for root, _, files in os.walk(self.package_folder):
            for name in files:
                path = os.path.join(root, name)
                if os.path.islink(path) or not self._is_elf(path):
                    continue
                self.run(f'"{objcopy}" --remove-section .codesign "{path}"',
                         ignore_errors=True)
                self.run(f'"{signer}" sign -inFile "{path}" -outFile "{path}" -selfSign 1')
                # 签名工具会把文件 mode 归零，需恢复执行位
                os.chmod(path, os.stat(path).st_mode | 0o111)
                signed += 1
        self.output.info(f"已对 {signed} 个 OHOS ELF 自签名")

    def package(self):
        cmake = CMake(self)
        cmake.install()
        self._sign_ohos_elfs()

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
