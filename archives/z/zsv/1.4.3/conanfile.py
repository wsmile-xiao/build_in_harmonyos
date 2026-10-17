#!/usr/bin/env python3
"""Conan recipe for zsv 1.4.3 — custom configure + Makefile project.

构建系统：zsv 使用自定义 configure 脚本（musl 风格）+ Makefile，
【不是】CMake、也不是 autotools 主项目：
  ./configure --prefix=...   # 生成 config.mk（自动检测 clang / NEON / 内置 pcre2、jq）
  make -j1                   # src/ 构建 libzsv.a，app/ 构建 CLI 工具
  make install DESTDIR=...   # 头文件 + libzsv.a + zsv 主二进制

嵌套依赖（app/external/*.tar.gz，make 时才解压构建）：
  - pcre2 / jq 的 config.guess 无法识别 HarmonyOS（E007 模式），且 umask 077
    在 HMDFS 上创建临时目录不可写 → patches/0001、0002 由 build() 先
    解压→打补丁→重新打包，再进入 make。
  - jq / pcre2 / sqlite3 均为 builtin 内部组件，不是 Conan 运行时依赖（不伪造）；
    libcurl 仅用于上游测试数据下载，不是库依赖。
"""
import os
import shutil
import tarfile

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.files import (get, copy, patch,
                               apply_conandata_patches, export_conandata_patches)
from conan.tools.layout import basic_layout


class ZsvConan(ConanFile):
    name = "zsv"
    version = "1.4.3"
    description = "zsv: World's fastest CSV parser (streaming CLI + C library)"
    license = "MIT"
    homepage = "https://github.com/liquidaty/zsv"
    url = "https://github.com/liquidaty/zsv"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        # 补丁随配方导出（export_sources_folder）。
        # 说明：conandata 不声明 patches——4 个补丁目标是【嵌套 tarball 内部】
        # 的 config.guess/config.sub，apply_conandata_patches() 无法应用到
        # 主源码树（目标文件在解压后不存在），由 build() 的
        # _patch_nested_tarball() 解压→打补丁→重打包后应用。
        export_conandata_patches(self)
        copy(self, "patches/*.patch", src=self.recipe_folder,
             dst=self.export_sources_folder)

    def requirements(self):
        pass

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"][str(self.version)], strip_root=True)

    def _patch_nested_tarball(self, tarball_rel, patch_rels):
        """OHOS: 嵌套 tarball（pcre2/jq）的 config.guess/config.sub 无法识别
        HarmonyOS triplet（E007 模式），且 config.guess 用 umask 077 创建临时
        目录在 HMDFS 不可写（E002/E011 模式）。
        解压 → 依次打补丁 → 重新打包覆盖原 tarball，供 zsv make 阶段直接使用。
        """
        tarball = os.path.join(self.source_folder, tarball_rel)
        if not os.path.exists(tarball):
            return
        tmp = os.path.join(self.build_folder, "nested_patch")
        shutil.rmtree(tmp, ignore_errors=True)
        os.makedirs(tmp, exist_ok=True)
        with tarfile.open(tarball, "r:gz") as tf:
            tf.extractall(tmp)
        for patch_rel in patch_rels:
            patch_file = os.path.join(self.export_sources_folder, patch_rel)
            # 使用 conan.tools.files.patch（纯 Python patch_ng 实现），
            # 不依赖系统 patch 命令（CI/OHOS 环境无该二进制 → FileNotFoundError）
            patch(self, base_path=tmp, patch_file=patch_file, strip=1)
        # E011: autoconf configure/config.status 用 umask 077 建临时目录（confXXXXXX），
        # OHOS HMDFS 上目录本身不可写 → 递归替换为 022 并恢复执行位（参照 tcl 方案）
        for root, _, files in os.walk(tmp):
            for _f in files:
                if _f in ("configure", "config.status", "config.guess", "config.sub"):
                    _p = os.path.join(root, _f)
                    try:
                        with open(_p, encoding="utf-8", errors="ignore") as _fh:
                            _text = _fh.read()
                    except OSError:
                        continue
                    if "umask 077" in _text:
                        with open(_p, "w", encoding="utf-8") as _fh:
                            _fh.write(_text.replace("umask 077", "umask 022"))
                        os.chmod(_p, 0o755)
        with tarfile.open(tarball, "w:gz") as tf:
            for name in os.listdir(tmp):
                tf.add(os.path.join(tmp, name), arcname=name)
        shutil.rmtree(tmp, ignore_errors=True)

    def build(self):
        # 主源码树补丁（conandata patches 无主树条目时为空操作；嵌套补丁见下）
        apply_conandata_patches(self)

        # R33: 编译器/工具从 Conan conf 获取，不裸读 shell 环境变量
        compiler_executables = self.conf.get("tools.build:compiler_executables",
                                             default={}, check_type=dict)
        cc = compiler_executables.get("c", "clang")
        ar = compiler_executables.get("ar", "llvm-ar")
        ranlib = compiler_executables.get("ranlib", "llvm-ranlib")

        # OHOS 缺失/异常系统命令 shim（E046 模式：chmod/chown 不生效）：
        # app/Makefile 解压 utf8proc 时执行 `chown -R $(whoami) ...`，
        # OHOS whoami 报 "bad uid"、chown 报 "Need 2 arguments" → 用 shim 兜底
        _shim = os.path.join(self.build_folder, "_cmd_shim")
        os.makedirs(_shim, exist_ok=True)
        with open(os.path.join(_shim, "whoami"), "w") as _f:
            _f.write('#!/bin/sh\necho root\n')
        with open(os.path.join(_shim, "chown"), "w") as _f:
            _f.write('#!/bin/sh\nexit 0\n')
        os.chmod(os.path.join(_shim, "whoami"), 0o755)
        os.chmod(os.path.join(_shim, "chown"), 0o755)
        try:
            _cur_path = self.conf.get("tools.build:env_path")
        except ConanException:
            _cur_path = os.environ.get("PATH", "")
        os.environ["PATH"] = _shim + os.pathsep + _cur_path

        # 嵌套依赖 config.guess/config.sub OHOS 兼容补丁
        self._patch_nested_tarball("app/external/pcre2-pcre2-10.47.tar.gz",
                                   ["patches/0001-pcre2-config-guess-ohos.patch",
                                    "patches/0003-pcre2-config-sub-ohos.patch"])
        self._patch_nested_tarball("app/external/jq-1.6.tar.gz",
                                   ["patches/0002-jq-config-guess-ohos.patch",
                                    "patches/0004-jq-config-sub-ohos.patch"])

        # staging prefix（可写路径；真实安装经 DESTDIR 进入 package_folder）
        stage = os.path.join(self.build_folder, "stage")
        config_shell = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        # umask 022: OHOS HMDFS 上默认 077 会让 configure 生成的临时目录不可写（E011 模式）
        # < /dev/null: CI worker 上 stdin 不可达，嵌套 autotools configure（jq/pcre2/sqlite3）
        # 在 zsh 父进程下做 fd 重定向（dup fd3→fd0）会报 Bad file descriptor 并挂起，
        # 重定向 stdin 到 /dev/null 规避（参照 aercbook 范式，CI #19917）
        # --disable-sheet: sheet 为可选交互式 TUI，依赖 ncurses 头文件中的 KEY_* 宏；
        # CI 环境的 curses 头文件不完整（缺 KEY_UP/KEY_RESIZE 等），编译 app/sheet/key-bindings.c
        # 会报 undeclared identifier。核心 CLI（version/count 等）不依赖 sheet，故禁用。
        self.run(f"umask 022 && {config_shell} ./configure --prefix={stage} "
                 f"--disable-sheet CC={cc} AR={ar} RANLIB={ranlib} < /dev/null",
                 cwd=self.source_folder)
        self.run("make -j1 < /dev/null", cwd=self.source_folder)

    def package(self):
        # make install DESTDIR: 头文件 + libzsv.a → package/include、package/lib，
        # bin/zsv → package/bin（zsv 顶层 Makefile 支持 DESTDIR staging）
        self.run(f"make install DESTDIR={self.package_folder} < /dev/null", cwd=self.source_folder)
        # libzsvutil.a 仅由 app/install-util-lib 生成（install 目标不含），生成后补拷
        stage = os.path.join(self.build_folder, "stage")
        self.run(f"make -C app install-util-lib CONFIGFILE={os.path.join(self.source_folder, 'config.mk')} < /dev/null",
                 cwd=self.source_folder)
        copy(self, "libzsvutil.a", os.path.join(stage, "lib"),
             os.path.join(self.package_folder, "lib"))

    def package_info(self):
        self.cpp_info.libs = ["zsv", "zsvutil"]
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.includedirs = ["include"]
