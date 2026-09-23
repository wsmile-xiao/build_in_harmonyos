#!/usr/bin/env python3
"""Conan recipe - gtypist 2.10.1 (Autotools: configure + make).

GNU Typist: ncurses-based typing tutor (universal + touch typing lessons).
Installs the `gtypist`/`gtypist.cur` binaries plus lesson files (.typ).

Terminal library: ncursesw is a hard configure requirement
(AC_CHECK_LIB(ncursesw, add_wch) errors out when missing) - provided by
conan ncurses/6.6 (bare ref; the CI artifact repo publishes without
@user/channel). gettext: AM_GNU_GETTEXT(external) with prebuilt .gmo
shipped; NLS is disabled (--disable-nls) because the OHOS target has no
libintl and the English lessons do not require message catalogs.

Patches (conandata.yml):
  0001-config.guess.patch  - HarmonyOS branch in 2018 config.guess, in the
                              per-branch echo/exit style this vintage uses
                              (patch-autotools-ohos.pl emits GUESS= style
                              which only works after the 2021 refactor)
  0002-config.sub.patch    - aarch64 + linux-ohos recognition for the
                              case-style 2018-02 config.sub
  0003-configure-umask.patch - remove umask 077 temp-dir wrappers (E011/E114)
  0004-configure-clang.patch - default CC to clang (autoconf 2.69 does not
                              search for clang)
"""
import os
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import Autotools, AutotoolsToolchain, AutotoolsDeps
from conan.tools.layout import basic_layout


class GtypistConan(ConanFile):
    name = "gtypist"
    version = "2.10.1"
    description = "GNU Typist: ncurses-based typing tutor with international lessons"
    license = "GPL-3.0-or-later"
    homepage = "https://www.gnu.org/software/gtypist/"
    url = ""  # CI fills this

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # W0 已核验：ohpcd 制品仓 ncurses/6.4/6.5/6.6 均已发布（conan download --only-recipe 实测）
        # CI 制品仓为裸 ref（无 @user/channel），勿写 @ohpcd/stable
        self.requires("ncurses/6.6")

    def validate(self):
        # R32: settings.os must check in ("Linux", "OHOS")
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "gtypist is only supported on Linux/OHOS, not " + str(self.settings.os))

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        # E490: 确保自动工具脚本保留可执行位
        for f in ("configure", "config.guess", "config.sub", "install-sh", "missing"):
            p = os.path.join(self.source_folder, f)
            if os.path.exists(p):
                os.chmod(p, 0o755)

    def generate(self):
        tc = AutotoolsToolchain(self)
        # 目标无 libintl，英文课程无需消息目录；gettext 探测在 musl 上不可用
        tc.configure_args.append("--disable-nls")
        # conan ncurses 包头文件为平铺布局（include/ncurses.h），而上游 configure
        # 在非 BSD 平台检测 ncursesw/ncurses.h、源码亦 #include <ncursesw/ncurses.h>。
        # 生成 compat-include/ncursesw/ 镜像层并前置 -I，令检测与编译命中。
        compat = os.path.join(self.build_folder, "compat-include")
        for dep in self.dependencies.host.values():
            if dep.ref.name == "ncurses":
                incdir = os.path.join(dep.package_folder, dep.cpp_info.includedirs[0])
                os.makedirs(os.path.join(compat, "ncursesw"), exist_ok=True)
                for f in os.listdir(incdir):
                    if f.endswith(".h"):
                        shutil.copy2(os.path.join(incdir, f),
                                     os.path.join(compat, "ncursesw", f))
                        shutil.copy2(os.path.join(incdir, f),
                                     os.path.join(compat, f))
                # build() 手动调用 configure（绕 CONFIG_SHELL 缺陷），不走
                # tc.configure_args；compat 目录通过实例属性交给 build() 拼入
                # 命令行 CPPFLAGS=（autoconf 标准传法，覆盖环境变量，因此
                # compat 目录需同时备平铺与 ncursesw/ 两套头镜像）
                self._compat_include = compat
                break
        tc.generate()
        # 将 ncursesw 的 -L/-l 注入 LDFLAGS/LIBS，供 AC_CHECK_LIB 与最终链接使用
        AutotoolsDeps(self).generate()

    def build(self):
        apply_conandata_patches(self)
        # HMDFS 下 conan 相对路径会触发 toybox sh 的 pwd 缺陷（E386 同族），
        # 与驱动 W3 一致使用绝对路径调用 configure/make
        src = self.source_folder.replace("\\", "/")
        prefix = self.package_folder.replace("\\", "/")
        # gettext 的 NLS 检查会建删 conftest.dir，--disable-nls 规避；
        # §12.38①: hnp bash 作 CONFIG_SHELL 在 HMDFS 构建目录 getcwd 必挂（autoconf re-exec 自身），
        # env -u CONFIG_SHELL SHELL=/bin/sh 显式路由；toybox 相对路径 pwd 缺陷用绝对路径规避
        compat = getattr(self, "_compat_include", None)
        cppflags = (" CPPFLAGS=-I" + compat) if compat else ""
        # ac_cv_header_libintl_h=no：目标无 libintl 实现，强制 _() 走 (msgid)
        # 透传分支（getopt.c 的 HAVE_LIBINTL_H 分支会引入 gettext 但链接期
        # 无实现，与 --disable-nls 语义一致）
        self.run('env -u CONFIG_SHELL SHELL=/bin/sh sh %s/configure --prefix="%s" --disable-nls ac_cv_header_libintl_h=no%s' % (src, prefix, cppflags))
        # doc/ 的 makeinfo/HTML 生成工具在 HMDFS 新建二进制执行限制族内
        # （gtypist.html Error 127，同 indent texinfo2man 教训）：MAKEINFO
        # 占位为 true（touch 语义），info/HTML 非交付物核心
        # src/ 的 gtypist.1 由 help2man（perl，worker 不存在）生成且仅当
        # 文件不存在时触发：预创建空 man 页占位即可跳过（man 页非交付物核心）
        import tempfile
        self.run('touch "%s/src/gtypist.1"' % self.build_folder.replace("\\", "/"))
        self.run('env -u CONFIG_SHELL SHELL=/bin/sh make -j1 MAKEINFO=true MAKEINFOHTML=true')
        self.run('env -u CONFIG_SHELL SHELL=/bin/sh make install MAKEINFO=true MAKEINFOHTML=true')

    def package(self):
        autotools = Autotools(self)
        # install 阶段同样占位 MAKEINFO：doc/.info 的 mtime 在打包复制后
        # 可能触发重生成，而 makeinfo 在目标环境不可用
        autotools.install(args=["MAKEINFO=true", "MAKEINFOHTML=true"])

    def package_info(self):
        # 终端工具包（gtypist / gtypist.cur + 课程数据），无库产物
        self.cpp_info.libs = []
        self.cpp_info.bindirs = ["bin"]
        self.runenv_info.prepend_path("PATH", os.path.join(self.package_folder, "bin"))
