#!/usr/bin/env python3
"""Conan recipe — pinentry 1.3.3 (autotools, command-line tool).

pinentry = GnuPG 的 PIN/passphrase 输入对话框集合。本配方构建
**pinentry-curses** 与 **pinentry-tty** 两个前端（GUI/Qt 系列全部关闭）。

OHOS 适配要点（承接 main 上 1.3.2 的已验证方案）：
- config.guess / config.sub 的 HarmonyOS patch（1.3.3 上游仍不含 ohos；
  实测 1.3.2 的 2 个 patch **可干净套用到 1.3.3**）。
- **依赖版本无抬升**：1.3.3 只要求 `NEED_GPG_ERROR_VERSION=1.16`
  （实测 configure.ac:239）与 `NEED_LIBASSUAN_VERSION=2.1.0`（:256）
  → ohpcd 现存的 libgpg-error/1.55、libassuan/3.0.2 均满足。
- `/bin/sh` 不可用：config 脚本（gpgrt-config / libassuan-config）的 shebang 需改为
  `/data/service/hnp/bin/bash`；并设 `CONFIG_SHELL`/`SHELL`。
- libgpg-error 1.56+ 只剩 `gpgrt-config`（无 gpg-error-config）→ 显式导出
  `GPGRT_CONFIG` 与 `LIBASSUAN_CONFIG`，并把依赖 bin 前置到 PATH。
- `TMPDIR` 指向 build 目录；`configure` 内 `umask 077` → `022`（HMDFS 权限问题）。
"""
import os

from conan import ConanFile
from conan.tools.env import Environment
from conan.tools.files import (apply_conandata_patches, export_conandata_patches,
                               get, replace_in_file)
from conan.tools.gnu import Autotools, AutotoolsDeps, AutotoolsToolchain, PkgConfigDeps
from conan.tools.layout import basic_layout

BASH = "/data/service/hnp/bin/bash"


class PinentryConan(ConanFile):
    name = "pinentry"
    version = "1.3.3"
    description = ("GnuPG PIN entry dialog for entering passwords and other "
                   "sensitive data")
    license = "GPL-2.0-or-later"
    homepage = "https://gnupg.org/related_software/pinentry/index.html"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "application"

    settings = "os", "arch", "compiler", "build_type"

    def export_sources(self):
        # patches/ 必须显式导出，否则 apply_conandata_patches 找不到文件
        export_conandata_patches(self)

    def requirements(self):
        # 1.3.3 仅要求 libgpg-error >= 1.16、libassuan >= 2.1.0（实测 configure.ac）
        self.requires("libgpg-error/1.55")
        self.requires("libassuan/3.0.2")
        self.requires("ncurses/6.6")

    def layout(self):
        basic_layout(self, src_folder=".")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        AutotoolsDeps(self).generate()
        PkgConfigDeps(self).generate()
        tc = AutotoolsToolchain(self)
        tc.configure_args.extend([
            "--enable-pinentry-curses",
            "--enable-pinentry-tty",
            "--disable-pinentry-efl",
            "--disable-pinentry-qt",
            "--disable-pinentry-qt4",
            "--disable-pinentry-qt5",
            "--disable-pinentry-tqt",
            "--disable-inside-emacs",
            "--disable-fallback-curses",
        ])
        tc.generate()

    def _fix_shebang(self, path):
        """OHOS 上 /bin/sh 不可用 → 把 config 脚本 shebang 改为可用的 bash。"""
        if not os.path.isfile(path):
            return
        with open(path, "r") as f:
            content = f.read()
        if content.startswith("#!/bin/sh"):
            with open(path, "w") as f:
                f.write(f"#!{BASH}\n")
                rest = content[len("#!/bin/sh"):]
                if rest.startswith("\n"):
                    rest = rest[1:]
                f.write(rest)

    def _build_environment(self):
        """构造构建环境：依赖 bin/PATH、config 脚本路径、TMPDIR、SHELL。"""
        gpg_error = self.dependencies["libgpg-error"]
        libassuan = self.dependencies["libassuan"]
        ncurses = self.dependencies["ncurses"]

        gpg_error_bin = os.path.join(gpg_error.package_folder, "bin")
        libassuan_bin = os.path.join(libassuan.package_folder, "bin")

        # 修正 config 脚本 shebang（OHOS /bin/sh 不可用）
        for script in ["gpgrt-config", "gpg-error-config"]:
            self._fix_shebang(os.path.join(gpg_error_bin, script))
        self._fix_shebang(os.path.join(libassuan_bin, "libassuan-config"))

        env = AutotoolsToolchain(self).environment()
        env.compose_env(AutotoolsDeps(self).vars())

        local_env = Environment()
        local_env.prepend_path("PATH", gpg_error_bin)
        local_env.prepend_path("PATH", libassuan_bin)
        local_env.prepend_path("LD_LIBRARY_PATH",
                               os.path.join(gpg_error.package_folder, "lib"))
        local_env.prepend_path("LD_LIBRARY_PATH",
                               os.path.join(libassuan.package_folder, "lib"))
        local_env.prepend_path("LD_LIBRARY_PATH",
                               os.path.join(ncurses.package_folder, "lib"))

        # libgpg-error 1.56+ 只剩 gpgrt-config（无 gpg-error-config）→ 显式给出
        gpgrt_config = os.path.join(gpg_error_bin, "gpgrt-config")
        if os.path.isfile(gpgrt_config):
            local_env.define("GPGRT_CONFIG", gpgrt_config)
        libassuan_config = os.path.join(libassuan_bin, "libassuan-config")
        if os.path.isfile(libassuan_config):
            local_env.define("LIBASSUAN_CONFIG", libassuan_config)

        tmpdir = os.path.join(self.build_folder, "tmp")
        os.makedirs(tmpdir, exist_ok=True)
        local_env.define("TMPDIR", tmpdir)
        local_env.define("CONFIG_SHELL", BASH)
        local_env.define("SHELL", BASH)

        env.compose_env(local_env)
        return env.vars(self)

    def build(self):
        apply_conandata_patches(self)
        # HMDFS 上 umask 077 会导致临时文件权限问题（R6：用 Conan API 而非手写 IO）
        replace_in_file(self, os.path.join(self.source_folder, "configure"),
                        "umask 077", "umask 022")
        with self._build_environment().apply():
            autotools = Autotools(self)
            autotools.configure()
            autotools.make(args=["-j4"])

    def package(self):
        with self._build_environment().apply():
            autotools = Autotools(self)
            autotools.install()

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
