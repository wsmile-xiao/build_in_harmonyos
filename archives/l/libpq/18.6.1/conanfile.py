#!/usr/bin/env python3
"""Conan recipe — libpq 18.6.1 (autotools) — PostgreSQL frontend client library.

OHOS 适配要点:
  1. PG 18 源码包不含任何预生成的 parser/catalog 头（gram.c/gram.h/scan.c、
     pg_*_d.h、lwlocknames.h、kwlist_d.h 等）。configure 无 bison/flex 直接
     as_fn_error 失败；`make -C src/interfaces/libpq` 触发 submake-libpgport →
     submake-generated-headers（MAKELEVEL=0）→ src/backend generated-headers，
     需要 bison 生成 parser/gram.h、perl 生成 catalog 头 / kwlist_d.h。
     → tool_requires bison+flex+perl（VirtualBuildEnv 注入 PATH），且必须在使用
     configure 时即生效：configure 会把 BISON/FLEX/PERL 绝对路径烤进
     src/Makefile.global（PERL='@PERL@'）。
  2. 与 18.1 一样在源码目录 in-source 原生构建：configure 后仅
     `make -C src/interfaces/libpq`（自动 submake src/port + src/common），
     install 同法 DESTDIR 打包，产物 libpq.so.5.18 + libpq.a。
  3. 零补丁：config.guess 猜不出 HarmonyOS → 显式 --build=$(cc -dumpmachine)
     （PG config.sub 接受 aarch64-linux-ohos，configure 按 linux* 落入
     PORTNAME=linux）；Autoconf 私有 `umask 077` 与 HMDFS setgid 目录语义冲突
     → 程序化放松为 022（E129，libpng 同款；PG configure 内恰好 2 处）。
  4. libpq-fe.h #include "postgres_ext.h"，但 libpq 子目录 install 只装
     libpq-fe.h/libpq-events.h，postgres_ext.h 在 src/include/ 不随装
     （pg_config_ext.h 已在 18.x 移除）→ 手动拷入 include/。
  5. HMDFS 不跟随 .so 软链 → 安装后把 libpq.so / libpq.so.5 解引用为真实副本。

18.6.1 相对 18.6 的修订（同一份 postgresql-18.6.tar.gz，libpq.so.5.18 逐字节同源）：
  6. 补 bin/pg_config：psycopg2 / psycopg-c(psycopg-binary) / asterisk 等消费方在
     构建期先跑 `pg_config --includedir/--libdir/--version` 定位 libpq，18.6 包
     没有它 → `pg_config executable not found`，编译第一步就停（asterisk-pgsql
     甚至为此在自己配方里造了个 shell shim）。pg_config 按自身所在 bin/ 反推
     prefix（src/port/path.c make_relative_path），--prefix=/ 打出来的包放到任何
     前缀下都能答出正确的 include/lib 路径，无需改源码。
  7. 补齐「客户端头闭包」（对齐 src/include/Makefile install 的前两段，即
     Debian libpq-dev 的头集合）：pg_config.h / pg_config_os.h /
     pg_config_manual.h / libpq/libpq-fs.h 进 include/，c.h / port.h /
     postgres_fe.h / libpq/pqcomm.h / libpq/protocol.h 进
     include/postgresql/internal/。18.6 只装 libpq 子目录自己的 3+3 个头，
     psycopg2 的 psycopg.h `#include <pg_config.h>`、lobject.h
     `#include <libpq/libpq-fs.h>` 与 psycopg_c 的 `#include "pg_config.h"`
     在 18.6 下全部找不到。
"""

import os
import shlex
import shutil
import subprocess
from pathlib import Path

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.env import Environment, VirtualBuildEnv
from conan.tools.files import copy, get
from conan.tools.gnu import AutotoolsDeps, AutotoolsToolchain
from conan.tools.layout import basic_layout


class LibpqConan(ConanFile):
    name = "libpq"
    version = "18.6.1"
    description = "PostgreSQL client library (libpq frontend C API)"
    license = "PostgreSQL"
    homepage = "https://www.postgresql.org/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "library"

    # package_type="library" 必须显式声明 shared 选项（conan create 硬校验：
    # "Package type is 'library', but no 'shared' option declared"）。
    # PG libpq Makefile 默认同产 .so 与 .a，两种取值都交付同一产物。
    options = {"shared": [True, False]}
    default_options = {"shared": True}

    settings = "os", "arch", "compiler", "build_type"

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"libpq/18.6.1 is only supported on Linux/OHOS, not {self.settings.os}"
            )

    def build_requirements(self):
        # PG 18 强制要求 bison/flex 在 configure PATH；make 期 generated-headers
        # 需 perl（genbki.pl/gen_keywordlist.pl）。全部用精确版本（L0i）。
        self.tool_requires("bison/3.8.2")
        self.tool_requires("flex/2.6.4")
        self.tool_requires("perl/5.42.2")

    def layout(self):
        basic_layout(self, src_folder=".")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        AutotoolsDeps(self).generate()
        # 把 tool_requires(bison/flex/perl) 的 bin/lib 注入 conanbuild PATH。
        VirtualBuildEnv(self).generate()
        self._autotools_toolchain().generate()

    def build(self):
        environment = self._build_environment()
        with environment.vars(self).apply():
            self._configure_with_posix_shell()
            self._run_with_posix_shell(
                "make -C src/interfaces/libpq -j1", cwd=self.source_folder
            )
            # pg_config 只依赖 src/port + src/common（上一步 submake 已建好），
            # 直链 hnp clang/lld → 链接器自签有效，install 阶段是纯拷贝不重链。
            self._run_with_posix_shell(
                "make -C src/bin/pg_config -j1", cwd=self.source_folder
            )

    def package(self):
        environment = self._build_environment()
        with environment.vars(self).apply():
            destination = shlex.quote(self.package_folder)
            self._run_with_posix_shell(
                f"make -C src/interfaces/libpq -j1 install DESTDIR={destination}",
                cwd=self.source_folder,
            )
            self._run_with_posix_shell(
                f"make -C src/bin/pg_config -j1 install DESTDIR={destination}",
                cwd=self.source_folder,
            )
        self._materialize_shared_library()
        self._install_client_headers()
        self._check_pg_config_installed()
        copy(
            self,
            "COPYRIGHT",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
            keep_path=False,
        )

    def package_info(self):
        self.cpp_info.libs = ["pq"]
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.set_property("pkg_config_name", "libpq")

    def _autotools_toolchain(self):
        # AutotoolsToolchain 默认 prefix="/" → configure_args 含 --prefix=/；
        # 配合 make install DESTDIR=<package_folder> 产物直达 package/lib 与
        # package/include。readline/zlib/icu 为默认会自动探测的项，显式关掉。
        tc = AutotoolsToolchain(self)
        tc.configure_args.extend(
            [
                "--without-readline",
                "--without-zlib",
                "--without-icu",
                "--disable-nls",
                "--disable-rpath",
            ]
        )
        return tc

    def _build_environment(self):
        temporary = Path(self.build_folder, ".tmp")
        temporary.mkdir(parents=True, exist_ok=True)
        environment = Environment()
        environment.define_path("TMPDIR", str(temporary))
        mkdir = shutil.which("mkdir")
        if mkdir:
            environment.define("MKDIR_P", f"{mkdir} -p")
        return environment

    def _configure_with_posix_shell(self):
        shell = self._posix_shell()
        compiler = self._c_compiler()
        triplet = subprocess.check_output(
            [compiler, "-dumpmachine"], text=True
        ).strip()
        if not triplet:
            raise ConanInvalidConfiguration(
                "C compiler returned an empty target triplet"
            )
        configure = Path(self.source_folder, "configure")
        if not configure.is_file():
            raise ConanInvalidConfiguration(
                "required upstream configure script is missing"
            )
        self._relax_private_umask(configure)
        arguments = self._autotools_toolchain().configure_args + [
            f"--build={triplet}"
        ]
        quoted_arguments = " ".join(
            shlex.quote(argument) for argument in arguments
        )
        self._run_with_posix_shell(
            f"{shlex.quote(shell)} ./configure {quoted_arguments}",
            cwd=self.source_folder,
        )

    def _run_with_posix_shell(self, command, cwd=None):
        shell = shlex.quote(self._posix_shell())
        prefix = f"export SHELL={shell} CONFIG_SHELL={shell}; "
        self.run(prefix + command, cwd=cwd or self.build_folder, env="conanbuild")

    def _posix_shell(self):
        shell = (
            "/system/bin/sh" if os.path.isfile("/system/bin/sh") else shutil.which("sh")
        )
        if not shell:
            raise ConanInvalidConfiguration("No POSIX shell is available")
        return shell

    def _c_compiler(self):
        executables = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        )
        compiler = executables.get("c") or shutil.which("cc")
        if not compiler:
            raise ConanInvalidConfiguration("No C compiler is configured")
        return compiler

    def _materialize_shared_library(self):
        """HMDFS 不跟随 .so 软链 → 把 libpq.so.5 / libpq.so 解引用为真实副本。"""
        libdir = Path(self.package_folder, "lib")
        real_libraries = sorted(libdir.glob("libpq.so.5.*"))
        if not real_libraries:
            raise ConanException(
                "installed shared library libpq.so.5.* is missing in the package"
            )
        real = real_libraries[0]
        if real.name.startswith("libpq.so.5."):
            for name in ("libpq.so.5", "libpq.so"):
                alias = Path(libdir, name)
                if alias.is_symlink():
                    alias.unlink()
                if not alias.exists():
                    shutil.copy2(real, alias)

    # src/include/Makefile `install` 的前两段（客户端公共头 + 接口内部头）。
    # libpq 子目录的 install 只装它自己目录下的头，这些都不随装；
    # 不跑整个 src/include install 是为了不把几百个服务端头（include/postgresql/server）
    # 也拖进一个客户端库包。pg_config.h / pg_config_os.h 是 configure 生成物，
    # 其余是源码树自带。
    _CLIENT_HEADERS = (
        "postgres_ext.h",
        "libpq/libpq-fs.h",
        "pg_config.h",
        "pg_config_os.h",
        "pg_config_manual.h",
    )
    _INTERNAL_HEADERS = (
        "c.h",
        "port.h",
        "postgres_fe.h",
        "libpq/pqcomm.h",
        "libpq/protocol.h",
    )

    def _install_client_headers(self):
        include_src = Path(self.source_folder, "src", "include")
        include_dst = Path(self.package_folder, "include")
        # 内部头与 libpq 自己 install 的 libpq-int.h 同目录（$(pkgincludedir)/internal，
        # --prefix=/ 下是 include/postgresql/internal）；从落盘位置反推而不是写死，
        # 两处才不会漂。
        installed_internal = sorted(include_dst.rglob("libpq-int.h"))
        if not installed_internal:
            raise ConanException(
                "libpq install did not place libpq-int.h under include/"
            )
        internal_dst = installed_internal[0].parent
        for relative, destination in (
            *((name, include_dst) for name in self._CLIENT_HEADERS),
            *((name, internal_dst) for name in self._INTERNAL_HEADERS),
        ):
            header = Path(include_src, relative)
            if not header.is_file():
                raise ConanException(
                    f"required upstream header src/include/{relative} is missing"
                )
            target = Path(destination, relative)
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(header, target)

    def _check_pg_config_installed(self):
        pg_config = Path(self.package_folder, "bin", "pg_config")
        if not pg_config.is_file():
            raise ConanException("bin/pg_config was not installed into the package")
        with open(pg_config, "rb") as handle:
            magic = handle.read(4)
        if magic != b"\x7fELF":
            raise ConanException("bin/pg_config is not an ELF executable")

    @staticmethod
    def _relax_private_umask(configure):
        # in-source 构建直接改源码树里的 configure；已放松过的源码再进入
        # 时 077 计数为 0，视为幂等直接返回。
        path = Path(configure)
        content = path.read_text(encoding="utf-8", errors="surrogateescape")
        count = content.count("umask 077")
        if count == 0:
            return
        if count != 2:
            raise ConanInvalidConfiguration(
                "unexpected number of private umask commands in configure"
            )
        content = content.replace("umask 077", "umask 022")
        path.write_text(content, encoding="utf-8", errors="surrogateescape")
