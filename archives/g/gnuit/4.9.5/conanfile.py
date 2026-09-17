#!/usr/bin/env python3
"""Conan recipe - gnuit 4.9.5 (Autotools: configure + make).

GNU Interactive Tools: terminal file manager / viewer / process tools
(binaries: gitfm gitps gitview gitwipe gitkeys gitwhich, plus git* scripts
and the `git` transition script).

Terminal capability library (tgetent/tputs in tty.c) is a hard configure
requirement: provided by conan ncurses/6.6 (bare ref - the CI artifact repo
publishes without @user/channel; @ohpcd/stable does not resolve).
readline is probed by configure but never referenced by any source file
(grep over src/*.c is empty), so it is explicitly disabled for
deterministic CI builds (--without-readline).

Patches (conandata.yml):
  0001-config.guess.patch   - HarmonyOS recognition in config.guess (E007)
  0002-config.sub.patch     - aarch64 + linux-ohos recognition in the 2008-era
                              config.sub (E007; perl script only covers 2018+ files)
  0003-configure-umask.patch - Remove umask 077 temp-dir wrappers (E011/E114 HMDFS)
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import Autotools, AutotoolsToolchain, AutotoolsDeps
from conan.tools.layout import basic_layout


class GnuitConan(ConanFile):
    name = "gnuit"
    version = "4.9.5"
    description = "GNU Interactive Tools: terminal file manager, viewer and process tools"
    license = "GPL-3.0-or-later"
    homepage = "https://www.gnu.org/software/gnuit/"
    url = ""  # CI fills this

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # W0 已核验：ohpcd 制品仓 ncurses/6.4 / 6.5 / 6.6 均已发布（conan download --only-recipe 实测）
        # CI 制品仓为裸 ref（无 @user/channel），勿写 @ohpcd/stable
        self.requires("ncurses/6.6")

    def validate(self):
        # R32: settings.os must check in ("Linux", "OHOS")
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "gnuit is only supported on Linux/OHOS, not " + str(self.settings.os))

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        # E490: 确保自动工具脚本保留可执行位（部分适配路径会丢失 mode）
        import os
        for f in ("configure", "config.guess", "config.sub", "install-sh", "missing"):
            p = os.path.join(self.source_folder, f)
            if os.path.exists(p):
                os.chmod(p, 0o755)

    def generate(self):
        tc = AutotoolsToolchain(self)
        # configure 探测 readline 但源码从未使用；显式关闭保证 CI 确定性
        tc.configure_args.append("--without-readline")
        tc.generate()
        # 将 ncurses 的 -L/-l 注入 LDFLAGS/LIBS，供 AC_CHECK_LIB(ncursesw, tgetent) 与最终链接使用
        AutotoolsDeps(self).generate()

    def build(self):
        apply_conandata_patches(self)
        autotools = Autotools(self)
        autotools.configure()
        autotools.make(args=["-j1"])

    def package(self):
        autotools = Autotools(self)
        autotools.install()

    def package_info(self):
        # 纯工具包（gitfm/gitps/gitview/gitwipe/gitkeys/gitwhich + git* 脚本），无库产物
        self.cpp_info.libs = []
        self.cpp_info.bindirs = ["bin"]
        # 让 test_package / 消费者通过 VirtualRunEnv 直接调用包内工具
        self.runenv_info.prepend_path("PATH", os.path.join(self.package_folder, "bin"))
