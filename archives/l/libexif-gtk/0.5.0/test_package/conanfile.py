#!/usr/bin/env python3
"""Consumer test for libexif-gtk 0.5.0 (conan test_package).

R34/PF3: test() 必须实质运行被测包 —— 这里编译并运行 test_libexif_gtk，
它调用 libexif-gtk 导出 API（gtk_exif_browser_get_type() 等）并 dlopen 共享库
做符号完整性检查，共 6 条断言（含 1 条鸿蒙特有用例 OHOS-1）。

链接方式：pkg-config（见 CMakeLists.txt 注释）—— gtk/3.24.43 是扁平包，
CMakeDeps 目标传不出 pango→harfbuzz 的传递头目录。

注：GTK 控件实例化需要显示后端，CI 无显示，故用例只覆盖不需要显示的
GType 注册 / 符号解析 / libexif 数据模型路径。上游无自动化测试
（Makefile.am 无 TESTS=/check_PROGRAMS），上游示例的交互式运行统计见
reports/test-report.md，二者不互相替代。
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout
from conan.tools.env import Environment
from conan.tools.gnu import PkgConfigDeps


class LibexifGtkTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeToolchain", "PkgConfigDeps"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def _pkg_config_env(self):
        # PkgConfigDeps 把全依赖图的 .pc（含被测包自身的 libexif-gtk3.pc）
        # 写进 generators 目录；cmake configure 期的 pkg_check_modules 需要它。
        env = Environment()
        env.prepend_path("PKG_CONFIG_PATH", self.generators_folder)
        return env

    def build(self):
        with self._pkg_config_env().vars(self).apply():
            cmake = CMake(self)
            cmake.configure()
            cmake.build()

    def test(self):
        bindirs = self.cpp.build.bindirs
        if not bindirs:
            raise RuntimeError("test_libexif_gtk bindir was not produced")
        exe = os.path.join(bindirs[0], "test_libexif_gtk")
        if not os.path.isfile(exe):
            raise RuntimeError("test_libexif_gtk binary missing: {}".format(exe))
        # conanrun 环境提供被测包与全部传递依赖（gtk/libexif/...）的 LD_LIBRARY_PATH
        self.run('"{}"'.format(exe), env="conanrun")
