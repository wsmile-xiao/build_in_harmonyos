#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ink 0.5.3 —— HarmonyOS PC (OHOS / aarch64) 适配配方

ink 是 libinklevel 的命令行前端（单二进制，上游仅 ink.c/malloc.c 两个源文件），
autotools 构建。configure 用 AC_CHECK_HEADERS(inklevel.h)/AC_CHECK_LIB(inklevel)
直接探测依赖（非 pkg-config）；libinklevel/0.9.7 已在制品仓发布，按 R36 直接依赖。

适配要点（patches/）：
  * 0001-config.guess.patch / 0002-config.sub.patch
    上游 2018-02 vintage 的 GNU config 不识别 HarmonyOS/OHOS 三元组，configure
    第一阶段即报 "cannot guess build type" 退出 1（E007）。内置
    patch-autotools-ohos.pl 对该 vintage 补不全（Score 1/5），按 libinklevel
    0.9.7 同款最小改动手补：config.guess 增 HarmonyOS uname 分支产出
    aarch64-unknown-linux-ohos；config.sub 放行 linux-ohos。不含平台宏。
  * 0003-configure-mktemp.patch
    autoconf 2.69 生成的 configure 用 mktemp -d ./confXXXXXX 建临时目录，该
    分支在 HMDFS 上历史不可用（E490，libinklevel 同源实证），改为固定目录名，
    语义与上游 fallback 分支一致。

依赖注入：AutotoolsDeps 把 libinklevel 的 -I/-L/-l 喂进 conanbuild 环境；
另按 aaphoto 先例补 LD_LIBRARY_PATH 供 conftest 与运行期加载共享库。
路径全部落在 Conan 构建目录，不写共享 /usr/local（R49）。
"""
from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.env import Environment
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import Autotools, AutotoolsToolchain, AutotoolsDeps
from conan.tools.layout import basic_layout


class InkConan(ConanFile):
    name = "ink"
    version = "0.5.3"
    description = ("ink displays the ink level of inkjet printers (HP) via "
                   "USB or BJNP — command-line frontend of libinklevel")
    license = "GPL-2.0"
    homepage = "https://ink.sourceforge.io/"
    url = ""  # CI fills this

    # CLI tool, not a library (R38: commands.json declared at software level)
    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("libinklevel/0.9.7")

    def validate(self):
        # R32: settings.os 必须兼容判断，不能 == "Linux"
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"ink is only supported on Linux/OHOS, not {self.settings.os}"
            )

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)
        apply_conandata_patches(self)

    def generate(self):
        # configure 用 AC_CHECK_HEADERS/AC_CHECK_LIB 探测（非 pkg-config）：
        # AutotoolsDeps 把 libinklevel 的 -I/-L/-l 注入 conanbuild 环境
        deps = AutotoolsDeps(self)
        deps.generate()
        tc = AutotoolsToolchain(self)
        tc.generate()
        # OHOS loader 对 conan 缓存中的共享库无默认搜索路径；configure 的
        # conftest 与运行期都需要 LD_LIBRARY_PATH 指向依赖 lib 目录（aaphoto 同款）
        env = Environment()
        for dep in self.dependencies.values():
            for libdir in dep.cpp_info.libdirs:
                env.prepend_path("LD_LIBRARY_PATH", libdir)
        env.vars(self, scope="build").save_script("conanbuild_runpath")

    def build(self):
        autotools = Autotools(self)
        autotools.configure()
        # R9: 单任务编译——并行 make 在 HMDFS 上撞 jobserver fifo EPERM（E074）
        autotools.make(args=["-j1"])

    def package(self):
        autotools = Autotools(self)
        autotools.install()

    def package_info(self):
        # 独立命令行二进制，无库信息
        self.cpp_info.libs = []
        self.cpp_info.bindirs = ["bin"]
