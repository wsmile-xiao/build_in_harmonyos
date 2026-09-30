#!/usr/bin/env python3
"""Conan recipe — olcPixelGameEngine 2.30 (header-only, 无构建打包族).

olcPixelGameEngine 是 OneLoneCoder 的单头文件 C++17 游戏引擎（OLC-3 许可）。
上游无构建系统，无第三方依赖，按 header-only 打包：
包内导出 olcPixelGameEngine.h + extensions/olcPGEX_*.h + utilities/olcUTIL_*.h。

OHOS 平台说明：上游原生窗口后端仅覆盖 Win32/X11/GLUT/Emscripten，OHOS 无
对应后端；消费方按上游支持的无头模式（-DOLC_PGE_HEADLESS）编译使用，已在本
任务中于 OHOS aarch64 实测可编译、可链接、可运行（见 test_package/test.cpp）。
"""
import os

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.files import get, copy, export_conandata_patches, apply_conandata_patches
from conan.tools.layout import basic_layout


class OlcpixelgameengineConan(ConanFile):
    name = "olcpixelgameengine"
    version = "2.30"
    description = "olcPixelGameEngine - a single header C++17 game engine by OneLoneCoder"
    license = "OLC-3"
    homepage = "https://github.com/OneLoneCoder/olcPixelGameEngine"
    url = ""  # CI fills this

    package_type = "header-library"

    settings = "os", "compiler", "build_type", "arch"

    no_copy_source = True

    def layout(self):
        basic_layout(self)

    def export_sources(self):
        export_conandata_patches(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        # header-only：无编译产物。应用 conandata 声明的补丁（当前 patches: {}），
        # 并做真实完整性检查（R34：不伪造编译日志，只校验主头文件存在）。
        apply_conandata_patches(self)
        header = os.path.join(self.source_folder, "olcPixelGameEngine.h")
        if not os.path.exists(header):
            raise ConanException(f"missing source header: {header}")

    def package(self):
        copy(self, "olcPixelGameEngine.h", src=self.source_folder,
             dst=os.path.join(self.package_folder, "include"), keep_path=False)
        copy(self, "olcPGEX_*.h", src=os.path.join(self.source_folder, "extensions"),
             dst=os.path.join(self.package_folder, "include"), keep_path=False)
        copy(self, "olcUTIL_*.h", src=os.path.join(self.source_folder, "utilities"),
             dst=os.path.join(self.package_folder, "include"), keep_path=False)
        copy(self, "LICENCE.md", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"), keep_path=False)

    def package_id(self):
        self.info.clear()  # 无构建产物依赖 os/compiler → 单一 package_id

    def package_info(self):
        self.cpp_info.bindirs = []
        self.cpp_info.libdirs = []
