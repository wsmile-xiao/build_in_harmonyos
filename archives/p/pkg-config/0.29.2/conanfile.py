#!/usr/bin/env python3
"""Conan recipe — pkg-config 0.29.2 (autotools, HarmonyOS aarch64)

pkg-config 是编译期辅助工具：查询已安装库的 CFLAGS/LIBS。
以 tool_requires 消费，为 autotools 项目提供 PKG_CHECK_MODULES 能力。

OHOS 适配要点（见 manifest.yaml ohos_adaptation）：
  1. config.guess/config.sub 需识别 aarch64-unknown-linux-ohos（主目录 + 内嵌 glib 两份副本）
  2. configure 的 conftest 管道在 musl 下需 `| cat` 兜底
  3. configure 生成 config.status 时用 `umask 077` 建临时目录，HMDFS 下该权限（drwx--S---）
     不可写 → 改 022（补丁 0007/0008）
  4. 内嵌 glib 2.56.0 在 aarch64+clang 下 gatomic.c 触发 -Werror，追加 -Wno-error 抑制（补丁 0009）
"""
from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class PkgConfigConan(ConanFile):
    name = "pkg-config"
    version = "0.29.2"
    description = "Helper tool for querying library compile/link flags"
    license = "GPL-2.0-or-later"
    homepage = "https://gitlab.freedesktop.org/pkg-config/pkg-config"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "application"

    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        # pkg-config 自带一份内嵌 glib 2.56.0（vendor）。OHOS 环境无独立 glib-2.0.pc，
        # 必须显式启用内嵌副本，否则 configure 报：
        #   Either a previously installed pkg-config or "glib-2.0 >= 2.16" could not be found.
        tc.configure_args.append("--with-internal-glib")
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        autotools = Autotools(self)
        autotools.configure()
        # HMDFS 不支持 mkfifo，make 的 jobserver 机制会报
        #   jobserver mkfifo: ...: Operation not permitted
        # 单线程构建规避该问题（该 warning 本身不致命，但 -j1 更干净且可复现）。
        autotools.make(args=["-j1"])

    def package(self):
        autotools = Autotools(self)
        autotools.install()
        # 上游默认把 triplet 前缀的 wrapper 装成软链接，HMDFS 下软链接不可用，
        # pkg-config 的 Makefile 已改为脚本方式（见上游 install-exec-hook）。

    def package_info(self):
        # 纯命令行工具：无库、无头文件，产物在 bin/。
        # 作为 tool_requires 被消费时，conan 自动把 bindirs 挂上 PATH；
        # 另显式导出 PKG_CONFIG，便于 autotools 的 PKG_CHECK_MODULES 直接定位。
        import os
        self.cpp_info.libs = []
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = ["bin"]
        self.buildenv_info.define_path(
            "PKG_CONFIG", os.path.join(self.package_folder, "bin", "pkg-config")
        )
