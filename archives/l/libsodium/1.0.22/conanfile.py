#!/usr/bin/env python3
import os
from conan import ConanFile
# 必须用 conan.tools.gnu（非 conan.tools.autotools）——CI conan 环境无
# conan.tools.autotools 模块（libgd #19569 实测 ModuleNotFoundError；alpine 用 gnu 正常）
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.files import apply_conandata_patches, get
from conan.tools.layout import basic_layout


class LibsodiumConan(ConanFile):
    name = "libsodium"
    version = "1.0.22"
    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    # library 类型必须声明 shared 选项（conan 2 校验——cattle/sherlock.lv2 先例）
    options = {"shared": [True, False]}
    default_options = {"shared": False}
    # 导出 patches/（apply_conandata_patches 需要——multitail 教训）
    exports_sources = "patches/*"
    # 无外部依赖（libsodium 为纯 C 加密库——configure 无 pkg-config/库检查）

    def layout(self):
        basic_layout(self)

    def generate(self):
        tc = AutotoolsToolchain(self)
        machine = self._machine(self.settings.arch)
        triplet = f"{machine}-unknown-linux-gnu"
        # --disable-shared --enable-static：静态链接（drill/cattle 先例）；
        # --build/--host 三元组（config.guess 无法识别 HarmonyOS——alpine/cattle 教训）
        tc.configure_args.extend(
            ["--disable-shared", "--enable-static",
             f"--build={triplet}", f"--host={triplet}"])
        tc.generate()

    def source(self):
        # 下载源码 + 剥离顶层目录（GitHub archive 解压带 libsodium-1.0.22/
        # 顶层——configure 在子目录——patch 目标 a/configure 不存在【CI
        # #23019 实测】——strip_root 到 source_folder 顶层——abduco 教训）
        get(self, **self.conan_data["sources"][self.version], strip_root=True)
        # 显式应用 0001-configure-umask.patch（multitail 教训：必须显式调用
        # apply_conandata_patches——否则补丁不会被应用）
        apply_conandata_patches(self)

    def build(self):
        autotools = Autotools(self)
        autotools.configure()
        # -j1：OHOS 沙箱不支持 mkfifo（jobserver），并行编译失败（opensp 先例）
        autotools.make(args=["-j1"])

    def package(self):
        autotools = Autotools(self)
        autotools.install()
        # conan 2 无 self.copy（AttributeError——CI #23065 实测）——
        # 用 conan.tools.files 的 copy 函数（make install 已装大部分
        # 头文件——sodium.h 补充复制）
        from conan.tools.files import copy
        copy(self, "sodium.h",
             src=os.path.join(self.source_folder, "include"),
             dst=os.path.join(self.package_folder, "include"),
             keep_path=False)
        copy(self, "*.h",
             src=os.path.join(self.source_folder, "include", "sodium"),
             dst=os.path.join(self.package_folder, "include", "sodium"),
             keep_path=False)

    def package_info(self):
        self.cpp_info.libs = ["sodium"]
        self.cpp_info.includedirs = ["include"]

    def _machine(self, arch):
        return {"armv8": "aarch64"}.get(str(arch), str(arch))
