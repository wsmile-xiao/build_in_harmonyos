#!/usr/bin/env python3
"""Conan recipe for libkcapi 1.5.0 — Linux kernel crypto API user space interface.

Builds the library and command line applications via autotools.
Note: libkcapi requires kernel AF_ALG sockets at runtime; this recipe
verifies compilation and basic API linkage on OHOS.
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.env import VirtualBuildEnv
from conan.tools.layout import basic_layout


class LibkcapiConan(ConanFile):
    name = "libkcapi"
    version = "1.5.0"
    description = "Linux kernel crypto API user space interface library"
    license = "BSD-3-Clause"
    homepage = "https://github.com/smuellerDD/libkcapi"
    url = "https://github.com/smuellerDD/libkcapi"
    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}

    def config_options(self):
        if self.settings.os == "Windows":
            del self.options.fPIC

    def export_sources(self):
        export_conandata_patches(self)

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration("libkcapi is supported only on Linux/OHOS")

    def requirements(self):
        pass

    def build_requirements(self):
        # Github tag archive 不带 configure/aclocal.m4/Makefile.in，build() 必须自举。
        # /data/service/hnp/bin 只有 autoconf 家族，没有 automake/libtool，
        # 故作为 tool_requires 拉入（制品仓已发布，同 abiword-plugin-* 先例）。
        self.tool_requires("automake/1.18")
        self.tool_requires("libtool/2.5.4")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        tc.configure_args.extend([
            "--disable-werror",
            "--enable-kcapi-test",
            "--disable-kcapi-speed",
            "--enable-kcapi-hasher",
            "--enable-kcapi-rngapp",
            "--enable-kcapi-encapp",
            "--enable-kcapi-dgstapp",
        ])
        if str(self.settings.os) == "OHOS":
            tc.configure_args.extend([
                "--build=aarch64-unknown-linux-gnu",
                "--host=aarch64-unknown-linux-gnu",
            ])
        tc.generate()

    def _bootstrap_autotools(self):
        """生成 configure/Makefile.in（tarball 不带，且 autoreconf 链在
        OHOS HMDFS 下有 autoconf.m4f 宏冲突先例，改用直跑链，同 abiword-plugin-*）。
        tool_requires(automake/libtool) 的 $ACLOCAL/$AUTOMAKE/$LIBTOOLIZE 只在
        conanbuild 环境生效且不注入 PATH，须用 self.run(env="conanbuild")。"""
        src = self.source_folder
        # aclocal 生成 aclocal.m4（上游 m4/ 宏加入 ACLOCAL_PATH）
        m4dir = os.path.join(src, "m4")
        self.run(
            f'ACLOCAL_PATH="{m4dir}:$ACLOCAL_PATH" "${{ACLOCAL:-aclocal}}" --force',
            cwd=src, env="conanbuild", ignore_errors=True,
        )
        # libtoolize（LT_INIT 需要）：先补 ltmain.sh 再 automake
        self.run('"${LIBTOOLIZE:-libtoolize}" --copy --force --install',
                 cwd=src, env="conanbuild", ignore_errors=True)
        # autoconf 生成 configure
        self.run("autoconf -o configure configure.ac",
                 cwd=src, env="conanbuild", ignore_errors=True)
        if not os.path.exists(os.path.join(src, "configure")):
            from conan.errors import ConanException
            raise ConanException("autoconf failed to generate configure")
        # HMDFS setgid 目录下 mktemp -d 恒 0700（不经 umask），config.status
        # 写 subs1.awk 被 EPERM（DRAFT-6507 cln 同型）：替换为唯一名 + umask 000。
        cfg = os.path.join(src, "configure")
        with open(cfg, encoding="utf-8") as f:
            txt = f.read()
        old_tmp = 'tmp=`(umask 077 && mktemp -d "./confXXXXXX") 2>/dev/null`'
        new_tmp = 'tmp=./conf$$-$RANDOM\n(umask 000 && mkdir "$tmp")\ntest -d "$tmp"'
        if old_tmp in txt:
            txt = txt.replace(old_tmp, new_tmp)
            with open(cfg, "w", encoding="utf-8") as f:
                f.write(txt)
            self.output.info("  [patched] configure: mktemp -d -> umask 000 mkdir")
        # automake 补 Makefile.in + aux 脚本
        self.run('"${AUTOMAKE:-automake}" --add-missing --copy --foreign',
                 cwd=src, env="conanbuild", ignore_errors=True)

    def build(self):
        apply_conandata_patches(self)
        self._bootstrap_autotools()
        autotools = Autotools(self)
        autotools.configure()
        autotools.make(args=["-j1"])

    def package(self):
        autotools = Autotools(self)
        autotools.install()
        import glob as _glob
        for _la in _glob.glob(os.path.join(self.package_folder, "lib", "*.la")):
            os.remove(_la)

    def package_info(self):
        self.cpp_info.libs = ["kcapi"]
        self.cpp_info.system_libs = ["m"]
        self.cpp_info.bindirs = ["bin"]
