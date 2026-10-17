#!/usr/bin/env python3
"""Conan recipe — bas55 2.0（ECMA-55 Minimal BASIC 解释器与编辑器）.

bas55 是 ECMA-55 Minimal BASIC 编程语言的实现，提供解释器与行号重排
编辑器。构建系统：GNU Autotools（tarball 内含 autoconf 2.69 生成的
configure；configure.ac 无 AC_CANONICAL_*，不依赖 config.guess/sub）。
平台：OHOS aarch64 / Linux。依赖：无第三方依赖（仅系统 libm；
readline/libedit 为可选编辑增强，默认不启用）。

HMDFS 适配说明：profile 的 CONFIG_SHELL 指向的 bash 在 HMDFS 深路径下
getcwd 失败、/tmp 可能只读，因此 build() 不使用 Conan Autotools helper，
而是把源码复制到独立构建目录后用 /bin/sh 脚本完成 configure/make/
make check/make install。CC、CFLAGS 全部从 conan conf 推导，无硬编码。
"""

import os
import shutil
import subprocess
import tempfile

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.files import (
    apply_conandata_patches,
    export_conandata_patches,
    get,
)
from conan.tools.layout import basic_layout


class Bas55Conan(ConanFile):
    name = "bas55"
    version = "2.0"
    description = "ECMA-55 Minimal BASIC interpreter and editor"
    license = "GPL-3.0-or-later"
    homepage = "https://jorgicor.niobe.org/bas55"
    package_type = "application"
    settings = "os", "arch", "compiler", "build_type"

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration("bas55 supports POSIX platforms")

    def export_sources(self):
        export_conandata_patches(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def layout(self):
        basic_layout(self)

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

    def build(self):
        apply_conandata_patches(self)
        cc = self._cc()
        cflags = {
            "Release": "-O3",
            "Debug": "-g -O0",
            "RelWithDebInfo": "-O2 -g",
            "MinSizeRel": "-Os",
        }.get(str(self.settings.build_type), "")
        defines = "-DNDEBUG" if str(self.settings.build_type) == "Release" else ""

        # 独立构建目录：TMPDIR 优先（HMDFS 深路径在 /bin/sh 下可用），
        # 未设置时退回 conan 构建目录（保证只读 /tmp 环境也能构建）。
        # mkdtemp 只建父目录，copytree 自建 src 子目录，避免 FileExistsError
        parent = tempfile.mkdtemp(
            prefix="bas55-",
            dir=os.environ.get("TMPDIR") or self.build_folder,
        )
        build_dir = os.path.join(parent, "src")
        shutil.copytree(self.source_folder, build_dir, symlinks=True)

        lines = [
            "#!/bin/sh",
            "set -e",
            f'cd "{build_dir}"',
            f'export CC="{cc}"',
            # CI worker（buildbot AppSpawn 沙箱）环境中 TMPDIR 指向受限
            # 目录时，clang/ld 创建临时文件会失败，导致 configure 的
            # conftest 链接失败（"C compiler cannot create executables"）。
            # 显式将 TMPDIR 设为刚创建的构建目录（必然可写可执行）。
            f'export TMPDIR="{build_dir}"',
            # 避免 profile CONFIG_SHELL 指向的 bash 触发 HMDFS getcwd 缺陷
            'export CONFIG_SHELL="/bin/sh"',
            'export SHELL="/bin/sh"',
            f'export PATH="{os.path.dirname(cc)}:$PATH"',
            f'export CFLAGS="{cflags} {defines}"',
        ]
        # configure.ac 无 AC_CANONICAL_*，无需 --build/--host 三元组
        lines.append("./configure --prefix=/")
        # configure 生成的 doc/copyright.texi 会触发 bas55.info 重建链
        # （stamp-vti -> version.texi -> bas55.info），而设备无
        # makeinfo/help2man（automake missing 返回 127，E 类坑）。
        # 用 touch 固定 mtime：bas55.info 必须最后 touch，否则 make
        # 按纳秒比较会判定 bas55.info 旧于 version.texi 而重建。
        lines.append(
            'touch doc/version.texi doc/stamp-vti doc/bas55.1 doc/bas55.info '
            '2>/dev/null || true'
        )
        lines.append("make -j1")
        # 上游测试：automake TESTS 205 个 .test 脚本全量执行，
        # 任一失败即中止（set -e），通过率由 CI 日志统计
        lines.append('make check || { echo "UPSTREAM_TESTS_FAILED"; exit 1; }')
        lines.append(
            'echo "UPSTREAM_TEST_RESULTS:"; '
            'grep -h ":test-result:" tests/*.trs 2>/dev/null | sort | uniq -c || true'
        )
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
