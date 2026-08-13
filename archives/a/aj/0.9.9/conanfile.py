#!/usr/bin/env python3
"""Conan recipe for aj (aj-snapshot) 0.9.9 — JACK/ALSA MIDI 连接快照工具.

aj-snapshot 是 C 命令行工具（单可执行 aj-snapshot），autotools 构建。
硬依赖三个库（configure.ac AC_MSG_ERROR 均 REQUIRED）：
  - alsa-lib（libasound）→ cmd-pkgs 预编译包 alsa-lib 1.2.12（generate() 安装）
  - jack（libjack）→ cmd-pkgs 预编译包 jack 1.9.22（generate() 安装）
  - mxml（libmxml）→ 无 cmd-pkgs 包，配方内自包含构建 mxml 4.0.4（传统布局
    --disable-libmxml4-prefix：aj-snapshot 需要 mxml.h/-lmxml/mxml.pc，而 mxml 4.x
    默认安装为 libmxml4 前缀，必须禁用该前缀）

OHOS 适配补丁（apply_conandata_patches）：
  0001-mxml4-descend-enum：mxml 4.x 用 mxml_descend_t 枚举取代旧宏 MXML_NO_DESCEND
  0002-mxml4-file-api：mxml 4.x 的 load/save API 签名改为 mxml_options_t 参数
  0003-configure-umask：configure 临时目录 umask 077→000（HMDFS 权限限制）

mxml 4.0.4 自包含构建复用 main 中 archives/m/mxml/4.0.4 的 3 个补丁
（config.guess/sub 的 OHOS 识别 + configure umask），补丁文件位于配方
recipe_folder/patches/（conandata 的 mxml_patches 仅记录元数据）。
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
    patch,
)
from conan.tools.layout import basic_layout


def _get_prefix():
    """系统依赖安装前缀（cmd-pkgs 预编译包 / mxml 自包含构建共用）。

    CI/HNP 环境用 DEFAULT_PREFIX，本地回退 ~/usr/local。
    """
    prefix = os.environ.get("DEFAULT_PREFIX")
    if prefix:
        return prefix
    return os.path.join(os.path.expanduser("~"), "usr", "local")


def _install_cmd_pkg(name, version, prefix):
    """下载并解压 cmd-pkgs 预编译包到 prefix（纯 Python，不依赖 curl）。"""
    import tarfile
    import urllib.request

    url = ("https://gitcode.com/OpenHarmonyPCDeveloper/cmd-pkgs/releases/download/pkgs/"
           f"{name}-{version}-ohos-aarch64.tar.gz")
    os.makedirs(prefix, exist_ok=True)
    tarball = os.path.join(prefix, f".install-{name}-{version}.tar.gz")
    try:
        urllib.request.urlretrieve(url, tarball)
        with tarfile.open(tarball, "r:gz") as tar:
            # HMDFS 覆盖已有文件会失败（Operation not permitted），先删后解
            for m in tar.getmembers():
                target = os.path.join(prefix, m.name)
                if os.path.isfile(target):
                    try:
                        os.remove(target)
                    except OSError:
                        pass
            tar.extractall(prefix)
    finally:
        try:
            os.remove(tarball)
        except OSError:
            pass


class AjConan(ConanFile):
    name = "aj"
    version = "0.9.9"
    description = "aj-snapshot: store/restore JACK and/or ALSA midi connections to/from an xml file"
    license = "GPL-3.0"
    homepage = "https://gitlab.com/aj-snapshot/aj-snapshot"
    url = ""  # CI fills this

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)
        # mxml 构建补丁（自包含依赖用，不随 apply_conandata_patches 应用）
        for entry in self.conan_data.get("mxml_patches", []):
            copy(self, os.path.basename(entry["patch_file"]),
                 os.path.join(self.recipe_folder, "patches"),
                 self.export_sources_folder)

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"aj is only supported on Linux/OHOS, not {self.settings.os}"
            )

    def layout(self):
        basic_layout(self)
        # aj-snapshot 构建 in-source（autotools 生成文件直接落在源码目录）
        self.folders.build = "."

    def source(self):
        # aj-snapshot 源码（.tar.bz2，SourceForge 分发）
        get(self, **self.conan_data["sources"], strip_root=True,
            filename="aj-snapshot-0.9.9.tar.bz2")
        # mxml 4.0.4 源码（自包含依赖，构建期使用）
        get(self, **self.conan_data["mxml"], strip_root=True,
            destination="mxml", filename="mxml-4.0.4.tar.gz")

    def generate(self):
        prefix = _get_prefix()
        # 系统依赖：alsa-lib / jack（cmd-pkgs 预编译包）
        _install_cmd_pkg("alsa-lib", "1.2.12", prefix)
        _install_cmd_pkg("jack", "1.9.22", prefix)

    def _build_mxml(self, cc):
        """自包含构建 mxml 4.0.4（传统布局）并安装到 prefix。

        --disable-libmxml4-prefix 是关键：aj-snapshot 按 mxml v3 接口
        （mxml.h / -lmxml / mxml.pc）编译，mxml 4.x 默认安装为 libmxml4
        前缀，必须禁用才产出传统布局。
        """
        prefix = _get_prefix()
        mxml_src = os.path.join(self.source_folder, "mxml")
        for entry in self.conan_data.get("mxml_patches", []):
            patch(
                self,
                base_path=mxml_src,
                patch_file=os.path.join(self.export_sources_folder,
                                        os.path.basename(entry["patch_file"])),
            )
        self.run(
            f"cd {mxml_src} && CC={cc} ./configure --prefix={prefix} "
            f"--disable-libmxml4-prefix --disable-threads --enable-static "
            f"--disable-shared"
        )
        self.run(f"cd {mxml_src} && make -j1")
        self.run(f"cd {mxml_src} && make install")
        return prefix

    def build(self):
        # R33: Get compiler from Conan conf, not shell env vars
        compilers = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)
        cc = compilers.get("c", "clang") if compilers else "clang"

        prefix = self._build_mxml(cc)

        # aj-snapshot 补丁（mxml 4.x 兼容 + configure umask）
        apply_conandata_patches(self)

        # 构建环境：pkg-config / 头文件 / 库 指向 prefix（in-source 构建）
        src = self.source_folder
        pkgcfg = os.path.join(prefix, "lib", "pkgconfig")
        self.run(
            f"cd {src} && "
            f"CC={cc} PKG_CONFIG_PATH='{pkgcfg}' "
            f"CPPFLAGS='-I{os.path.join(prefix, 'include')}' "
            f"LDFLAGS='-L{os.path.join(prefix, 'lib')}' "
            f"SHELL=/system/bin/sh ./configure --prefix={prefix}"
        )
        self.run(f"cd {src} && make -j1")

    def package(self):
        # 单可执行文件 aj-snapshot（in-source 构建，产物在 source_folder/src/）
        bin_dir = os.path.join(self.source_folder, "src")
        copy(self, "aj-snapshot", src=bin_dir,
             dst=os.path.join(self.package_folder, "bin"))
        # 许可证
        copy(self, "COPYING", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        # alsa-lib/jack 为动态库（libasound.so.2/libjack.so.0），消费测试运行时
        # 需要 LD_LIBRARY_PATH 指向系统依赖 prefix
        prefix = _get_prefix()
        self.runenv_info.append_path(
            "LD_LIBRARY_PATH", os.path.join(prefix, "lib")
        )
