#!/usr/bin/env python3
"""Conan recipe — tintin 2.02.61（TinTin++ MUD 客户端，GNU Autotools）.

TinTin++（tt++）是 GPLv3+ 的免费 MUD 客户端，支持 TELNET、PCRE2、UTF-8、
TLS（gnutls，可选）、VT100 与 TINTIN 脚本语言。构建系统：GNU Autoconf
（configure.in + Makefile.in，tarball 内含 autoconf 2.72 生成的 configure）。
平台：OHOS aarch64 / Linux。
依赖：zlib（MCCP 压缩，configure 硬性要求）、pcre2（正则，硬性要求）；
gnutls 为可选依赖且 configure 对其优雅降级（缺省不引入，闭包最小化）。

HMDFS 适配说明：profile 的 CONFIG_SHELL 指向的 bash 在 HMDFS 深路径下
getcwd 失败、/tmp 可能只读，因此 build() 不使用 Conan Autotools helper，
而是把源码复制到独立构建目录后用 /bin/sh 脚本完成 configure/make/
make install（configure 位于 src/ 子目录）。CC、CFLAGS、依赖 include/lib
路径全部从 conan conf 与依赖包推导，无硬编码。
"""

import os
import shutil
import subprocess
import tempfile

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.build import cross_building
from conan.tools.files import (
    apply_conandata_patches,
    export_conandata_patches,
    get,
)
from conan.tools.layout import basic_layout


class TintinConan(ConanFile):
    name = "tintin"
    version = "2.02.61"
    description = "TinTin++ (tt++), a free extensible MUD client with TINTIN scripting language"
    license = "GPL-3.0-or-later"
    homepage = "https://tintin.mudhalla.net/"
    package_type = "application"
    settings = "os", "arch", "compiler", "build_type"

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration("tintin supports POSIX platforms")

    def requirements(self):
        # run=True：zlib/pcre2 在 ohpcd 均为静态包，链接后 tt++ 无运行时
        # conan cache .so 依赖；显式声明避免 conan 推导 run=False 导致
        # 测试图跳过其二进制包
        self.requires(
            "zlib/1.3.2",
            transitive_headers=True,
            transitive_libs=True,
            run=True,
        )
        self.requires(
            "pcre2/10.45.1",
            transitive_headers=True,
            transitive_libs=True,
            run=True,
        )

    def export_sources(self):
        export_conandata_patches(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def layout(self):
        basic_layout(self)

    def _gnu_triplet(self):
        machine = {
            "armv8": "aarch64",
            "armv7": "arm",
            "x86_64": "x86_64",
            "x86": "i686",
        }.get(str(self.settings.arch), str(self.settings.arch))
        return f"{machine}-unknown-linux-ohos"

    def _cc(self):
        executables = self.conf.get(
            "tools.build:compiler_executables", check_type=dict
        )
        cc = executables.get("c") if executables else None
        if not cc:
            raise ConanException(
                "tools.build:compiler_executables must be set in the profile"
            )
        return cc

    def _dep_flags(self):
        # 复刻 AutotoolsDeps 提供的编译/链接搜索路径（均取自依赖包）。
        # 上游 configure 用 AC_CHECK_HEADERS/AC_CHECK_LIB 直接探测 zlib 与
        # pcre2，无需 pkg-config。
        inc_flags, lib_flags = [], []
        for dep in self.dependencies.values():
            for d in dep.cpp_info.includedirs:
                inc_flags.append(f"-I{os.path.join(dep.package_folder, d)}")
            for d in dep.cpp_info.libdirs:
                lib_flags.append(f"-L{os.path.join(dep.package_folder, d)}")
        return inc_flags, lib_flags

    def build(self):
        apply_conandata_patches(self)

        cc = self._cc()
        inc_flags, lib_flags = self._dep_flags()

        cflags = {
            "Release": "-O3",
            "Debug": "-g -O0",
            "RelWithDebInfo": "-O2 -g",
            "MinSizeRel": "-Os",
        }.get(str(self.settings.build_type), "")
        defines = "-DNDEBUG" if str(self.settings.build_type) == "Release" else ""
        # include 路径必须同时进 CFLAGS：Makefile 编译规则只使用
        # $(CFLAGS)（INCS=@MYINCLUDE@ 因 includedir 取默认值而为空），
        # CPPFLAGS 仅对 configure 的 conftest 生效
        cppflags = " ".join(inc_flags)
        if defines:
            cppflags = f"{defines} {cppflags}"

        # --bindir 等使用单引号保留 ${prefix} 字面值，由 Makefile 的
        # ${DESTDIR}@bindir@ 在 make install 时展开
        configure_args = [
            "./configure",
            "--prefix=/",
            "'--bindir=${prefix}/bin'",
            "'--sbindir=${prefix}/bin'",
            "'--libdir=${prefix}/lib'",
            "'--includedir=${prefix}/include'",
            "'--oldincludedir=${prefix}/include'",
        ]
        if str(self.settings.os) == "OHOS":
            if not cross_building(self):
                # 原生 OHOS 环境无法运行 config.guess（HMDFS 只读 tmp），
                # 显式给出三元组；tarball 自带 config.sub（2025-07-10）
                # 原生支持 linux-ohos，无需补丁
                triplet = self._gnu_triplet()
                configure_args += [f"--build={triplet}", f"--host={triplet}"]
            else:
                configure_args += [f"--host={self._gnu_triplet()}"]

        # 独立构建目录：TMPDIR 优先（HMDFS 深路径在 /bin/sh 下可用），
        # 未设置时退回 conan 构建目录（保证只读 /tmp 环境也能构建）
        build_dir = tempfile.mkdtemp(
            prefix="tintin-",
            dir=os.environ.get("TMPDIR") or self.build_folder,
        )
        shutil.copytree(
            self.source_folder, build_dir, symlinks=True, dirs_exist_ok=True
        )

        lines = [
            "#!/bin/sh",
            "set -e",
            # configure/Makefile 位于 src/ 子目录
            f'cd "{build_dir}/src"',
            f'export CC="{cc}"',
            # 避免 profile CONFIG_SHELL 指向的 bash 触发 HMDFS getcwd 缺陷
            'export CONFIG_SHELL="/bin/sh"',
            'export SHELL="/bin/sh"',
            f'export PATH="{os.path.dirname(cc)}:$PATH"',
            f'export CFLAGS="{cflags} {cppflags}"',
            f'export CPPFLAGS="{cppflags}"',
            f'export LDFLAGS="{" ".join(lib_flags)}"',
        ]
        lines.append(" ".join(configure_args))
        lines.append("make -j1")
        lines.append(f'make install DESTDIR="{self.package_folder}"')

        script = os.path.join(build_dir, "_build.sh")
        with open(script, "w", encoding="utf-8", newline="\n") as f:
            f.write("\n".join(lines) + "\n")
        os.chmod(script, 0o755)
        subprocess.check_call(["/bin/sh", script], cwd=build_dir)

    def package(self):
        # 构建脚本已完成 make install DESTDIR=package_folder
        pass

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.libs = []
        self.buildenv_info.append_path(
            "PATH", os.path.join(self.package_folder, "bin")
        )
        self.runenv_info.append_path(
            "PATH", os.path.join(self.package_folder, "bin")
        )
