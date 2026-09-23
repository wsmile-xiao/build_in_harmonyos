#!/usr/bin/env python3
"""Conan recipe — suil 0.10.26 (LV2 plugin GUI hosting library).

suil 是 LV2 生态的插件 GUI 承载库：宿主通过 libsuil 动态加载各 GUI
工具包（Qt/GTK/X11/Cocoa）适配模块，把插件 UI 嵌入宿主窗口，而宿主
本身不直接依赖任何 GUI 工具包。

上游 0.10.26 构建系统为 meson（2021 年起 LV2 全家桶已从 waf 迁移到
meson，仓内 lv2/1.18.11-git 同系先例）。核心库 libsuil-0 只依赖
lv2 + dl；GUI 适配模块按 feature 开关编译。OHOS PC 无 X11/GTK/Qt
窗口系统接入（无 gtk+-2.0/gtk+-3.0/Qt5Widgets/x11 pkg-config），全
部 GUI 后端按上游 feature 开关禁用——符合上游 PACKAGING.md 的设计
意图：主库不依赖任何工具包，模块按发行版环境单独打包。GUI 模块后续
可在 GUI 框架（Qt for OHOS 等）落地后按同款配方追加。

产物：libsuil-0.so（versioned soname，支持并行安装 0.x/1.x 主版本）
+ include/suil-0/suil/suil.h + lib/pkgconfig/suil-0.pc。
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.env import VirtualBuildEnv
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get, rmdir
from conan.tools.layout import basic_layout
from conan.tools.meson import Meson, MesonToolchain


class SuilConan(ConanFile):
    name = "suil"
    version = "0.10.26"
    description = "Library for loading and wrapping LV2 plugin UIs"
    license = "0BSD OR ISC"
    homepage = "https://drobilla.net/software/suil.html"
    url = "https://gitlab.com/lv2/suil"
    topics = ("lv2", "audio", "plugin", "gui", "wrapper")

    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
    }
    default_options = {
        "shared": True,
        "fPIC": True,
    }

    def export_sources(self):
        export_conandata_patches(self)

    def configure(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"suil/0.10.26 recipe currently supports Linux and OHOS (got {self.settings.os})"
            )
        if not self.options.shared:
            # 上游 meson.build 以 shared library + shared_module 设计：
            # libsuil 通过 dlopen 加载 GUI 适配模块，上游未提供静态库
            # 安装路径（SUIL_STATIC 仅影响编译宏，不改变库类型）。
            raise ConanInvalidConfiguration(
                "suil/0.10.26 upstream only installs a shared library (versioned soname)"
            )
        self.options.rm_safe("fPIC")

    def requirements(self):
        self.requires("lv2/1.18.11-git")

    def build_requirements(self):
        # 上游构建系统为 Meson（制品仓已发布，c-list/c-rbtree 同款先例）
        self.tool_requires("meson/1.11.0")
        self.tool_requires("ninja/1.12.1")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        # 上游 meson.build 以 dependency('lv2') 消费 LV2（include_type:
        # system + version >= 1.18.4），读取 lv2.pc。lv2/1.18.11-git 的
        # package_info 已设置 pkg_config_name=lv2 且制品仓包内自带
        # lib/pkgconfig/lv2.pc（prefix=${pcfiledir}/../.. 自定位），这里
        # 用 PkgConfigDeps 生成到 generators 目录并让 meson 经
        # PKG_CONFIG_PATH 命中（c-rbtree 3.2.0 手写 pc shim 的免 shim 变体）。
        from conan.tools.gnu.pkgconfigdeps import PkgConfigDeps

        PkgConfigDeps(self).generate()
        VirtualBuildEnv(self).generate()

        tc = MesonToolchain(self)
        # §6.2: CI worker 的 PATH 不含 llvm-ar/llvm-ranlib，Meson 在
        # project() 阶段探测链接器会失败；从 profile compiler_executables
        # 的编译器绝对路径推导同目录工具，写入 machine file 的 [binaries]
        # （c-list 3.1.0 同款先例）。
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        )
        cc = compilers.get("c") if compilers else None
        if cc:
            tool_dir = os.path.dirname(cc)
            tc.binaries["ar"] = os.path.join(tool_dir, "llvm-ar")
            tc.binaries["ranlib"] = os.path.join(tool_dir, "llvm-ranlib")
        tc.project_options.update({
            # OHOS PC 无 X11/GTK/Qt 窗口系统接入，GUI 适配模块全部
            # 按上游 feature 开关禁用（上游 PACKAGING.md：主库不依赖
            # 任何工具包，模块按环境单独打包）。
            "gtk2": "disabled",
            "gtk3": "disabled",
            "qt5": "disabled",
            "qt6": "disabled",
            "x11": "disabled",
            "cocoa": "disabled",
            "docs": "disabled",
            # 上游 test/headers：编译并运行 headers 冒烟测试
            "tests": "enabled",
        })
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        meson = Meson(self)
        meson.configure()
        meson.build()

    def package(self):
        meson = Meson(self)
        meson.install()
        # 上游安装 libsuil-0.so.0.10.26 + .so.0/.so 两条符号链接；HMDFS
        # 上保留（meson install 已实测可用），但删除 share/ 等空目录残留
        rmdir(self, os.path.join(self.package_folder, "share"))
        # 交叉编译环境跑不了 meson test（exit 77 SKIP），headers 测试
        # 二进制保留在 build 目录，由 test_package 消费者视角验证。

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "suil-0")
        self.cpp_info.set_property("cmake_target_name", "suil-0::suil-0")
        self.cpp_info.set_property("pkg_config_name", "suil-0")
        self.cpp_info.libs = ["suil-0"]
        self.cpp_info.libdirs = ["lib"]
        if self.settings.os in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["dl"]
        # 上游安装头文件到 versioned 目录 include/suil-0/suil/suil.h，
        # 消费者 #include <suil/suil.h>（经 suil-0.pc 的
        # Cflags: -I${includedir}/suil-0）；conan 侧给出 versioned 子目录
        # 作为 include 路径。
        self.cpp_info.includedirs = [os.path.join("include", "suil-0")]
