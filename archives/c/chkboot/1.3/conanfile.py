#!/usr/bin/env python3
"""chkboot 1.3 —— 检测未加密 /boot 分区文件是否被篡改（纯 shell 脚本包，无编译）。

上游交付物：
  chkboot                : 以 root 运行，对 BOOTDIR 逐文件算 sha512 基线并 diff 出变更
  chkboot-check          : 读取变更告警文件；有未确认变更时以 rc=1 告警
  chkboot-desktopalert   : 桌面通知前端（zenity / xmessage）
  chkboot-profilealert.sh: 登录时通知前端（/etc/profile.d）
  chkboot-bootcheck      : 开机检查（systemd 用户单元脚本）
  chkboot.service + pacman-hooks/ + mkinitcpio-hooks/: 开机集成资产

OHOS 适配（补丁 5 处，每处一行；见 patches/）：
  运行期：/etc 在 OHOS 上是只读文件系统（实测 `mkdir /etc/default` →
  "Read-only file system"），上游硬编码的 `source /etc/default/chkboot.conf`
  不可用；且变量未定义时 ${CHKBOOT_DATA}/${CHANGES_ALERT} 会塌缩成 "/"，
  使 chkboot-check 对任意目录误报 "CHKBOOT ALERT"（并伴随 `cat /` 权限错误）。
  补丁改为 `source "${CHKBOOT_CONF:-/etc/default/chkboot.conf}"`：未设置时与上游
  行为逐字一致；OHOS 上用 CHKBOOT_CONF 指向包内配置。package_info() 的 runenv
  默认把 CHKBOOT_CONF 指向 res/default/chkboot.conf，使 conan 环境内开箱可用。

  构建期（无源码改动）：OHOS 未把 install(1) 暴露为独立命令（coreutils 缺失；
  busybox 内含 install applet 但无同名入口），上游 `make install` 直接
  Error 127。build() 生成一个指向平台 busybox 的 install shim 并前置 PATH，
  使上游 Makefile 原样可用。

  systemd / pacman / mkinitcpio 三类集成资产在 OHOS 无对应子系统，
  安装到 res/ 作为参考数据保留（不参与运行）。

R38：本包安装可执行文件 → 软件级 commands.json。
R26：不适用（无系统同名原生库）；R33：不适用（无编译命令）。
"""
import os
import shutil

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches


class ChkbootConan(ConanFile):
    name = "chkboot"
    version = "1.3"
    description = "Detect changes to the files on an unencrypted /boot partition (boot integrity checker)"
    license = "GPL-2.0-only"
    homepage = "https://github.com/grazzolini/chkboot"
    url = "https://github.com/grazzolini/chkboot"

    package_type = "application"
    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        # 源码与构建产物分离：staging/ 与 install shim 落在 build_folder 下
        self.folders.build = "build"
        self.folders.generators = "build"

    def source(self):
        get(self, **self.conan_data["sources"], filename="chkboot-1.3.tar.gz", strip_root=True)

    def _install_shim_dir(self):
        """OHOS 没有独立的 install(1) 命令：用平台 busybox 的 install applet 建同名入口。

        返回 shim 目录；平台自带 install(1)（如常规 Linux coreutils）时返回 None。
        """
        if shutil.which("install"):
            return None
        busybox = shutil.which("busybox")
        if busybox is None:
            for candidate in ("/usr/bin/busybox",
                              "/bin/busybox",
                              "/data/service/hnp/bin/busybox"):
                if os.path.isfile(candidate):
                    busybox = candidate
                    break
        if busybox is None:
            raise ConanException(
                "chkboot: 平台既无 install(1) 也无 busybox —— 上游 Makefile 的 install: 目标无法执行"
            )
        shim_dir = os.path.join(self.build_folder, "install-shim")
        os.makedirs(shim_dir, exist_ok=True)
        shim = os.path.join(shim_dir, "install")
        if not os.path.exists(shim):
            os.symlink(busybox, shim)
        return shim_dir

    def build(self):
        apply_conandata_patches(self)
        staging = os.path.join(self.build_folder, "staging")
        shim_dir = self._install_shim_dir()
        prefix = f'export PATH="{shim_dir}:$PATH"; ' if shim_dir else ""
        # 上游 Makefile：install: 与 3 个可选目标（systemd / pacman / initcpio）
        for target in ("install", "install-systemd", "install-pacman", "install-initcpio"):
            self.run(f"{prefix}make {target} DESTDIR={staging}", cwd=self.source_folder)

    def package(self):
        staging = os.path.join(self.build_folder, "staging")
        # make install: 产物 → 包内可重定位布局
        copy(self, "*", src=os.path.join(staging, "usr", "bin"),
             dst=os.path.join(self.package_folder, "bin"))
        copy(self, "chkboot.conf", src=os.path.join(staging, "etc", "default"),
             dst=os.path.join(self.package_folder, "res", "default"))
        copy(self, "*", src=os.path.join(staging, "etc", "profile.d"),
             dst=os.path.join(self.package_folder, "res", "profile.d"))
        # 开机集成资产（OHOS 无 systemd / pacman / initcpio，仅作参考数据）
        copy(self, "*", src=os.path.join(staging, "usr", "lib", "systemd"),
             dst=os.path.join(self.package_folder, "res", "systemd"))
        copy(self, "*", src=os.path.join(staging, "usr", "lib", "initcpio", "install"),
             dst=os.path.join(self.package_folder, "res", "initcpio"))
        copy(self, "*", src=os.path.join(staging, "usr", "share", "libalpm", "hooks"),
             dst=os.path.join(self.package_folder, "res", "libalpm-hooks"))
        copy(self, "LICENSE.md", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))
        copy(self, "GPLv2.md", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.resdirs = ["res"]
        # OHOS /etc 只读：默认把配置路径指向包内配置（用户可用 CHKBOOT_CONF 覆盖）
        self.runenv_info.define(
            "CHKBOOT_CONF",
            os.path.join(self.package_folder, "res", "default", "chkboot.conf"),
        )
