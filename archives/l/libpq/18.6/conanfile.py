#!/usr/bin/env python3
"""Conan recipe for libpq 18.6 — PostgreSQL frontend client library.

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
    version = "18.6"
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
                f"libpq/18.6 is only supported on Linux/OHOS, not {self.settings.os}"
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

    def package(self):
        environment = self._build_environment()
        with environment.vars(self).apply():
            destination = shlex.quote(self.package_folder)
            self._run_with_posix_shell(
                f"make -C src/interfaces/libpq -j1 install DESTDIR={destination}",
                cwd=self.source_folder,
            )
        self._materialize_shared_library()
        self._install_postgres_ext_header()
        copy(
            self,
            "COPYRIGHT",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
            keep_path=False,
        )

    def package_info(self):
        self.cpp_info.libs = ["pq"]
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

    def _install_postgres_ext_header(self):
        header = Path(self.source_folder, "src", "include", "postgres_ext.h")
        if not header.is_file():
            raise ConanException(
                "required upstream header src/include/postgres_ext.h is missing"
            )
        copy(
            self,
            "postgres_ext.h",
            src=os.path.dirname(header),
            dst=os.path.join(self.package_folder, "include"),
            keep_path=False,
        )

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
