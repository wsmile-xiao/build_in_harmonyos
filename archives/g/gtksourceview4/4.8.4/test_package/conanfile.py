#!/usr/bin/env python3
"""Conan test_package for gtksourceview4 4.8.4 — consumer test (L1).

Builds test_gtksourceview4.c — a real GtkSourceView 4 consumer program
(version macros, language manager whose language-spec XML is parsed through
libxml2, language metadata, style scheme manager, buffer text roundtrip and an
asynchronous search context) — with CMake and runs it headless. GtkSourceView 4
is GTK3-based, but none of the APIs exercised here open a display connection,
which is what makes the test meaningful on HarmonyOS PC (no window system).
"""
import os

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, cmake_layout
from conan.tools.env import Environment


class GtkSourceView4TestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    # ⚠️ 显式列出 generators 会替换 conan 默认集，必须带上 VirtualRunEnv：
    # 否则 test() 里 env="conanrun" 拿不到依赖的 LD_LIBRARY_PATH
    # （gtksourceview3 test_package 同款教训）。
    generators = "CMakeDeps", "CMakeToolchain", "PkgConfigDeps", "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)
        # ⚠️ gtksourceview4 的公共头包含 gtk/glib/gio/gobject/fribidi，而
        # CMakeDeps 对「传递依赖」只生成空数据（conan 2.29 行为）→ 显式声明
        # 直接依赖，test 编译链接才拿得到头文件与库。
        self.requires("gtk/3.24.43")
        self.requires("libxml2/2.15.3")
        self.requires("fribidi/1.0.16")

    def layout(self):
        cmake_layout(self)

    def generate(self):
        env = Environment()
        if self.settings.os == "OHOS":
            # OHOS：gtk 传递依赖（harfbuzz 等）NEEDED libc++_shared.so，而 conan
            # 依赖图不携带该库，由系统 /system/lib64 提供（gtksourceview3 同款）。
            env.prepend_path("LD_LIBRARY_PATH", "/system/lib64")
        # 语言规格 XML 不会装到 /usr/share（OHOS 无该前缀）：显式把包的 share
        # 目录与 language-specs 目录交给被测程序。
        pkg = self.dependencies[self.tested_reference_str]
        share = os.path.join(pkg.package_folder, "share")
        env.prepend_path("XDG_DATA_DIRS", share)
        env.define_path("GSV_LANGSPECS_DIR",
                        os.path.join(share, "gtksourceview-4", "language-specs"))
        env.vars(self).save_script("gsv4_test_env")

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        if not can_run(self):
            self.output.warning("Cannot run the test binary in this environment")
            return
        bin_path = os.path.join(self.cpp.build.bindirs[0], "test_gtksourceview4")
        self.run(bin_path, env=["conanrun", "gsv4_test_env"], cwd=self.build_folder)
