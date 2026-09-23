#!/usr/bin/env python3
"""Conan recipe — cyrus-sasl-sql 2.1.28 (Autotools).

SQL auxprop package for Cyrus SASL on HarmonyOS PC (aarch64).

Same upstream 2.1.28 release tarball as cyrus-sasl, configured with the
SQL auxiliary-property plugin enabled against SQLite3:

    --enable-sql --with-sqlite3=<sqlite3 conan package>

Unlike the mechanism packages in this family (cyrus-sasl-login,
cyrus-sasl-gs2, ...), SQL is an *auxprop* plugin, not an authentication
mechanism: it backs `auxprop_plugin: sql` so a server can look users up
in a database instead of the sasldb file.

Static linking is available upstream (unlike GS2): configure.ac defines
STATIC_SQL when both --enable-sql and --enable-static are given, and
lib/staticopen.h already registers SPECIFIC_AUXPROP_PLUG_INIT(sql,
"SQL"), so the plugin ships inside libsasl2.a with no runtime plugin
search path (base package keeps --disable-staticdlopen).

OHOS notes (cyrus-sasl/2.1.28 + 2.1.28.1 precedent, CI-passed):
  - configure probes the *build* compiler through AC_PROG_CC_FOR_BUILD
    and bare-searches gcc/cc, but OHOS ships only clang, so feed
    CC_FOR_BUILD/CPP_FOR_BUILD explicitly (native build, build == host).
  - HMDFS temporary directories are not usable as autoconf scratch
    space: TMPDIR points inside the source tree and patch 0001 relaxes
    the generated configure's `umask 077` temp-dir creation.
  - lib/Makefile symlinks the static plugin sources into lib/ before
    compiling them; HMDFS does not serve those symlinks to the build,
    so patch 0002 turns the `ln -s` into `cp -pR` and the recipe also
    pre-copies plugins/sql.c into lib/.
  - OHOS has no coreutils `install`; the packaged config/install-sh is
    injected through MKDIR_P/INSTALL/INSTALL_PROGRAM/INSTALL_DATA.
  - SQLite3 is linked statically from the Conan package. configure's
    --with-sqlite3=PATH accepts a package root and probes
    <root>/lib/libsqlite3.a, which the sqlite3 recipe provides.
"""

import os
import shlex
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import apply_conandata_patches, copy, get
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class CyrusSaslSqlConan(ConanFile):
    name = "cyrus-sasl-sql"
    version = "2.1.28"
    description = ("Cyrus SASL SQL auxiliary property plugin "
                   "(libsasl2 with SQL/SQLite3 auxprop support)")
    license = "BSD-Attribution-HPND-disclaimer"
    homepage = "https://www.cyrusimap.org/sasl/"
    url = "https://github.com/cyrusimap/cyrus-sasl"
    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
    }
    default_options = {
        "shared": False,
        "fPIC": True,
    }
    exports_sources = "patches/*"

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def requirements(self):
        # Linked into the consumer: sql.o ships inside libsasl2.a and
        # references sqlite3_open, so consumers need -lsqlite3 as well.
        self.requires("sqlite3/3.53.4")

    def layout(self):
        basic_layout(self, src_folder=".")
        self.folders.build = "."

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        apply_conandata_patches(self)

    def generate(self):
        toolchain = AutotoolsToolchain(self)
        toolchain.configure_args.extend(self._configure_args())
        toolchain.generate()

    def build(self):
        if self.settings.os == "OHOS":
            self._build_ohos_tree(self.source_folder)
        else:
            autotools = Autotools(self)
            autotools.configure()
            autotools.make(args=["-j1"])

    def package(self):
        if self.settings.os == "OHOS":
            tmpdir = os.path.join(self.source_folder, "tmp")
            os.makedirs(tmpdir, exist_ok=True)
            install_sh = self._copy_install_sh_for_ohos(self.source_folder,
                                                       tmpdir)
            self.run(
                f'TMPDIR="{tmpdir}" make install '
                f'DESTDIR="{self.package_folder}" -j1 '
                f'{self._ohos_make_vars(install_sh)}'
            )
        else:
            Autotools(self).install()
        copy(self, "COPYING", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.libs = ["sasl2"]
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.set_property("cmake_file_name", "cyrus-sasl-sql")
        self.cpp_info.set_property("cmake_target_name",
                                   "cyrus-sasl-sql::cyrus-sasl-sql")
        self.cpp_info.set_property("pkg_config_name", "libsasl2")
        self.runenv_info.prepend_path(
            "LD_LIBRARY_PATH", os.path.join(self.package_folder, "lib")
        )
        # 插件搜索路径：--with-staticsasl 会强制 enable_shared=yes
        # （configure.ac:104-107），因此包内同时有 libsasl2.so 与 libsasl2.a。
        # 消费者默认链接到的 .so 是用 DO_DLOPEN 构建的 —— 它的
        # _sasl_static_plugins 静态注册表**不存在**（实测 .so 中该符号为 0，
        # 而 .a 中为 1），插件只能经 dlopen 从搜索路径加载。
        # 不设 SASL_PATH 时 auxprop 列表为空，连 auxprop_plugin="sql" 都解析
        # 不到（CI 实测：正向断言失败、阴性对照"通过"，即列表整体为空）。
        # 故按编译期 plugin dir（<prefix>/lib/sasl2）导出 SASL_PATH。
        self.runenv_info.append_path(
            "SASL_PATH", os.path.join(self.package_folder, "lib", "sasl2")
        )
        if self.settings.os in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["pthread", "dl", "m"]

    # ------------------------------------------------------------------
    # helpers
    # ------------------------------------------------------------------

    def _build_cc_for_ohos(self):
        executables = self.conf.get("tools.build:compiler_executables",
                                    default={})
        return executables.get("c") or executables.get("cc") or "clang"

    def _sqlite3_prefix(self):
        return self.dependencies["sqlite3"].package_folder

    def _configure_args(self):
        args = []
        if self.settings.os == "OHOS":
            args.extend([
                "--build=aarch64-unknown-linux-gnu",
                "--host=aarch64-unknown-linux-gnu",
            ])
        if self.options.shared:
            args.extend(["--enable-shared", "--disable-static"])
        else:
            args.extend(["--disable-shared", "--enable-static",
                         "--with-staticsasl"])
        # SQL on, every other backend off. configure requires at least
        # one of mysql/pgsql/sqlite/sqlite3 when --enable-sql is given;
        # SQLite3 is the only one that needs no running server.
        args.extend([
            "--enable-sql",
            f"--with-sqlite3={self._sqlite3_prefix()}",
            "--without-mysql",
            "--without-pgsql",
            "--without-sqlite",
            "--disable-auth-sasldb",
            "--with-dblib=none",
            "--without-saslauthd",
            "--prefix=/",
            "--disable-dependency-tracking",
            "--disable-sample",
            "--disable-staticdlopen",
            "--disable-alwaystrue",
            "--disable-gssapi",
            "--disable-httpform",
            "--disable-krb4",
            "--disable-ldapdb",
            "--disable-login",
            "--disable-ntlm",
            "--disable-otp",
            "--disable-passdss",
            "--disable-sia",
            "--disable-srp",
            "--disable-srp-setpass",
            "--without-authdaemond",
            "--without-des",
            "--without-gdbm",
            "--without-ldap",
            "--without-openssl",
            "--without-opie",
            "--without-pam",
            "--without-pwcheck",
        ])
        return args

    def _build_ohos_tree(self, source_folder):
        configure = os.path.join(source_folder, "configure")
        tmpdir = os.path.join(source_folder, "tmp")
        os.makedirs(tmpdir, exist_ok=True)
        build_cc = self._build_cc_for_ohos()
        configure_args = " ".join(
            shlex.quote(arg) for arg in self._configure_args()
        )
        command = (
            f'TMPDIR="{tmpdir}" CONFIG_SHELL=/system/bin/sh '
            f'SHELL=/system/bin/sh '
            f'CC_FOR_BUILD="{build_cc}" CPP_FOR_BUILD="{build_cc} -E" '
            f'/system/bin/sh "{configure}" {configure_args}'
        )
        self.run(command, cwd=source_folder)

        self._copy_linksrcs_for_ohos(source_folder)
        install_sh = self._copy_install_sh_for_ohos(source_folder, tmpdir)
        self.run(
            f'TMPDIR="{tmpdir}" make -j1 {self._ohos_make_vars(install_sh)}',
            cwd=source_folder,
        )

    def _ohos_make_vars(self, install_sh):
        return (
            f'MKDIR_P="/system/bin/sh {install_sh} -c -d" '
            f'INSTALL="/system/bin/sh {install_sh} -c" '
            f'INSTALL_PROGRAM="/system/bin/sh {install_sh} -c" '
            f'INSTALL_DATA="/system/bin/sh {install_sh} -c -m 644"'
        )

    def _copy_install_sh_for_ohos(self, source_folder, tmpdir):
        source = os.path.join(source_folder, "config", "install-sh")
        destination = os.path.join(tmpdir, "install-sh")
        shutil.copy2(source, destination)
        os.chmod(destination, 0o755)
        return destination

    def _copy_linksrcs_for_ohos(self, source_folder):
        # lib/Makefile.am compiles $(SASL_STATIC_SRCS) after symlinking
        # them into lib/; HMDFS does not serve those symlinks, so copy
        # the sources the same way the cyrus-sasl/2.1.28.1 recipe does.
        links = {
            "plugins/cram.c": "lib/cram.c",
            "plugins/digestmd5.c": "lib/digestmd5.c",
            "plugins/plain.c": "lib/plain.c",
            "plugins/anonymous.c": "lib/anonymous.c",
            # SQL auxprop plugin (STATIC_SQL -> SASL_STATIC_SRCS sql.c)
            "plugins/sql.c": "lib/sql.c",
            "sasldb/db_none.c": "lib/db_none.c",
        }
        for source, target in links.items():
            src_path = os.path.join(source_folder, source)
            if not os.path.isfile(src_path):
                raise ConanInvalidConfiguration(
                    f"expected upstream source missing: {source}"
                )
            shutil.copy2(src_path, os.path.join(source_folder, target))
