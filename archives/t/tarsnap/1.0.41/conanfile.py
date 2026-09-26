#!/usr/bin/env python3
"""Conan recipe for tarsnap 1.0.41 - secure online backup client tools.

Builds and installs the tarsnap client binaries (tarsnap, tarsnap-keygen,
tarsnap-keymgmt, tarsnap-keyregen, tarsnap-recrypt) plus man pages.

OHOS notes
----------
* The official autoconf tarball ships a generated ``configure``; no
  autoreconf needed.
* Device ``uname`` returns ``HarmonyOS`` so ``config.guess`` cannot identify
  the triplet -> pass ``--build=aarch64-unknown-linux-ohos`` explicitly.
* autoconf's generated ``configure``/``config.status`` create their scratch
  directory with ``umask 077 && mktemp -d``; on the OHOS shared filesystem
  (HMDFS, setgid parent) that yields an unwritable ``drwx--S---`` directory.
  Dropping ``umask 077`` fixes it (E114 / DRAFT-6507; same as tnef 1.4.18).
* E074: parallel make hits the HMDFS jobserver fifo EPERM -> ``make -j1``.
* Dependencies openssl + zlib come from Conan packages; include/lib dirs are
  injected into the autotools env via AutotoolsDeps (R33: no bare shell vars).
* Upstream tests run via the custom ``make test`` target
  (tests/test_tarsnap.sh); scenario 04 self-skips without a real
  TARSNAP_TEST_KEYFILE, the rest are offline (fake key + dry-run).
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import get
from conan.tools.gnu import AutotoolsDeps, AutotoolsToolchain
from conan.tools.layout import basic_layout

required_conan_version = ">=2.0"


def _drop_umask_077(path):
    """E114: HMDFS forces setgid on directories, so `umask 077 && mktemp -d`
    creates a drwx--S--- temp dir that is not writable.  Remove `umask 077`
    so configure/config.status can create their scratch directory."""
    with open(path, "r", encoding="utf-8") as handle:
        data = handle.read()
    data = data.replace("(umask 077 && mktemp -d", "(mktemp -d")
    data = data.replace('(umask 077 && mkdir "$tmp")', 'mkdir "$tmp"')
    with open(path, "w", encoding="utf-8") as handle:
        handle.write(data)


class TarsnapConan(ConanFile):
    name = "tarsnap"
    version = "1.0.41"
    description = "Tarsnap secure online backup client (tarsnap and key management tools)"
    license = "Tarsnap"  # 顶层 COPYING 为 Tarsnap 客户端专用许可，捆绑组件另有 BSD 等声明
    homepage = "https://www.tarsnap.com/"
    url = "https://www.tarsnap.com/download.html"

    package_type = "application"
    settings = "os", "compiler", "build_type", "arch"

    def validate(self):
        # R32: settings.os 判断必须同时接受 Linux 与 OHOS
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "tarsnap OHOS adaptation is validated on Linux/OHOS, not "
                + str(self.settings.os))

    def requirements(self):
        # W0: openssl 与 zlib 均已在制品仓发布（openssl/3.0.21、zlib/1.3.2），
        # MateBook 阶段用 conan download 复核二进制包（R35，禁用 conan list 判断）。
        self.requires("openssl/3.0.21")
        self.requires("zlib/1.3.2")
        # MateBook 实测新增：--build=*-*-linux-ohos 使 configure 的 $target_os
        # 命中 linux* 分支，m4/check_linux_ext2fs.m4 硬性检查 ext2fs/ext2_fs.h
        #（libarchive 的 archive_entry.c 等包含它读 Linux 文件标志）。
        # 头文件由已发布的 e2fsprogs/1.47.4 提供（conan download 复核过二进制）。
        self.requires("e2fsprogs/1.47.4")

    def layout(self):
        basic_layout(self)  # in-source 构建（上游测试脚本假定源码树内运行）

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        AutotoolsToolchain(self).generate()
        # 把 openssl/zlib 的 -I/-L/-l 注入 conanbuild 环境的 CPPFLAGS/LDFLAGS/LIBS
        AutotoolsDeps(self).generate()

    def _compiler(self, name, fallback):
        # R33: 编译器从 Conan conf 获取，禁止裸用 shell 环境变量
        executables = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict) or {}
        return executables.get(name) or fallback

    def build(self):
        src = self.source_folder
        cc = self._compiler("c", "clang")
        # E114（对官方 configure 的就地修正，与 tnef 1.4.18 同源知识）
        _drop_umask_077(os.path.join(src, "configure"))
        # config.guess 认不出 HarmonyOS，显式给三元组（tnef 先例）
        self.run('CC="{}" ./configure --build=aarch64-unknown-linux-ohos '
                 '--prefix="{}"'.format(cc, self.package_folder),
                 cwd=src, env="conanbuild")
        # E074: make -j1
        self.run("make -j1", cwd=src, env="conanbuild")
        # 上游官方测试（自定义 test 目标；无标准 check 目标）
        self.run("make test", cwd=src, env="conanbuild")

    def package(self):
        self.run("make install", cwd=self.source_folder, env="conanbuild")

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
