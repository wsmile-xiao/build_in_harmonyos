#!/usr/bin/env python3
"""Conan recipe — malint 0.2 (autotools, 官方 tarball 自带 configure)

malint 是 Dieter Baron 的 MPEG Audio 流校验器：解析 MPEG 音频流并报告
流信息与格式违规。产物为单二进制 bin/malint。

OHOS 适配要点（均在真机 shadow CI 实测验证）：
1. 官方 tarball 由 autoconf 2.59 生成，自带 configure/Makefile.in，
   无需 bootstrap；但不含 config.guess/config.sub —— 必须显式传
   --build/--host 三元组，避免 configure 内联 uname 猜测宿主类型
   在 OHOS 上失败（知识 E007 同类规避方式）。
2. HMDFS setgid 目录按组权限判定写入：autoconf 2.59 的 configure 以
   `umask 077` 创建 confstat 临时目录，config.status 报 Permission
   denied（知识 E011/E052/E129）—— 构建前将 configure 内的 `umask 077`
   字面替换为 `umask 022`（与 zzuf 0.15 相同方式），并以 umask 022
   运行全部构建命令（构建环境层，非上游源码补丁）。
3. 纯 C、无第三方依赖：musl libc 自带 strerror/getopt，configure 的
   LIBOBJS 替换（strerror.c/getopt.c/getopt1.c）不会启用。
4. 设备 shell 故障适配（真机实测）：/bin/sh 与 /data/service/hnp/bin/bash
   可能处于不可执行状态，此时可用 shell 为 HMDFS 上的 zsh：
   - shell 选择：CONFIG_SHELL 经 shutil.which 校验后回退 PATH 中
     bash/sh（CI job 环境 PATH 首位提供 bash 兼容入口）；
   - configure 以 `{shell} ./configure` 直接解释执行（绕开 `#!/bin/sh`
     shebang exec 被拒，E087）；
   - make 显式 `SHELL={shell}`，make check 显式 `TESTS_ENVIRONMENT=sh`
     （HMDFS 源文件无执行位，runtest 须经 sh 显式调用，E046/E087）。
5. 设备 /tmp 可能只读（E002）：TMPDIR 指向 build 目录下自建 tmp/
   （clang 临时文件与 zsh here-document 均需要）。
6. 上游 regress 测试（6 个 runtest 用例）在非交叉编译时通过
   `make check TESTS_ENVIRONMENT=sh` 集成进 build 阶段（真机 6/6 通过）。
"""

import os
import shutil

from conan import ConanFile

from conan.errors import ConanInvalidConfiguration
from conan.tools.build import cross_building
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.layout import basic_layout

# 源码 URL/SHA256 保留在配方内，不进入 CI 的 conandata 预下载分支
# （xmodem 适配经验：该分支引用未初始化 BUILD_DIR）。
_SOURCE_URL = "https://www.nih.at/malint/malint-0.2.tar.gz"
_SOURCE_SHA256 = "798a76d60df6c1c18c0b9d6661f1e320d515fa24517c69c538d6256e57f15ca2"

_TRIPLET = "aarch64-unknown-linux-gnu"


class MalintConan(ConanFile):
    name = "malint"
    version = "0.2"
    description = (
        "MPEG Audio stream validator: parses an MPEG audio stream and "
        "prints information about the stream and format violations"
    )
    license = "GPL-2.0-or-later"
    homepage = "https://www.nih.at/malint/"
    url = "https://www.nih.at/malint/"
    package_type = "application"

    settings = "os", "arch", "compiler", "build_type"

    def export_sources(self):
        # 无补丁时 export_conandata_patches 为 no-op（G1 要求结构完整）
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)
        # autotools 就地构建（tarball 自带 configure，in-source 同 zzuf 惯例）
        self.folders.build = "."

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration("malint is built for Linux/OHOS only")

    def source(self):
        get(
            self,
            url=_SOURCE_URL,
            sha256=_SOURCE_SHA256,
            strip_root=True,
        )

    def _pick_shell(self):
        # CONFIG_SHELL 注入的路径可能失效（设备 bash 签名失效场景），
        # shutil.which 校验后回退 PATH 中的 bash/sh。
        shell = os.environ.get("CONFIG_SHELL", "")
        if not (shell and shutil.which(shell)):
            shell = "bash" if shutil.which("bash") else "sh"
        return shell

    def _build_env(self, shell):
        # /tmp 只读时 clang/zsh 临时文件落到 build 目录（E002）
        tmpdir = os.path.join(self.build_folder, "tmp")
        os.makedirs(tmpdir, exist_ok=True)
        tmpdir = tmpdir.replace("\\", "/")
        # R33（zzuf 同模式）：编译器从 Conan conf 取，不依赖 shell 环境变量
        # —— PATH 中的 cc 可能是 shebang 失效的 HMDFS 包装脚本，导致
        # configure 的 "checking for cc" 选中坏入口（bad interpreter）。
        compilers = self.conf.get("tools.build:compiler_executables") or {}
        cc = compilers.get("c") or "clang"
        return f"TMPDIR={tmpdir} TMPPREFIX={tmpdir}/zsh CC={cc}", shell

    def build(self):
        # 补丁应用（patches 为空时 no-op，G1 要求调用存在）
        apply_conandata_patches(self)

        shell = self._pick_shell()
        envp, shell = self._build_env(shell)

        # 0. E011/E129：将 configure 内部的 umask 077 临时目录改为 022
        #    （HMDFS setgid 目录按组权限判定写入），Python 层替换避免依赖 sed
        cfg = os.path.join(self.build_folder, "configure")
        with open(cfg, encoding="utf-8", errors="surrogateescape") as f:
            content = f.read()
        content = content.replace("umask 077", "umask 022")
        with open(cfg, "w", encoding="utf-8", errors="surrogateescape") as f:
            f.write(content)

        # 1. configure：{shell} 直接解释执行（绕开 /bin/sh shebang，E087）；
        #    显式 --build/--host 跳过 config.guess 内联猜测（E007）。
        prefix = self.package_folder.replace("\\", "/")
        self.run(
            f'"{shell}" -c "set -e && umask 022 && env {envp} '
            f"{shell} ./configure --prefix={prefix}"
            f" --build={_TRIPLET} --host={_TRIPLET}\"",
            env="conanbuild",
        )

        # 2. 编译（-j1 保证顺序，与 zzuf 同惯例；SHELL= 注入 make 子命令解释器）
        self.run(
            f'"{shell}" -c "umask 022 && env {envp} make -j1 SHELL={shell}"',
            env="conanbuild",
        )

        # 3. 上游测试：regress/ 下 6 个 runtest 用例（frame-l3crc、
        #    frame-long、frame-short、id3v1-end、id3v1-noseek、
        #    id3v1-short）。TESTS_ENVIRONMENT=sh 让 runtest 经 sh 显式调用
        #    （HMDFS 无执行位，E046/E087）。交叉编译时跳过。
        if not cross_building(self):
            self.run(
                f'"{shell}" -c "umask 022 && env {envp} '
                f'make check SHELL={shell} TESTS_ENVIRONMENT=sh"',
                env="conanbuild",
            )

    def package(self):
        # --prefix 已指向 package_folder，直接 make install
        shell = self._pick_shell()
        envp, shell = self._build_env(shell)
        self.run(
            f'"{shell}" -c "umask 022 && env {envp} make install SHELL={shell}"',
            env="conanbuild",
        )
        copy(
            self,
            "COPYING",
            self.source_folder,
            os.path.join(self.package_folder, "licenses"),
            keep_path=False,
        )

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = ["bin"]
        self.runenv_info.prepend_path(
            "PATH", os.path.join(self.package_folder, "bin")
        )
