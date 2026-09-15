#!/usr/bin/env python3
"""Conan recipe — libksba 1.8.1 (autotools, OHOS).

libksba = X.509 / CMS / S/MIME 证书与签名解析库，GnuPG 组件之一
（gnupg 链：libgpg-error → libksba）。

OHOS 适配要点（承接 main 上 1.6.7.1 的已验证方案）：
- **显式 --build/--host=aarch64-unknown-linux-musl**：① 设备 HMDFS 上 config.guess
  的 mktemp 探针写 dummy.c 报 Permission denied（"unable to guess system type"）；
  ② 1.8.1 的 config.sub **仍不识别 `linux-ohos`**（实测 `Invalid configuration`），
  但**自带 linux-musl 分支**（实测 `config.sub aarch64-unknown-linux-musl` 通过）
  → 用 musl triplet 显式指定即可，无需 patch config.sub。
  `build == host` → 原生模式（与 libgpg-error 的 lock-obj 尺寸逻辑一致）。
- **libgpg-error 1.55 足够**：1.8.1 只要求 `NEED_GPG_ERROR_VERSION=1.28`
  （实测 configure.ac:61），**低于** ohpcd 现存的 1.55 → 不依赖 1.61。
- **gpgrt-config 而非 gpg-error-config**：libgpg-error 1.56+ 已移除
  `gpg-error-config`，只剩 `gpgrt-config`。gpg-error.m4 用 AC_PATH_PROG 在 PATH 上找，
  故须把 libgpg-error 的 bin 加入 PATH；`--with-libgpg-error-prefix` 按约定拼出的
  `$prefix/bin/gpg-error-config` 不存在。
- **CPPFLAGS/LDFLAGS 兜底**：`gpgrt-config --cflags` 为空（includedir 按烤死的 `/`
  算成标准路径）→ 编译找不到 `gpg-error.h`；直接经 CPPFLAGS/LDFLAGS 补
  libgpg-error 的 include/lib。
- `TMPDIR` 指向 build 目录；`configure` 内 `umask 077` → `022`（HMDFS 上权限异常）。
- 上游测试：`make check` 实跑（7 个测试二进制，sample 数据随源码分发）。
"""
import glob
import os

from conan import ConanFile
from conan.tools.files import (apply_conandata_patches, collect_libs, get)
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class LibksbaConan(ConanFile):
    name = "libksba"
    version = "1.8.1"
    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": True, "fPIC": True}

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def requirements(self):
        # 1.8.1 只要求 NEED_GPG_ERROR_VERSION=1.28（实测 configure.ac:61）→ 1.55 足够
        self.requires("libgpg-error/1.55")

    def layout(self):
        basic_layout(self, src_folder=".")

    def generate(self):
        tc = AutotoolsToolchain(self)
        # config.sub 不识别 linux-ohos，但自带 linux-musl 分支 → 用 musl triplet 显式指定，
        # 同时跳过 config.guess（HMDFS 探针失败）。build==host → 原生模式。
        tc.configure_args.append("--build=aarch64-unknown-linux-musl")
        tc.configure_args.append("--host=aarch64-unknown-linux-musl")
        tc.configure_args.append("--disable-doc")
        # 只出共享库（test_package 走 dlopen 探针）
        tc.configure_args.append("--disable-static")
        tc.configure_args.append(
            "--with-libgpg-error-prefix={}".format(
                self.dependencies["libgpg-error"].package_folder))
        tc.generate()

    def build(self):
        apply_conandata_patches(self)

        # TMPDIR 指向可写的 build 目录（HMDFS 上 conftest/config.guess 写 dummy.c 失败）
        _tmp = os.path.join(self.build_folder, "_tmp")
        os.makedirs(_tmp, exist_ok=True)
        os.environ["TMPDIR"] = _tmp

        # libgpg-error 1.56+ 已移除 gpg-error-config，只剩 gpgrt-config；gpg-error.m4 用
        # AC_PATH_PROG 在 PATH 上找它，故把 bin 加进 PATH。
        _gpgerr = self.dependencies["libgpg-error"].package_folder
        os.environ["PATH"] = (os.path.join(_gpgerr, "bin") + os.pathsep
                              + os.environ.get("PATH", ""))

        # gpgrt-config --cflags 为空（includedir 按烤死的 / 算）→ 编译找不到 gpg-error.h；
        # 直接补 include/lib（autoconf 会把它烤进 Makefile）。
        os.environ["CPPFLAGS"] = ("-I{} ".format(os.path.join(_gpgerr, "include"))
                                  + os.environ.get("CPPFLAGS", ""))
        os.environ["LDFLAGS"] = ("-L{} ".format(os.path.join(_gpgerr, "lib"))
                                 + os.environ.get("LDFLAGS", ""))

        # HMDFS 上 umask 077 建归档目录会产生 0600 成员，install 阶段可读性不稳 → 放宽为 022
        for _cfg in glob.glob(os.path.join(self.source_folder, "**", "configure"),
                              recursive=True):
            try:
                with open(_cfg, encoding="utf-8", errors="ignore") as f:
                    text = f.read()
            except OSError:
                continue
            if "umask 077" in text:
                with open(_cfg, "w", encoding="utf-8") as f:
                    f.write(text.replace("umask 077", "umask 022"))

        autotools = Autotools(self)
        autotools.configure()
        autotools.make(args=["-j1"])
        # 上游回归套件（rule4 须实跑）：7 个测试二进制在 make all 阶段已编好，
        # sample 数据随源码包分发。
        autotools.make(target="check", args=["-j1"])

    def package(self):
        autotools = Autotools(self)
        autotools.install()

    def package_info(self):
        explicit_libs = ["ksba"]
        self.cpp_info.libs = explicit_libs or collect_libs(self)
        self.cpp_info.set_property("cmake_file_name", "libksba")
        self.cpp_info.set_property("cmake_target_name", "libksba::libksba")
        self.cpp_info.set_property("pkg_config_name", "ksba")
