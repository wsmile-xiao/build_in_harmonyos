#!/usr/bin/env python3
"""Conan recipe — nutcracker (twemproxy) 0.5.0.

twemproxy 是 Twitter 开源的轻量级高性能 Redis/Memcached 协议代理（daemon 工具）。
构建系统：GNU Autotools（tarball 自带预生成 configure，CI 无需 autoreconf）。
平台：OHOS aarch64 / Linux。

OHOS 适配要点：
- 上游 configure.ac 无 AC_CANONICAL_HOST，传 --host/--build=aarch64-linux-ohos 后
  经 patch 后的 config.sub 归一化为 aarch64-unknown-linux-gnu（build==host、
  cross_compiling=no），AC_TRY_RUN 的 epoll 探针 native 运行 → HAVE_EPOLL。
- config.guess(2018) 不认识 HarmonyOS uname；config.sub 缺 -ohos；patch 0001 补齐。
- vendored libyaml 0.2.5：configure.ac 经 AC_CONFIG_SUBDIRS 递归构建
  contrib/yaml-0.2.5.tar.gz（硬依赖，静态链接 .libs/libyaml.a）。
  patch 0002 在解压后用主树 patch 后的 config.guess/sub 覆盖其 2011 旧版，
  并统一两处 configure 的 mktemp→mkdir（HMDFS 下 Toybox mktemp -d 创建 0700
  目录，进程 UID 与目录 owner 不同时 group 无写权限 → config.status 写临时
  文件 Permission denied；mkdir 目录由 HMDFS 强制 drwxrws--x，group 可写）。
- patch 修改 configure 后其 mtime 最新，automake am--refresh 会尝试重跑
  aclocal-1.16（环境无此工具）→ 构建前 touch 统一时间戳避免自动重建。
- requirements 声明 libyaml/0.2.5 保证依赖清单完整（实际链接 vendored 静态库，
  上游设计如此）；CI 依赖闸 PF4 验证 libyaml/0.2.5 已发布制品仓。
"""
import os
import subprocess

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout

_TMP_TOUCHED = (
    "aclocal.m4 configure config.h.in Makefile.in "
    "contrib/Makefile.in src/Makefile.in"
)


class NutcrackerConan(ConanFile):
    name = "nutcracker"
    version = "0.5.0"
    description = "Twemproxy - a fast, light-weight proxy for memcached and redis"
    license = "Apache-2.0"
    homepage = "https://github.com/twitter/twemproxy"
    package_type = "application"

    settings = "os", "arch", "compiler", "build_type"

    def validate(self):
        # R32: settings.os 判断必须 in ("Linux", "OHOS")
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"nutcracker is only supported on Linux/OHOS, not {self.settings.os}"
            )

    def requirements(self):
        # libyaml 为解析 nutcracker.yml 的硬依赖；上游 0.5.0 vendored 构建，
        # 声明保证依赖清单完整。实际链接由上游 configure 的 AC_CONFIG_SUBDIRS 完成。
        self.requires("libyaml/0.2.5")

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        # 补丁在 build() 中应用（dnsperf 模式），保证 source_folder 就绪后统一处理
        get(self, **self.conan_data["sources"], strip_root=True)

    def _cc(self):
        # R33: 编译器从 profile conf 读取，禁止裸用环境变量（release worker 上为空）
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

        # patch 修改 configure 后 mtime 最新，automake am--refresh 会尝试重跑
        # aclocal-1.16（环境无此工具），统一时间戳避免自动重建（R6：不重生成
        # 构建系统文件）。
        self.run(f"touch aclocal.m4 && touch -r aclocal.m4 {_TMP_TOUCHED}",
                 cwd=self.source_folder)

        build_dir = self.source_folder
        lines = [
            "#!/bin/sh",
            "set -e",
            f'cd "{build_dir}"',
            f'export CC="{cc}"',
            # profile CONFIG_SHELL 指向 bash 在深路径下 getcwd 异常，统一 /bin/sh
            'export CONFIG_SHELL="/bin/sh"',
            'export SHELL="/bin/sh"',
            f'export PATH="{os.path.dirname(cc)}:$PATH"',
            f'export TMPDIR="{self.build_folder}"',
            "./configure --host=aarch64-linux-ohos --build=aarch64-linux-ohos --prefix=/",
            # R9: 单 job 编译（HMDFS jobserver fifo EPERM）
            "make -j1",
            # 上游测试：make check 运行 test_all（967 断言）+ vendored yaml 2 项
            "make check",
        ]
        script = os.path.join(self.build_folder, "_build.sh")
        with open(script, "w", encoding="utf-8", newline="\n") as f:
            f.write("\n".join(lines) + "\n")
        os.chmod(script, 0o755)
        subprocess.check_call(["/bin/sh", script], cwd=build_dir)

    def package(self):
        # configure --prefix=/ + DESTDIR 隔离安装
        self.run(f"make install DESTDIR={self.package_folder}",
                 cwd=self.source_folder)

    def package_info(self):
        self.cpp_info.bindirs = ["sbin", "bin"]
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.libs = []
        self.buildenv_info.append_path(
            "PATH", os.path.join(self.package_folder, "sbin")
        )
        self.runenv_info.append_path(
            "PATH", os.path.join(self.package_folder, "sbin")
        )