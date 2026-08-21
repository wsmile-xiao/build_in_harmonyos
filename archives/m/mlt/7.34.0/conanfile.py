#!/usr/bin/env python3
"""Conan recipe for mlt 7.34.0 — multimedia framework (MLT).

CMake build. OHOS adaptation:
- Core framework + melt CLI, tests enabled (BUILD_TESTING=ON).
- Modules requiring unavailable deps on OHOS are disabled:
  sdl (MOD_SDL2 off), frei0r (MOD_FREI0R off), jack (MOD_JACKRACK off),
  LV2/VST2 (USE_LV2/USE_VST2 off), decklink/glaxnimate/ndi off.
- Requires: ffmpeg (avformat) + libxml2 (both published to ohpcd).
"""
import os

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get
from conan.tools.scm import Version


class MltConan(ConanFile):
    name = "mlt"
    version = "7.34.0"
    description = "MLT multimedia framework (open source movie editor toolkit)"
    license = "LGPL-2.1"
    homepage = "https://www.mltframework.org/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False]}
    default_options = {"shared": True}

    def export_sources(self):
        export_conandata_patches(self)

    requires = (
        "ffmpeg/6.1.6",
        "libxml2/2.15.3",
        "qtbase/6.11.1",
    )

    def configure(self):
        # ohpcd publishes ffmpeg/6.1.6 as shared:True — match it to reuse the
        # prebuilt binary instead of triggering a long source build on CI
        self.options["ffmpeg"].shared = True
        # qtbase/6.11.1 提供 Qt6Test 组件（Qt6::Core/Qt6::Test），供上游 src/tests/
        # QtTest 套件链接；制品仓 qtbase 为 shared:True，匹配以复用预编译包
        self.options["qtbase"].shared = True

    def layout(self):
        cmake_layout(self)

    def generate(self):
        tc = CMakeToolchain(self)
        # 注入 qtbase 的 cmake 目录到 CMAKE_PREFIX_PATH，使 mlt 的 find_package(Qt6)
        # 能找到 Qt6Config.cmake（qtbase/6.11.1 提供 Qt6::Core/Qt6::Test 组件）。
        # 同时显式设置 Qt6_DIR 强制 config 模式查找（mlt 的 CMAKE_MODULE_PATH 会干扰
        # find_package(Qt6) 走 module 模式，导致找不到 FindQt6.cmake 而失败）
        if self.dependencies.get("qtbase"):
            qt_prefix = self.dependencies["qtbase"].package_folder
            qt_cmake = os.path.join(qt_prefix, "lib", "cmake")
            tc.variables["CMAKE_PREFIX_PATH"] = qt_cmake
            tc.variables["Qt6_DIR"] = os.path.join(qt_cmake, "Qt6")
        # Kwalify 为 Ruby gem（本机已安装 kwalify-0.7.2 + Psych 兼容补丁），
        # 显式注入 Kwalify_EXECUTABLE 使 mlt 的 find_program(kwalify) 能找到，
        # 供 src/tests/ 的 kwalify schema 校验测试使用
        kwalify_bin = "/storage/Users/currentUser/.local/share/gem/ruby/3.4.0/gems/kwalify-0.7.2/bin/kwalify"
        if os.path.isfile(kwalify_bin):
            tc.variables["Kwalify_EXECUTABLE"] = kwalify_bin
        # libxml2 制品仓提供 libxml-2.0.pc（MOD_XML 模块 pkg_check_modules 需要），
        # 但 .pc 的 prefix 写死 /usr/local，CMake 报 include 路径不存在。
        # 生成修正版 .pc（prefix 指向 conan 实际路径）并优先注入 PKG_CONFIG_PATH
        if self.dependencies.get("libxml2"):
            xml_prefix = self.dependencies["libxml2"].package_folder
            pc_orig = os.path.join(xml_prefix, "lib", "pkgconfig", "libxml-2.0.pc")
            pc_fixed = os.path.join(self.build_folder, "pkgconfig_fixed", "libxml-2.0.pc")
            if os.path.isfile(pc_orig):
                os.makedirs(os.path.dirname(pc_fixed), exist_ok=True)
                with open(pc_orig) as f:
                    content = f.read()
                content = content.replace("prefix=/usr/local", f"prefix={xml_prefix}")
                with open(pc_fixed, "w") as f:
                    f.write(content)
                from conan.tools.env import Environment
                env = Environment()
                env.prepend_path("PKG_CONFIG_PATH", os.path.dirname(pc_fixed))
                # OHOS SDK 的 lld（链接器）自身依赖 SDK 的 libxml2.so.16（RUNPATH=$ORIGIN/../lib）；
                # conan 将 mlt 依赖的 libxml2 目录注入 LD_LIBRARY_PATH 后优先级高于 RUNPATH，
                # 导致 lld 加载 conan 版 libxml2（符号版本不匹配，xmlFreeDoc symbol not found），
                # CMake ABI 检测崩溃。前置 SDK llvm/lib 使 lld 加载 SDK 自带的 libxml2。
                sdk_llvm_lib = "/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/llvm/lib"
                if os.path.isdir(sdk_llvm_lib):
                    env.prepend_path("LD_LIBRARY_PATH", sdk_llvm_lib)
                env.vars(self).save_script("pkgconfig_path")
        # Modules that need unavailable OHOS deps — disable them
        tc.variables["MOD_SDL2"] = "OFF"
        tc.variables["MOD_FREI0R"] = "OFF"
        tc.variables["MOD_JACKRACK"] = "OFF"
        tc.variables["MOD_MOVIT"] = "OFF"
        tc.variables["MOD_RTAUDIO"] = "OFF"
        tc.variables["MOD_SOX"] = "OFF"
        tc.variables["MOD_VORBIS"] = "OFF"
        # MOD_XML 保持 ON：libxml2/2.15.3 制品仓提供 libxml-2.0.pc（pkg-config 可解析），
        # test_xml/test_service 依赖 xml consumer 插件（libmltxml.so），关闭会导致崩溃
        tc.variables["MOD_DECKLINK"] = "OFF"
        tc.variables["MOD_GDK"] = "OFF"
        tc.variables["MOD_KDENLIVE"] = "OFF"
        tc.variables["MOD_GLAXNIMATE"] = "OFF"
        tc.variables["MOD_GLAXNIMATE_QT6"] = "OFF"
        tc.variables["MOD_QT6"] = "OFF"
        tc.variables["MOD_NDI"] = "OFF"
        tc.variables["USE_LV2"] = "OFF"
        tc.variables["USE_VST2"] = "OFF"
        tc.variables["GPL"] = "OFF"
        tc.variables["GPL3"] = "OFF"
        # 上游 src/tests/ QtTest 套件依赖 Qt6::Core/Qt6::Test（qtbase/6.11.1 提供）
        # + mlt++；开启 BUILD_TESTING 构建运行上游测试。Kwalify 缺失（制品仓无此包），
        # 通过补丁把 find_package(Kwalify REQUIRED) 改为 QUIET 绕过（kwalify 测试项跳过）。
        tc.variables["BUILD_TESTING"] = "ON"
        tc.variables["BUILD_TESTS_WITH_QT6"] = "ON"
        tc.variables["BUILD_DOCS"] = "OFF"
        tc.variables["CLANG_FORMAT"] = "OFF"
        tc.generate()

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        apply_conandata_patches(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        self.cpp_info.libs = ["mlt"]
